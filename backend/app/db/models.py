import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

RefreshStatus = Literal["pending", "running", "done", "failed"]


class ProductRow(Base):
    __tablename__ = "products"

    asin: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str | None]  # None until first scraped
    tracked: Mapped[bool] = mapped_column(default=True)
    added_at: Mapped[datetime.date] = mapped_column(default=datetime.date.today)

    prices: Mapped[list[PriceRow]] = relationship(order_by="PriceRow.date")


class PriceRow(Base):
    __tablename__ = "prices"

    asin: Mapped[str] = mapped_column(ForeignKey("products.asin"), primary_key=True)
    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    price_cents: Mapped[int]


class RefreshRow(Base):
    """The latest refresh of a product; a new request overwrites it."""

    __tablename__ = "refreshes"

    asin: Mapped[str] = mapped_column(ForeignKey("products.asin"), primary_key=True)
    status: Mapped[RefreshStatus]
    requested_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    error: Mapped[str | None]
