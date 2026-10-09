import datetime
from typing import Final

import pytest
from sqlalchemy.orm import Session

from app import products
from app.config import settings
from app.db.models import PriceRow, ProductRow, RefreshRow
from app.links import InvalidLink
from app.products import PricePoint, Product, ProductSummary

USER: Final[str] = "alice"
SOMEONE: Final[str] = "bob"
ID: Final[int] = 1
OTHER: Final[int] = 2
DAY: Final[datetime.date] = datetime.date(2023, 2, 11)
LONG_AGO: Final[datetime.datetime] = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)


def row(product_id: int, owner: str = USER, **fields: object) -> ProductRow:
    url = f"https://shop.example/p/{product_id}"
    return ProductRow(
        id=product_id, owner_id=owner, url=url, domain="shop.example", **fields
    )


def test_tracked_and_archived_products_split_on_tracked_oldest_added_first(
    session: Session,
) -> None:
    session.add_all(
        [
            row(1, added_at=DAY + datetime.timedelta(1)),
            row(3, added_at=DAY),
            row(2, added_at=DAY),
            row(4, added_at=DAY, tracked=False),
        ]
    )
    session.commit()
    assert [p.id for p in products.tracked_products(session, USER)] == [2, 3, 1]
    assert [p.id for p in products.archived_products(session, USER)] == [4]


def test_change_link_keeps_history_and_queues_the_new_page(session: Session) -> None:
    session.add(row(ID, unavailable_since=DAY))
    session.add(PriceRow(product_id=ID, date=DAY, price_cents=100))
    session.add(RefreshRow(product_id=ID, status="failed", requested_at=LONG_AGO))
    session.commit()

    moved = products.change_link(
        session, USER, ID, "https://www.amazon.es/gp/product/B0NEWASIN1?th=1"
    )

    assert moved.url == "https://www.amazon.es/dp/B0NEWASIN1"
    assert (moved.unavailable_since, len(moved.history)) == (None, 1)
    assert session.get_one(ProductRow, ID).domain == "amazon.es"
    assert session.get_one(RefreshRow, ID).status == "pending"


def test_change_link_is_for_the_owner_and_refuses_a_duplicate(
    session: Session,
) -> None:
    session.add_all([row(ID), row(OTHER), row(3, owner=SOMEONE, public=True)])
    session.commit()
    with pytest.raises(products.AlreadyTracked):
        products.change_link(session, USER, ID, "https://shop.example/p/2")
    with pytest.raises(products.UnknownProduct):
        products.change_link(session, USER, 3, "https://shop.example/p/9")
    with pytest.raises(InvalidLink):
        products.change_link(session, USER, ID, "http://shop.example/p/9")


def test_history_is_oldest_first(session: Session) -> None:
    session.add(row(ID, currency="EUR"))
    session.add_all(
        [
            PriceRow(product_id=ID, date=DAY, price_cents=115000),
            PriceRow(
                product_id=ID, date=DAY - datetime.timedelta(1), price_cents=110050
            ),
        ]
    )
    session.commit()
    [product] = products.tracked_products(session, USER)
    assert product.currency == "EUR"
    assert product.history == [
        PricePoint(date=DAY - datetime.timedelta(1), price=1100.5),
        PricePoint(date=DAY, price=1150.0),
    ]


def test_track_stores_canonical_url_and_domain(session: Session) -> None:
    product = products.track(
        session, USER, "https://www.amazon.es/x/dp/B0BNLSDRKB?psc=1"
    )
    assert product == Product(
        id=product.id,
        url="https://www.amazon.es/dp/B0BNLSDRKB",
        name=None,
        currency=None,
        public=False,
        mine=True,
        history=[],
    )
    assert session.get_one(ProductRow, product.id).domain == "amazon.es"


def test_track_same_product_by_another_link_is_already_tracked(
    session: Session,
) -> None:
    products.track(session, USER, "https://www.amazon.es/dp/B0BNLSDRKB?psc=1")
    with pytest.raises(products.AlreadyTracked):
        products.track(session, USER, "b0bnlsdrkb")


def test_users_track_the_same_product_separately(session: Session) -> None:
    link = "https://shop.example/p/1"
    mine = products.track(session, USER, link)
    theirs = products.track(session, SOMEONE, link)
    assert mine.id != theirs.id


def test_users_see_their_own_and_public_products_only(session: Session) -> None:
    session.add_all(
        [
            row(1),
            row(2, owner=SOMEONE),
            row(3, owner=SOMEONE, public=True),
            row(4, owner=SOMEONE, public=True, tracked=False),
        ]
    )
    session.commit()
    seen = products.tracked_products(session, USER)
    assert [(p.id, p.mine) for p in seen] == [(1, True), (3, False)]
    assert products.archived_products(session, USER) == []
    with pytest.raises(products.UnknownProduct, match="2"):
        products.price_history(session, USER, 2, 7)
    with pytest.raises(products.UnknownProduct, match="2"):
        products.queue_refresh(session, USER, [1, 2])
    assert products.price_summary(session, USER, 3, 7).id == 3


def test_only_the_owner_shares_archives_or_deletes(session: Session) -> None:
    session.add(row(ID, owner=SOMEONE, public=True))
    session.commit()
    with pytest.raises(products.UnknownProduct):
        products.set_public(session, USER, ID, False)
    with pytest.raises(products.NotTracked):
        products.archive_product(session, USER, ID)
    with pytest.raises(products.UnknownProduct):
        products.delete_product(session, USER, ID)

    assert not products.set_public(session, SOMEONE, ID, False).public
    assert products.tracked_products(session, USER) == []


def test_tracker_cap_counts_each_user_alone(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_trackers", 1)
    products.track(session, SOMEONE, "https://shop.example/p/1")
    products.track(session, USER, "https://shop.example/p/2")


def test_track_rejects_non_https_links(session: Session) -> None:
    with pytest.raises(InvalidLink):
        products.track(session, USER, "http://shop.example/p/1")


def test_track_stops_at_the_tracker_cap(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_trackers", 1)
    products.track(session, USER, "https://shop.example/p/1")
    with pytest.raises(products.TooManyTrackers):
        products.track(session, USER, "https://shop.example/p/2")


def test_retracking_keeps_history(session: Session) -> None:
    session.add(row(ID, tracked=False))
    session.add(PriceRow(product_id=ID, date=DAY, price_cents=100000))
    session.commit()
    product = products.track(session, USER, f"https://shop.example/p/{ID}")
    assert product.history == [PricePoint(date=DAY, price=1000.0)]


def test_product_summary() -> None:
    url = "https://shop.example/p/1"
    product = Product(
        id=ID,
        url=url,
        name="RTX 5070Ti",
        currency="EUR",
        history=[
            PricePoint(date=datetime.date(2026, 10, 2), price=100.5),
            PricePoint(date=datetime.date(2026, 10, 5), price=200.0),
        ],
    )
    assert products.summarize(product) == ProductSummary(
        id=ID,
        url=url,
        name="RTX 5070Ti",
        currency="EUR",
        price=200.0,
        price_date=datetime.date(2026, 10, 5),
    )
    new_product = Product(id=ID, url=url, history=[])
    assert products.summarize(new_product) == ProductSummary(id=ID, url=url)


def test_price_history_keeps_cutoff_day_to_today_of_one_product_oldest_first(
    session: Session,
) -> None:
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(7)
    session.add_all([row(ID), row(OTHER)])
    session.add_all(
        [
            PriceRow(product_id=ID, date=today, price_cents=110050),
            PriceRow(product_id=OTHER, date=today, price_cents=99900),
            PriceRow(product_id=ID, date=cutoff, price_cents=115000),
            PriceRow(
                product_id=ID,
                date=cutoff - datetime.timedelta(1),
                price_cents=120000,
            ),
        ]
    )
    session.commit()
    assert products.price_history(session, USER, ID, 7) == [
        PricePoint(date=cutoff, price=1150.0),
        PricePoint(date=today, price=1100.5),
    ]


def test_price_history_rejects_unknown_product(session: Session) -> None:
    with pytest.raises(products.UnknownProduct):
        products.price_history(session, USER, ID, 7)


def test_price_summary_of_the_window(session: Session) -> None:
    today = datetime.date.today()
    session.add(row(ID, name="RTX 5070 Ti", currency="EUR"))
    session.add_all(
        [
            PriceRow(product_id=ID, date=today, price_cents=100000),
            PriceRow(
                product_id=ID, date=today - datetime.timedelta(1), price_cents=120000
            ),
            PriceRow(
                product_id=ID, date=today - datetime.timedelta(2), price_cents=110050
            ),
            PriceRow(product_id=ID, date=today - datetime.timedelta(30), price_cents=1),
        ]
    )
    session.commit()
    assert products.price_summary(session, USER, ID, 7) == products.PriceSummary(
        id=ID,
        name="RTX 5070 Ti",
        currency="EUR",
        latest_price=1000.0,
        highest_price=1200.0,
        lowest_price=1000.0,
        mean_price=1100.17,
        median_price=1100.5,
    )


def test_price_summary_without_prices_in_the_window_is_empty(session: Session) -> None:
    session.add(row(ID))
    session.add(
        PriceRow(
            product_id=ID,
            date=datetime.date.today() - datetime.timedelta(30),
            price_cents=100000,
        )
    )
    session.commit()
    assert products.price_summary(session, USER, ID, 7) == products.PriceSummary(
        id=ID, name=None, currency=None
    )


def test_price_summary_rejects_unknown_product(session: Session) -> None:
    with pytest.raises(products.UnknownProduct):
        products.price_summary(session, USER, ID, 7)


def test_queue_refresh_creates_pending_request(session: Session) -> None:
    session.add(row(ID))
    session.commit()
    [info] = products.queue_refresh(session, USER, [ID])
    assert info.status == "pending"
    assert info.requested_at is not None


def test_queue_refresh_within_cooldown_returns_same_request(session: Session) -> None:
    session.add(row(ID))
    session.commit()
    first = products.queue_refresh(session, USER, [ID])
    assert products.queue_refresh(session, USER, [ID]) == first


def test_queue_refresh_after_cooldown_requeues_and_clears_last_outcome(
    session: Session,
) -> None:
    session.add(row(ID))
    session.add(
        RefreshRow(
            product_id=ID,
            status="failed",
            requested_at=LONG_AGO,
            finished_at=LONG_AGO,
            error="HTTP 503",
        )
    )
    session.commit()
    [info] = products.queue_refresh(session, USER, [ID])
    assert (info.status, info.finished_at, info.error) == ("pending", None, None)


def test_queue_refresh_leaves_running_request_alone(session: Session) -> None:
    session.add(row(ID))
    session.add(RefreshRow(product_id=ID, status="running", requested_at=LONG_AGO))
    session.commit()
    [info] = products.queue_refresh(session, USER, [ID])
    assert info.status == "running"


def test_queue_refresh_queues_nothing_if_one_product_is_untracked(
    session: Session,
) -> None:
    session.add_all([row(ID), row(OTHER, tracked=False)])
    session.commit()
    with pytest.raises(products.NotTracked, match=str(OTHER)):
        products.queue_refresh(session, USER, [ID, OTHER])
    assert session.get(RefreshRow, ID) is None


def test_queue_refresh_names_every_unknown_product(session: Session) -> None:
    session.add(row(ID))
    session.commit()
    with pytest.raises(products.UnknownProduct, match="8, 9"):
        products.queue_refresh(session, USER, [ID, 8, 9])
    assert session.get(RefreshRow, ID) is None


def test_refresh_status_of_never_refreshed_product(session: Session) -> None:
    session.add(row(ID))
    session.add_all(
        [
            PriceRow(product_id=ID, date=DAY, price_cents=100000),
            PriceRow(product_id=ID, date=DAY - datetime.timedelta(1), price_cents=1),
        ]
    )
    session.commit()
    assert products.refresh_status(session, USER, [ID]) == [
        products.RefreshInfo(product_id=ID, last_price_date=DAY)
    ]


def test_refresh_status_reports_why_the_last_refresh_failed(session: Session) -> None:
    session.add(row(ID))
    session.add(
        RefreshRow(
            product_id=ID,
            status="failed",
            requested_at=LONG_AGO,
            finished_at=LONG_AGO,
            error="HTTP 503",
        )
    )
    session.commit()
    [info] = products.refresh_status(session, USER, [ID])
    assert (info.status, info.error) == ("failed", "HTTP 503")


def test_refresh_status_keeps_request_order_without_duplicates(
    session: Session,
) -> None:
    session.add_all([row(ID), row(OTHER)])
    session.commit()
    infos = products.refresh_status(session, USER, [OTHER, ID, OTHER])
    assert [info.product_id for info in infos] == [OTHER, ID]


def test_refresh_status_rejects_unknown_product(session: Session) -> None:
    with pytest.raises(products.UnknownProduct):
        products.refresh_status(session, USER, [ID])
