"""The refresh queue in the ``refreshes`` table, as the home scraper works it.

Users and agents queue single products (``products.queue_refresh``); the daily run
queues every tracked product. One scraper process claims and finishes them.
"""

import datetime
from collections import defaultdict
from typing import Final, NamedTuple

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import ProductRow, RefreshRow
from app.scraper import save_data
from app.scraper.process_data import Scraped

MAX_ERROR_LENGTH: Final[int] = 200


class Job(NamedTuple):
    """One page to fetch, for every product that tracks this URL."""

    product_ids: tuple[int, ...]
    url: str
    domain: str


def _utc(moment: datetime.datetime) -> datetime.datetime:
    # SQLite hands back naive datetimes; Postgres keeps the zone
    return moment if moment.tzinfo else moment.replace(tzinfo=datetime.UTC)


def queue_daily(session: Session, now: datetime.datetime) -> int:
    """Queue every tracked product not requested yet on ``now``'s UTC day.

    Safe to call on every poll: a product requested today, or still pending or
    running, is left alone.

    Returns:
        How many products were queued.
    """
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tracked = session.scalars(select(ProductRow.id).where(ProductRow.tracked)).all()
    refreshes = {
        row.product_id: row
        for row in session.scalars(
            select(RefreshRow).where(RefreshRow.product_id.in_(tracked))
        )
    }
    queued = 0
    for product_id in tracked:
        refresh = refreshes.get(product_id)
        if refresh is None:
            refresh = RefreshRow(product_id=product_id)
            session.add(refresh)
        elif (
            refresh.status in ("pending", "running")
            or _utc(refresh.requested_at) >= midnight
        ):
            continue
        refresh.status = "pending"
        refresh.requested_at = now
        refresh.finished_at = None
        refresh.error = None
        queued += 1
    session.commit()
    return queued


def requeue_running(session: Session) -> None:
    """Put refreshes a killed scraper left ``running`` back in the queue."""
    # Assumes one scraper process; several would need a claimed_at
    # column and a timeout instead
    session.execute(
        update(RefreshRow)
        .where(RefreshRow.status == "running")
        .values(status="pending")
    )
    session.commit()


def claim(session: Session, limit: int) -> list[Job]:
    """Mark up to ``limit`` pending refreshes running, oldest first, as jobs.

    Products of different users with the same URL share one job, so the page is
    fetched once.
    """
    rows = session.execute(
        select(RefreshRow, ProductRow.url, ProductRow.domain)
        .join(ProductRow, ProductRow.id == RefreshRow.product_id)
        .where(RefreshRow.status == "pending")
        .order_by(RefreshRow.requested_at, RefreshRow.product_id)
        .limit(limit)
        .with_for_update(of=RefreshRow, skip_locked=True)
    ).all()
    by_url: dict[tuple[str, str], list[int]] = defaultdict(list)
    for refresh, url, domain in rows:
        refresh.status = "running"
        by_url[url, domain].append(refresh.product_id)
    session.commit()
    return [Job(tuple(ids), url, domain) for (url, domain), ids in by_url.items()]


def finish(
    session: Session,
    job: Job,
    outcome: Scraped | Exception,
    now: datetime.datetime,
) -> None:
    """Save the job's price for each of its products and close their refreshes."""
    error = None
    if isinstance(outcome, Exception):
        error = str(outcome) or type(outcome).__name__
    elif not outcome.available:
        error = "Not available: the page has no offer"
    elif outcome.price_cents is None:
        error = "No price found on the page"
    for refresh in session.scalars(
        select(RefreshRow).where(RefreshRow.product_id.in_(job.product_ids))
    ):
        refresh.status = "failed" if error else "done"
        refresh.finished_at = now
        refresh.error = error[:MAX_ERROR_LENGTH] if error else None
    scraped = (
        []
        if isinstance(outcome, Exception)
        else [outcome._replace(product_id=i) for i in job.product_ids]
    )
    save_data.save(session, scraped, now.date())  # commits the refreshes too
