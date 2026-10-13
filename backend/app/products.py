import datetime
import statistics
from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db.models import PriceRow, ProductRow, RefreshRow, RefreshStatus
from app.links import canonical_url, site

# FastAPI path params and MCP tool args validate the same way
ProductId = Annotated[int, Field(ge=1)]


class AlreadyTracked(Exception):
    pass


class UnknownProduct(LookupError):
    pass


class NotTracked(Exception):
    pass


class TooManyTrackers(Exception):
    pass


class PricePoint(BaseModel):
    date: datetime.date
    price: float  # in the product's currency


class Product(BaseModel):
    id: int
    url: str
    name: str | None = None
    currency: str | None = None
    public: bool = False
    mine: bool = True  # only the owner may archive, delete or share it
    unavailable_since: datetime.date | None = None
    history: list[PricePoint]  # oldest first


class ProductSummary(BaseModel):
    id: int
    url: str
    name: str | None = None
    currency: str | None = None
    price: float | None = None
    price_date: datetime.date | None = None
    unavailable_since: datetime.date | None = None


class PriceSummary(BaseModel):
    id: int
    name: str | None
    currency: str | None
    latest_price: float | None = None
    highest_price: float | None = None
    lowest_price: float | None = None
    mean_price: float | None = None
    median_price: float | None = None


class RefreshInfo(BaseModel):
    product_id: int
    status: RefreshStatus | None = None
    requested_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    error: str | None = None
    last_price_date: datetime.date | None = None


def _as_utc(moment: datetime.datetime) -> datetime.datetime:
    """Treat a naive datetime as UTC; SQLite drops the timezone Postgres keeps."""
    return moment if moment.tzinfo else moment.replace(tzinfo=datetime.UTC)


def _visible_to(user: str) -> ColumnElement[bool]:
    return or_(ProductRow.owner_id == user, ProductRow.public)


def to_product(row: ProductRow, user: str) -> Product:
    return Product(
        id=row.id,
        url=row.url,
        name=row.name,
        currency=row.currency,
        public=row.public,
        mine=row.owner_id == user,
        unavailable_since=row.unavailable_since,
        history=[
            PricePoint(date=p.date, price=p.price_cents / 100) for p in row.prices
        ],
    )


def tracked_products(session: Session, user: str) -> list[Product]:
    """The user's tracked products and everyone's public ones."""
    return _products(session, user, ProductRow.tracked.is_(True), _visible_to(user))


def archived_products(session: Session, user: str) -> list[Product]:
    """The user's untracked products. Tracking the URL again restores one."""
    return _products(session, user, ~ProductRow.tracked, ProductRow.owner_id == user)


def _products(
    session: Session, user: str, *where: ColumnElement[bool]
) -> list[Product]:
    rows = session.scalars(
        select(ProductRow)
        .where(*where)
        .order_by(ProductRow.added_at, ProductRow.id)
        .options(selectinload(ProductRow.prices))  # one query for all histories
    )
    return [to_product(row, user) for row in rows]


def track(session: Session, user: str, link: str) -> Product:
    """Start tracking a product. If it was tracked before, its price history is kept.

    Raises:
        InvalidLink: The link is not an https link to a public website.
        AlreadyTracked: The user already tracks the product.
        TooManyTrackers: The user tracks ``settings.max_trackers`` products already.
    """
    url = canonical_url(link)
    mine = ProductRow.owner_id == user
    row = session.scalar(select(ProductRow).where(mine, ProductRow.url == url))
    if row is not None and row.tracked:
        raise AlreadyTracked("Already tracking this product")
    # Every tracker costs a scrape; the cap bounds what a looping agent can queue
    tracked = session.scalar(
        select(func.count()).select_from(ProductRow).where(mine, ProductRow.tracked)
    )
    if (tracked or 0) >= settings.max_trackers:
        raise TooManyTrackers(f"Tracking the maximum of {settings.max_trackers}")
    if row is None:
        row = ProductRow(owner_id=user, url=url, domain=site(url))
        session.add(row)
    row.tracked = True
    session.commit()
    return to_product(row, user)


def summarize(product: Product) -> ProductSummary:
    """The product's latest price; price fields are ``None`` if never scraped."""
    latest_record = product.history[-1] if product.history else None

    return ProductSummary(
        id=product.id,
        url=product.url,
        name=product.name,
        currency=product.currency,
        price=latest_record.price if latest_record else None,
        price_date=latest_record.date if latest_record else None,
        unavailable_since=product.unavailable_since,
    )


def product_row(
    session: Session, user: str, product_id: int, *, owned: bool = False
) -> ProductRow:
    """Return the product, tracked or not, if the user can see it (or owns it).

    Raises:
        UnknownProduct: No such product for this user. Someone else's private
            product is unknown too, so probing ids reveals nothing.
    """
    row = session.get(ProductRow, product_id)
    if row is None or (row.owner_id != user and (owned or not row.public)):
        raise UnknownProduct(f"No product with id {product_id}")
    return row


def set_public(session: Session, user: str, product_id: int, public: bool) -> Product:
    """Share the user's product with every user, or stop sharing it.

    Raises:
        UnknownProduct: The user owns no product with this id.
    """
    row = product_row(session, user, product_id, owned=True)
    row.public = public
    session.commit()
    return to_product(row, user)


def change_link(session: Session, user: str, product_id: int, link: str) -> Product:
    """Point the user's product at a new listing, keeping its price history.

    For a listing that was replaced, e.g. a new Amazon ASIN for the same item. The
    new page is queued for a refresh.

    Raises:
        UnknownProduct: The user owns no product with this id.
        InvalidLink: The link is not an https link to a public website.
        AlreadyTracked: Another of the user's products has this link.
    """
    row = product_row(session, user, product_id, owned=True)
    url = canonical_url(link)
    if url != row.url and session.scalar(
        select(ProductRow.id).where(ProductRow.owner_id == user, ProductRow.url == url)
    ):
        raise AlreadyTracked("Another of your products has this link")
    row.url, row.domain = url, site(url)
    row.unavailable_since = None
    _mark_pending(session, product_id, datetime.datetime.now(datetime.UTC))
    session.commit()
    return to_product(row, user)


def archive_product(session: Session, user: str, product_id: int) -> None:
    """Stop tracking the user's product and keep its price history.

    Raises:
        NotTracked: The user tracks no product with this id.
    """
    row = session.get(ProductRow, product_id)
    if row is None or row.owner_id != user or not row.tracked:
        raise NotTracked("Product not tracked")
    row.tracked = False
    session.commit()


def delete_product(session: Session, user: str, product_id: int) -> None:
    """Delete the user's product, tracked or not, with its history. Cannot be undone.

    Raises:
        UnknownProduct: The user owns no product with this id.
    """
    row = product_row(session, user, product_id, owned=True)
    # The foreign keys have no ON DELETE CASCADE, so the child rows go first
    session.execute(delete(PriceRow).where(PriceRow.product_id == product_id))
    session.execute(delete(RefreshRow).where(RefreshRow.product_id == product_id))
    session.delete(row)
    session.commit()


def price_history(
    session: Session, user: str, product_id: int, days: int
) -> list[PricePoint]:
    """Return prices from the last ``days`` days plus today, oldest first.

    Raises:
        UnknownProduct: The user can see no product with this id.
    """
    product_row(session, user, product_id)
    filtered_history = session.scalars(
        select(PriceRow)
        .where(
            PriceRow.date >= (datetime.date.today() - datetime.timedelta(days=days)),
            PriceRow.product_id == product_id,
        )
        .order_by(PriceRow.date)
    )
    return [
        PricePoint(price=p.price_cents / 100, date=p.date) for p in filtered_history
    ]


def price_summary(
    session: Session, user: str, product_id: int, days: int
) -> PriceSummary:
    """Summarize prices from the last ``days`` days plus today.

    Price fields are None when no price was recorded in that window.

    Raises:
        UnknownProduct: The user can see no product with this id.
    """
    row = product_row(session, user, product_id)
    prices = [p.price for p in price_history(session, user, product_id, days)]
    if not prices:
        return PriceSummary(id=row.id, name=row.name, currency=row.currency)

    return PriceSummary(
        id=row.id,
        name=row.name,
        currency=row.currency,
        latest_price=prices[-1],
        highest_price=max(prices),
        lowest_price=min(prices),
        mean_price=round(statistics.mean(prices), 2),
        median_price=round(statistics.median(prices), 2),
    )


def product_rows(
    session: Session, user: str, product_ids: list[int]
) -> list[ProductRow]:
    """Return the products in the order given, without duplicates.

    Raises:
        UnknownProduct: The user can't see some ids; the message lists them all.
    """
    unique = list(dict.fromkeys(product_ids))
    query = select(ProductRow).where(ProductRow.id.in_(unique), _visible_to(user))
    rows = {row.id: row for row in session.scalars(query)}
    if missing := [str(i) for i in unique if i not in rows]:
        raise UnknownProduct(f"No product with id {', '.join(missing)}")
    return [rows[i] for i in unique]


def _refreshes(session: Session, product_ids: list[int]) -> dict[int, RefreshRow]:
    query = select(RefreshRow).where(RefreshRow.product_id.in_(product_ids))
    return {row.product_id: row for row in session.scalars(query)}


def refresh_status(
    session: Session, user: str, product_ids: list[int]
) -> list[RefreshInfo]:
    """Each product's latest refresh request and the date of its newest price.

    Raises:
        UnknownProduct: The user can't see some ids.
    """
    unique = [row.id for row in product_rows(session, user, product_ids)]
    last_price_dates = dict(
        session.execute(
            select(PriceRow.product_id, func.max(PriceRow.date))
            .where(PriceRow.product_id.in_(unique))
            .group_by(PriceRow.product_id)
        ).all()
    )
    refreshes = _refreshes(session, unique)
    infos = []
    for product_id in unique:
        info = RefreshInfo(
            product_id=product_id, last_price_date=last_price_dates.get(product_id)
        )
        if refresh := refreshes.get(product_id):
            info.status = refresh.status
            info.requested_at = refresh.requested_at
            info.finished_at = refresh.finished_at
            info.error = refresh.error
        infos.append(info)
    return infos


def _mark_pending(session: Session, product_id: int, now: datetime.datetime) -> None:
    refresh = session.get(RefreshRow, product_id)
    if refresh is None:
        refresh = RefreshRow(product_id=product_id)
        session.add(refresh)
    refresh.status = "pending"
    refresh.requested_at = now
    refresh.finished_at = None
    refresh.error = None


def queue_refresh(
    session: Session, user: str, product_ids: list[int]
) -> list[RefreshInfo]:
    """Queue a refresh of each product, all or none.

    A product whose refresh is pending, running or recent keeps it. "Recent"
    means requested within ``settings.refresh_cooldown_minutes``.

    Raises:
        UnknownProduct: The user can't see some ids; nothing is queued.
        NotTracked: Some products are not tracked; nothing is queued.
    """
    rows = product_rows(session, user, product_ids)
    if untracked := [str(row.id) for row in rows if not row.tracked]:
        raise NotTracked(f"Not tracked: {', '.join(untracked)}")
    unique = [row.id for row in rows]
    now = datetime.datetime.now(datetime.UTC)
    cooldown = datetime.timedelta(minutes=settings.refresh_cooldown_minutes)
    refreshes = _refreshes(session, unique)
    for product_id in unique:
        refresh = refreshes.get(product_id)
        if refresh is not None and (
            refresh.status in ("pending", "running")
            or now - _as_utc(refresh.requested_at) < cooldown
        ):
            continue
        _mark_pending(session, product_id, now)
    session.commit()
    return refresh_status(session, user, unique)
