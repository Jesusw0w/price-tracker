import datetime
import logging
import sys

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import ProductRow
from app.logs import setup_logging
from app.products import product_url
from app.scraper import save_data
from app.scraper.load_data import ExtractData
from app.scraper.process_data import parse_page

log = logging.getLogger(__name__)


def main() -> None:
    """Scrape every tracked product once and save today's prices."""
    log.info("Scrape started")

    # Separate sessions: holding one open through minutes of HTTP pins a connection
    with SessionLocal() as session:
        asins = session.scalars(select(ProductRow.asin).where(ProductRow.tracked))
        by_url = {product_url(asin): asin for asin in asins}

    raw_data = ExtractData(gpu_list=list(by_url)).bs_extraction()
    scraped = [
        parse_page(by_url[url], html)
        for url, html in zip(
            raw_data["url_list"], raw_data["gpu_raw_data"], strict=True
        )
    ]

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
