import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

RefreshStatus = Literal["pending", "running", "done", "failed"]


class ProductRow(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True)  # canonical form
    domain: Mapped[str]  # picks the parser; "www." stripped
    name: Mapped[str | None]  # None until first scraped
    currency: Mapped[str | None] = mapped_column(String(3))  # ISO 4217
    tracked: Mapped[bool] = mapped_column(default=True)
    added_at: Mapped[datetime.date] = mapped_column(default=datetime.date.today)

    prices: Mapped[list[PriceRow]] = relationship(order_by="PriceRow.date")


class PriceRow(Base):
    __tablename__ = "prices"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    price_cents: Mapped[int]  # price x 100, in the product's currency


class RefreshRow(Base):
    """The latest refresh of a product; a new request overwrites it."""

    __tablename__ = "refreshes"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    status: Mapped[RefreshStatus]
    requested_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    error: Mapped[str | None]
