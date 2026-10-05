import datetime
import re
from typing import Annotated

from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ProductRow

ASIN_RE = re.compile(r"(?:/dp/|/gp/product/|^)([A-Z0-9]{10})(?:[/?#]|$)", re.IGNORECASE)

# FastAPI path params and MCP tool args validate the same way
Asin = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{10}$")]


class InvalidLink(ValueError):
    pass


class AlreadyTracked(Exception):
    pass


class PricePoint(BaseModel):
    date: datetime.date
    price: float  # euros


class Product(BaseModel):
    asin: str
    url: str
    name: str | None  # None until first scraped
    history: list[PricePoint]  # oldest first


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
