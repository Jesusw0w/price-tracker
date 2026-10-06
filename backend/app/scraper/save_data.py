import datetime

from sqlalchemy.orm import Session

from app.db.models import PriceRow, ProductRow
from app.scraper.process_data import Scraped


def save(session: Session, scraped: list[Scraped], day: datetime.date) -> None:
    """Store one price per product for ``day``; a re-scrape that day overwrites it."""
    for page in scraped:
        if page.name:
            session.get_one(ProductRow, page.asin).name = page.name
        if page.price_cents is not None:
            session.merge(
                PriceRow(asin=page.asin, date=day, price_cents=page.price_cents)
            )
    session.commit()
