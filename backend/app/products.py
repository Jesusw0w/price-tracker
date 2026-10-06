import datetime
import re
import statistics
from typing import Annotated

from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import PriceRow, ProductRow

ASIN_RE = re.compile(r"(?:/dp/|/gp/product/|^)([A-Z0-9]{10})(?:[/?#]|$)", re.IGNORECASE)

# FastAPI path params and MCP tool args validate the same way
Asin = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{10}$")]


class InvalidLink(ValueError):
    pass


class AlreadyTracked(Exception):
    pass


class UnknownProduct(LookupError):
    pass


class PricePoint(BaseModel):
    date: datetime.date
    price: float  # euros


class Product(BaseModel):
    asin: str
    url: str
    name: str | None  # None until first scraped
    history: list[PricePoint]  # oldest first


class ProductSummary(BaseModel):
    asin: str
    name: str | None
    price: float | None
    price_date: datetime.date | None


class PriceSummary(BaseModel):
    asin: str
    name: str | None
    latest_price: float | None = None
    highest_price: float | None = None
    lowest_price: float | None = None
    mean_price: float | None = None
    median_price: float | None = None


def parse_asin(link: str) -> str | None:
    """Return the upper-cased ASIN from a product URL or bare ASIN, else ``None``."""
    match = ASIN_RE.search(link.strip())
    return match.group(1).upper() if match else None


def product_url(asin: str) -> str:
    return f"https://www.amazon.es/dp/{asin}"


def to_product(row: ProductRow) -> Product:
    return Product(
        asin=row.asin,
        url=product_url(row.asin),
        name=row.name,
        history=[
            PricePoint(date=p.date, price=p.price_cents / 100) for p in row.prices
        ],
    )


def tracked_products(session: Session) -> list[Product]:
    rows = session.scalars(
        select(ProductRow)
        .where(ProductRow.tracked)
        .order_by(ProductRow.added_at, ProductRow.asin)
        .options(selectinload(ProductRow.prices))  # one query for all histories
    )
    return [to_product(row) for row in rows]


def track(session: Session, link: str) -> Product:
    """Start tracking a product. If it was tracked before, its price history is kept.

    Raises:
        InvalidLink: The link has no ASIN.
        AlreadyTracked: The product is already tracked.
    """
    asin = parse_asin(link)
    if asin is None:
        raise InvalidLink("Paste an Amazon product link or a 10-character ASIN")
    row = session.get(ProductRow, asin)
    if row is None:
        row = ProductRow(asin=asin)
        session.add(row)
    elif row.tracked:
        raise AlreadyTracked("Already tracking this product")
    row.tracked = True
    session.commit()
    return to_product(row)


def summarize(product: Product) -> ProductSummary:
    """Generate a summary of the product with latest price."""
    latest_record = product.history[-1] if product.history else None

    return ProductSummary(
        asin=product.asin,
        name=product.name,
        price=latest_record.price if latest_record else None,
        price_date=latest_record.date if latest_record else None,
    )


def product_row(session: Session, asin: str) -> ProductRow:
    """Return the product, tracked or not.

    Raises:
        UnknownProduct: No product has this ASIN.
    """
    row = session.get(ProductRow, asin)
    if row is None:
        raise UnknownProduct(f"No product with ASIN {asin}")
    return row


def price_history(session: Session, asin: str, days: int) -> list[PricePoint]:
    """Return prices from the last ``days`` days plus today, oldest first, in euros.

    Raises:
        UnknownProduct: No product has this ASIN.
    """
    product_row(session, asin)
    filtered_history = session.scalars(
        select(PriceRow)
        .where(
            PriceRow.date >= (datetime.date.today() - datetime.timedelta(days=days)),
            PriceRow.asin == asin,
        )
        .order_by(PriceRow.date)
    )
    return [
        PricePoint(price=p.price_cents / 100, date=p.date) for p in filtered_history
    ]


def price_summary(session: Session, asin: str, days: int) -> PriceSummary:
    """Summarize prices from the last ``days`` days plus today, in euros.

    Price fields are None when no price was recorded in that window.

    Raises:
        UnknownProduct: No product has this ASIN.
    """
    row = product_row(session, asin)
    prices = [p.price for p in price_history(session, asin, days)]
    if not prices:
        return PriceSummary(asin=asin, name=row.name)

    return PriceSummary(
        asin=asin,
        name=row.name,
        latest_price=prices[-1],
        highest_price=max(prices),
        lowest_price=min(prices),
        mean_price=round(statistics.mean(prices), 2),
        median_price=round(statistics.median(prices), 2),
    )
