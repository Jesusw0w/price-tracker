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
from app.scraper.load_data import Blocked, FetchError, fetch
from app.scraper.process_data import Scraped, is_blocked, parse_page

# Gap between two requests to the same site; Amazon answers 2 s bursts with captchas
REQUEST_GAP_S: Final[int] = 20
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
        raise Blocked(f"Blocked by {domain} (captcha)")
    return parse_page(product_id, domain, html)


def _describe(scraped: Scraped) -> str:
    if not scraped.available:
        return "not available"
    if scraped.price_cents is None:
        return "no price found"
    return f"{scraped.price_cents / 100:.2f} {scraped.currency or ''}".rstrip()


def scrape_site(site_jobs: list[Job]) -> list[tuple[Job, Scraped | Exception]]:
    """Scrape one site's pages in turn, spaced out; failures come back as values."""
    total = len(site_jobs)
    log.info(
        "%s: %d pages, about %d min",
        site_jobs[0].domain,
        total,
        round((total - 1) * REQUEST_GAP_S / 60),
    )
    outcomes: list[tuple[Job, Scraped | Exception]] = []
    for i, job in enumerate(site_jobs):
        if i:
            time.sleep(REQUEST_GAP_S)
        progress = f"{job.domain} {i + 1}/{total} ({(i + 1) * 100 // total}%)"
        try:
            scraped = scrape(job.product_ids[0], job.url, job.domain)
            log.info("%s %s: %s", progress, job.url, _describe(scraped))
            outcomes.append((job, scraped))
        except Blocked as e:
            # More requests only prolong the block, so fail the rest without fetching
            log.warning("%s %s; skipping the rest", progress, e)
            outcomes.extend((rest, e) for rest in site_jobs[i:])
            break
        except (InvalidLink, FetchError, requests.RequestException) as e:
            log.warning("%s %s failed: %s", progress, job.url, e)
            outcomes.append((job, e))
    return outcomes


def drain_batch(pool: Executor) -> int:
    """Claim a batch, scrape its sites in parallel and save each site as it ends.

    Returns:
        How many pages were claimed; 0 means the queue is empty.
    """
    start = time.monotonic()
    with SessionLocal() as session:
        claimed = jobs.claim(session, BATCH)
    by_site: dict[str, list[Job]] = defaultdict(list)
    for job in claimed:
        by_site[job.domain].append(job)

    # Threads only fetch and parse; every database write stays on this thread
    futures = [pool.submit(scrape_site, site_jobs) for site_jobs in by_site.values()]
    failed = 0
    for future in as_completed(futures):
        now = datetime.datetime.now(datetime.UTC)
        with SessionLocal() as session:
            for job, outcome in future.result():
                failed += isinstance(outcome, Exception)
                jobs.finish(session, job, outcome, now)
    if claimed:
        log.info(
            "Scraped %d of %d pages from %d sites in %.0f s",
            len(claimed) - failed,
            len(claimed),
            len(by_site),
            time.monotonic() - start,
        )
    return len(claimed)


def run(*, once: bool) -> None:
    log.info("Scraper started, polling every %d s", POLL_S)
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
