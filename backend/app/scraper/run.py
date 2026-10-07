import datetime
import logging
import sys
import time
from typing import Final

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import ProductRow
from app.links import InvalidLink
from app.logs import setup_logging
from app.scraper import save_data
from app.scraper.load_data import FetchError, fetch
from app.scraper.process_data import Scraped, is_blocked, parse_page

REQUEST_GAP_S: Final[int] = (
    2  # one page at a time, spaced out, to stay under bot detection
)

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


def main() -> None:
    """Scrape every tracked product once and save today's prices."""
    with SessionLocal() as session:
        targets = session.execute(
            select(ProductRow.id, ProductRow.url, ProductRow.domain).where(
                ProductRow.tracked
            )
        ).all()
    log.info("Scraping %d products", len(targets))

    scraped = []
    for i, (product_id, url, domain) in enumerate(targets):
        if i:
            time.sleep(REQUEST_GAP_S)
        try:
            scraped.append(scrape(product_id, url, domain))
        except (InvalidLink, FetchError, requests.RequestException) as e:
            log.warning("Skipping %s: %s", url, e)

    with SessionLocal() as session:
        save_data.save(session, scraped, datetime.date.today())

    log.info("Saved %d prices", sum(p.price_cents is not None for p in scraped))


if __name__ == "__main__":
    setup_logging()
    try:
        main()
    except Exception:
        log.exception("Scrape failed")
        sys.exit(1)
