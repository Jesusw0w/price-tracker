import datetime

from sqlalchemy.orm import Session

from app.db.models import PriceRow, ProductRow
from app.scraper.process_data import Scraped


def save(session: Session, scraped: list[Scraped], day: datetime.date) -> None:
    """Store one price per product for ``day``; a re-scrape that day overwrites it."""
    for page in scraped:
        product = session.get_one(ProductRow, page.product_id)
        if page.name:
            product.name = page.name
        if page.currency:
            product.currency = page.currency
        if page.price_cents is not None:
            session.merge(
                PriceRow(
                    product_id=page.product_id, date=day, price_cents=page.price_cents
                )
            )
    session.commit()
