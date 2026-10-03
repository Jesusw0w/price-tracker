import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, engine


class ProductRow(Base):
    __tablename__ = "products"

    asin: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str | None]  # None until first scraped
    tracked: Mapped[bool] = mapped_column(default=True)
    added_at: Mapped[datetime.date] = mapped_column(default=datetime.date.today)


class PriceRow(Base):
    __tablename__ = "prices"

    asin: Mapped[str] = mapped_column(ForeignKey("products.asin"), primary_key=True)
    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    price_cents: Mapped[int]  # integer cents: floats can't hold money exactly


def init_db() -> None:
    """Create missing tables and close them to Supabase's public REST API."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for table in Base.metadata.tables:
            # RLS with no policies blocks the anon REST API; the postgres role we
            # connect as bypasses RLS. Table names come from our models, not input.
            conn.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
