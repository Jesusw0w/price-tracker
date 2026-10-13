import datetime
from typing import Any, Literal

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

RefreshStatus = Literal["pending", "running", "done", "failed"]
MemberStatus = Literal["pending", "approved", "rejected"]


class ProductRow(Base):
    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint("owner_id", "url", name="products_owner_id_url_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64))  # Cognito sub
    public: Mapped[bool] = mapped_column(default=False)
    url: Mapped[str] = mapped_column(String(2048))
    domain: Mapped[str]
    name: Mapped[str | None]  # None until first scraped
    currency: Mapped[str | None] = mapped_column(String(3))  # ISO 4217
    tracked: Mapped[bool] = mapped_column(default=True)
    added_at: Mapped[datetime.date] = mapped_column(default=datetime.date.today)
    # First scrape that found the page without an offer; cleared by the next price
    unavailable_since: Mapped[datetime.date | None]

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


class SessionRow(Base):
    """A signed-in browser. Deleting the row signs it out."""

    __tablename__ = "sessions"

    # SHA-256 of the cookie, so a leaked table holds no usable sessions
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_sub: Mapped[str] = mapped_column(String(64), index=True)
    email: Mapped[str]
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))


class UserSettingsRow(Base):
    __tablename__ = "user_settings"

    user_sub: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)  # validated by UserSettings


class MemberRow(Base):
    """A Cognito user who has signed in; only approved ones may use /api."""

    __tablename__ = "members"

    sub: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str]
    status: Mapped[MemberStatus]
    requested_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
