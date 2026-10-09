"""The home scraper: works the refresh queue, and queues every product once a day.

``python -m app.scraper.run`` keeps running; ``--once`` does today's run and exits.
"""

import argparse
import datetime
import logging
import sys
import time
from collections import defaultdict
from concurrent.futures import Executor, ThreadPoolExecutor, as_completed
from typing import Final

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.db.database import SessionLocal
from app.links import InvalidLink
from app.logs import setup_logging
from app.scraper import jobs
from app.scraper.jobs import Job
from app.scraper.load_data import FetchError, fetch
from app.scraper.process_data import Scraped, is_blocked, parse_page

# Gap between two requests to the same site, to stay under bot detection
REQUEST_GAP_S: Final[int] = 2
POLL_S: Final[int] = 60
BATCH: Final[int] = 50

log = logging.getLogger(__name__)


def scrape(product_id: int, url: str, domain: str) -> Scraped:
    """Fetch and parse one product page.

    Raises:
        InvalidLink: The URL, or a redirect, points somewhere non-public.
        FetchError: The page could not be read, or the site blocked the scraper.
        requests.RequestException: The connection failed or timed out.
    """
    html = BeautifulSoup(fetch(url), "html.parser")
    if is_blocked(domain, html):
        raise FetchError(f"Blocked by {domain} (captcha)")
    return parse_page(product_id, domain, html)


def scrape_site(site_jobs: list[Job]) -> list[tuple[Job, Scraped | Exception]]:
    """Scrape one site's pages in turn, spaced out; failures come back as values."""
    outcomes: list[tuple[Job, Scraped | Exception]] = []
    for i, job in enumerate(site_jobs):
        if i:
            time.sleep(REQUEST_GAP_S)
        try:
            outcomes.append((job, scrape(job.product_ids[0], job.url, job.domain)))
        except (InvalidLink, FetchError, requests.RequestException) as e:
            log.warning("Failed %s: %s", job.url, e)
            outcomes.append((job, e))
    return outcomes


def drain_batch(pool: Executor) -> int:
    """Claim a batch, scrape its sites in parallel and save each site as it ends.

    Returns:
        How many pages were claimed; 0 means the queue is empty.
    """
    with SessionLocal() as session:
        claimed = jobs.claim(session, BATCH)
    by_site: dict[str, list[Job]] = defaultdict(list)
    for job in claimed:
        by_site[job.domain].append(job)

    # Threads only fetch and parse; every database write stays on this thread
    futures = [pool.submit(scrape_site, site_jobs) for site_jobs in by_site.values()]
    for future in as_completed(futures):
        now = datetime.datetime.now(datetime.UTC)
        with SessionLocal() as session:
            for job, outcome in future.result():
                jobs.finish(session, job, outcome, now)
    if claimed:
        log.info("Scraped %d pages from %d sites", len(claimed), len(by_site))
    return len(claimed)


def run(*, once: bool) -> None:
    with SessionLocal() as session:
        jobs.requeue_running(session)
    with ThreadPoolExecutor(settings.scrape_workers) as pool:
        while True:
            now = datetime.datetime.now(datetime.UTC)
            if once or now.hour >= settings.scrape_hour_utc:
                with SessionLocal() as session:
                    if queued := jobs.queue_daily(session, now):
                        log.info("Queued %d products for today", queued)
            while drain_batch(pool):
                # The next batch may start on a site the last one just finished
                time.sleep(REQUEST_GAP_S)
            if once:
                return
            time.sleep(POLL_S)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="queue today's run now, work the queue until empty, then exit",
    )
    args = parser.parse_args()
    setup_logging()
    try:
        run(once=args.once)
    except KeyboardInterrupt:
        pass
    except Exception:
        log.exception("Scraper stopped")
        sys.exit(1)


if __name__ == "__main__":
    main()
