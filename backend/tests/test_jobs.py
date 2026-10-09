import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Final

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import PriceRow, ProductRow, RefreshRow
from app.scraper import jobs, run
from app.scraper.jobs import Job
from app.scraper.load_data import FetchError
from app.scraper.process_data import Scraped

NOW: Final[datetime.datetime] = datetime.datetime(2026, 10, 9, 7, tzinfo=datetime.UTC)
GPU: Final[str] = "https://shop.example/gpu"


def product(session: Session, product_id: int, url: str, owner: str = "ana") -> None:
    session.add(
        ProductRow(id=product_id, owner_id=owner, url=url, domain="shop.example")
    )


def statuses(session: Session) -> dict[int, str]:
    session.expire_all()
    return {r.product_id: r.status for r in session.scalars(select(RefreshRow))}


def test_daily_run_queues_each_tracked_product_once_a_day(session: Session) -> None:
    product(session, 1, GPU)
    product(session, 2, "https://shop.example/cpu")
    product(session, 3, "https://shop.example/old")
    session.get_one(ProductRow, 3).tracked = False
    session.add(
        RefreshRow(product_id=2, status="done", requested_at=NOW.replace(hour=1))
    )
    session.commit()

    assert jobs.queue_daily(session, NOW) == 1
    assert statuses(session) == {1: "pending", 2: "done"}
    assert jobs.queue_daily(session, NOW) == 0
    # Tomorrow: 2 again, while 1 is still waiting from today
    assert jobs.queue_daily(session, NOW + datetime.timedelta(days=1)) == 1
    assert statuses(session) == {1: "pending", 2: "pending"}


def test_claim_fetches_a_url_once_for_every_owner(session: Session) -> None:
    product(session, 1, GPU, owner="ana")
    product(session, 2, GPU, owner="bob")
    product(session, 3, "https://shop.example/cpu")
    session.commit()
    jobs.queue_daily(session, NOW)

    claimed = jobs.claim(session, limit=10)

    assert sorted(claimed) == [
        Job((1, 2), GPU, "shop.example"),
        Job((3,), "https://shop.example/cpu", "shop.example"),
    ]
    assert set(statuses(session).values()) == {"running"}
    assert jobs.claim(session, limit=10) == []


def test_finish_saves_the_price_for_every_owner_or_records_the_error(
    session: Session,
) -> None:
    product(session, 1, GPU, owner="ana")
    product(session, 2, GPU, owner="bob")
    product(session, 3, "https://shop.example/cpu")
    session.commit()
    jobs.queue_daily(session, NOW)
    gpu, cpu = sorted(jobs.claim(session, limit=10))

    jobs.finish(session, gpu, Scraped(1, "GPU", 89990, "EUR"), NOW)
    jobs.finish(session, cpu, FetchError("HTTP 503"), NOW)

    prices = session.scalars(select(PriceRow)).all()
    assert {(p.product_id, p.date, p.price_cents) for p in prices} == {
        (1, NOW.date(), 89990),
        (2, NOW.date(), 89990),
    }
    assert session.get_one(ProductRow, 2).name == "GPU"
    assert statuses(session) == {1: "done", 2: "done", 3: "failed"}
    assert session.get_one(RefreshRow, 3).error == "HTTP 503"


def test_a_page_without_a_price_is_a_failed_refresh(session: Session) -> None:
    product(session, 1, GPU)
    session.commit()
    jobs.queue_daily(session, NOW)
    [job] = jobs.claim(session, limit=10)

    jobs.finish(session, job, Scraped(1, "GPU", None, None), NOW)

    assert session.get_one(RefreshRow, 1).error == "No price found on the page"
    assert session.scalars(select(PriceRow)).all() == []


def test_an_unavailable_listing_says_so(session: Session) -> None:
    product(session, 1, GPU)
    session.commit()
    jobs.queue_daily(session, NOW)
    [job] = jobs.claim(session, limit=10)

    jobs.finish(session, job, Scraped(1, "GPU", None, None, available=False), NOW)

    assert (
        session.get_one(RefreshRow, 1).error == "Not available: the page has no offer"
    )
    assert session.get_one(ProductRow, 1).unavailable_since == NOW.date()


def test_restart_requeues_what_a_killed_scraper_left_running(session: Session) -> None:
    product(session, 1, GPU)
    session.commit()
    jobs.queue_daily(session, NOW)
    jobs.claim(session, limit=10)

    jobs.requeue_running(session)

    assert statuses(session) == {1: "pending"}


def test_drain_batch_scrapes_and_saves_every_site(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    product(session, 1, GPU)
    product(session, 2, "https://other.example/gpu")
    session.get_one(ProductRow, 2).domain = "other.example"
    session.commit()
    jobs.queue_daily(session, NOW)

    def scrape(product_id: int, url: str, domain: str) -> Scraped:
        if domain == "other.example":
            raise FetchError("HTTP 403")
        return Scraped(product_id, "GPU", 100, "EUR")

    monkeypatch.setattr(run, "scrape", scrape)
    monkeypatch.setattr(run, "SessionLocal", sessionmaker(session.get_bind()))
    with ThreadPoolExecutor(2) as pool:
        assert run.drain_batch(pool) == 2
        assert run.drain_batch(pool) == 0

    assert statuses(session) == {1: "done", 2: "failed"}
