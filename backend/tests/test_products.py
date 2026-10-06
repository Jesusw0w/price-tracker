import datetime

import pytest
from sqlalchemy.orm import Session

from app import products
from app.db.models import PriceRow, ProductRow
from app.products import PricePoint, Product, ProductSummary

ASIN = "B0BMG3FBND"
DAY = datetime.date(2023, 2, 11)


@pytest.mark.parametrize(
    ("link", "asin"),
    [
        (
            "https://www.amazon.es/XFX-Radeon/dp/B0BNLSDRKB/ref=sr_1_2?k=amd",
            "B0BNLSDRKB",
        ),
        ("https://www.amazon.es/gp/product/B0BNLSDRKB?th=1", "B0BNLSDRKB"),
        (" b0bnlsdrkb ", "B0BNLSDRKB"),
        ("https://www.amazon.es/s?k=rtx+4070", None),
        ("rtx 4070 ti", None),
    ],
)
def test_parse_asin(link: str, asin: str | None) -> None:
    assert products.parse_asin(link) == asin


def test_tracked_products_skip_untracked_and_list_oldest_added_first(
    session: Session,
) -> None:
    session.add_all(
        [
            ProductRow(asin="B000000001", added_at=DAY + datetime.timedelta(1)),
            ProductRow(asin="B000000003", added_at=DAY),
            ProductRow(asin="B000000002", added_at=DAY),
            ProductRow(asin="B000000004", added_at=DAY, tracked=False),
        ]
    )
    session.commit()
    assert [p.asin for p in products.tracked_products(session)] == [
        "B000000002",
        "B000000003",
        "B000000001",
    ]


def test_history_is_oldest_first_in_euros(session: Session) -> None:
    session.add(ProductRow(asin=ASIN))
    session.add_all(
        [
            PriceRow(asin=ASIN, date=DAY, price_cents=115000),
            PriceRow(asin=ASIN, date=DAY - datetime.timedelta(1), price_cents=110050),
        ]
    )
    session.commit()
    [product] = products.tracked_products(session)
    assert product.history == [
        PricePoint(date=DAY - datetime.timedelta(1), price=1100.5),
        PricePoint(date=DAY, price=1150.0),
    ]


def test_track_new_product_starts_without_name_or_history(session: Session) -> None:
    product = products.track(session, "https://www.amazon.es/dp/B0BNLSDRKB?psc=1")
    assert product == products.Product(
        asin="B0BNLSDRKB",
        url="https://www.amazon.es/dp/B0BNLSDRKB",
        name=None,
        history=[],
    )
    assert session.get_one(ProductRow, "B0BNLSDRKB").tracked


def test_track_rejects_links_without_asin(session: Session) -> None:
    with pytest.raises(products.InvalidLink):
        products.track(session, "https://www.amazon.es/s?k=rtx+4070")


def test_track_rejects_already_tracked(session: Session) -> None:
    session.add(ProductRow(asin=ASIN))
    session.commit()
    with pytest.raises(products.AlreadyTracked):
        products.track(session, ASIN)


def test_retracking_keeps_history(session: Session) -> None:
    session.add(ProductRow(asin=ASIN, tracked=False))
    session.add(PriceRow(asin=ASIN, date=DAY, price_cents=100000))
    session.commit()
    product = products.track(session, ASIN)
    assert product.history == [PricePoint(date=DAY, price=1000.0)]


def test_product_summary() -> None:
    product = Product(
        asin=ASIN,
        url=products.product_url(ASIN),
        name="RTX 5070Ti",
        history=[
            PricePoint(date=datetime.date(2026, 10, 2), price=100.5),
            PricePoint(date=datetime.date(2026, 10, 5), price=200.0),
        ],
    )
    new_product = Product(
        asin=ASIN,
        url=products.product_url(ASIN),
        name=None,
        history=[],
    )
    assert products.summarize(product) == ProductSummary(
        asin=ASIN,
        name="RTX 5070Ti",
        price=200.0,
        price_date=datetime.date(2026, 10, 5),
    )
    assert products.summarize(new_product) == ProductSummary(
        asin=ASIN, name=None, price=None, price_date=None
    )


def test_price_history_keeps_cutoff_day_to_today_of_one_product_oldest_first(
    session: Session,
) -> None:
    other = "B000000001"
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(7)
    session.add_all([ProductRow(asin=ASIN), ProductRow(asin=other)])
    session.add_all(
        [
            PriceRow(asin=ASIN, date=today, price_cents=110050),
            PriceRow(asin=other, date=today, price_cents=99900),
            PriceRow(asin=ASIN, date=cutoff, price_cents=115000),
            PriceRow(
                asin=ASIN, date=cutoff - datetime.timedelta(1), price_cents=120000
            ),
        ]
    )
    session.commit()
    assert products.price_history(session, ASIN, 7) == [
        PricePoint(date=cutoff, price=1150.0),
        PricePoint(date=today, price=1100.5),
    ]
