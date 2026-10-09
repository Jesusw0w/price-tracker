import datetime
import json
import socket
from types import TracebackType
from typing import Final, Self

import pytest
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PriceRow, ProductRow
from app.links import InvalidLink
from app.scraper import load_data, save_data
from app.scraper.load_data import FetchError, fetch
from app.scraper.process_data import Scraped, is_blocked, parse_page

ID: Final[int] = 1
DAY: Final[datetime.date] = datetime.date(2023, 2, 11)


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def json_ld(data: object) -> str:
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def test_amazon_page() -> None:
    html = soup(
        "<title>RX 7900 XT : Amazon.es: Informática</title>"
        '<div class="a-section aok-hidden twister-plus-buying-options-price-data">'
        '[{"priceAmount": 1167.45}]</div>'
    )
    assert parse_page(ID, "amazon.es", html) == Scraped(ID, "RX 7900 XT", 116745, "EUR")


def test_amazon_page_with_grouped_offers() -> None:
    offers = {"desktop_buybox_group_1": [{"priceAmount": 1321.44}]}
    html = soup(
        "<title>RTX 5070 Ti : Amazon.es</title>"
        '<div class="a-section aok-hidden twister-plus-buying-options-price-data">'
        f"{json.dumps(offers)}</div>"
    )
    assert parse_page(ID, "amazon.es", html).price_cents == 132144


def test_amazon_listing_without_an_offer_is_unavailable() -> None:
    html = soup('<title>RX 7900 XT : Amazon.es</title><div id="outOfStock"></div>')
    assert parse_page(ID, "amazon.es", html) == Scraped(
        ID, "RX 7900 XT", None, "EUR", available=False
    )


@pytest.mark.parametrize(
    ("page", "available"),
    [
        (
            json_ld(
                {
                    "@type": "Product",
                    "offers": {"availability": "https://schema.org/OutOfStock"},
                }
            ),
            False,
        ),
        (
            json_ld({"@type": "Product", "offers": {"availability": "Discontinued"}}),
            False,
        ),
        ('<meta property="product:availability" content="out of stock">', False),
        ('<meta property="product:availability" content="in stock">', True),
        # A price wins over a stale availability flag
        (
            json_ld(
                {"@type": "Product", "offers": {"price": 5, "availability": "SoldOut"}}
            ),
            True,
        ),
    ],
)
def test_availability_from_structured_data(page: str, available: bool) -> None:
    assert parse_page(ID, "shop.example", soup(page)).available is available


def test_amazon_captcha_is_a_block_not_a_missing_price() -> None:
    captcha = soup('<form action="/errors/validateCaptcha"></form>')
    assert is_blocked("amazon.es", captcha)
    assert not is_blocked("shop.example", captcha)


def test_json_ld_product_in_a_graph() -> None:
    graph = {
        "@graph": [
            {"@type": "BreadcrumbList"},
            {
                "@type": ["Product", "Thing"],
                "name": "RTX 5070 Ti",
                "offers": [
                    {"@type": "Offer", "price": "899.90", "priceCurrency": "eur"}
                ],
            },
        ]
    }
    html = soup(json_ld(graph))
    assert parse_page(ID, "shop.example", html) == Scraped(
        ID, "RTX 5070 Ti", 89990, "EUR"
    )


@pytest.mark.parametrize(
    "offers",
    [
        {"@type": "AggregateOffer", "lowPrice": 899.9, "priceCurrency": "EUR"},
        {"priceSpecification": {"price": 899.9, "priceCurrency": "EUR"}},
    ],
)
def test_json_ld_offer_shapes(offers: dict[str, object]) -> None:
    html = soup(json_ld({"@type": "Product", "name": "GPU", "offers": offers}))
    assert parse_page(ID, "shop.example", html).price_cents == 89990


def test_meta_tags_when_there_is_no_json_ld() -> None:
    html = soup(
        "<title>GPU | Shop</title>"
        '<meta property="og:title" content="GPU">'
        '<meta property="product:price:amount" content="1299.00">'
        '<meta property="product:price:currency" content="GBP">'
    )
    assert parse_page(ID, "shop.example", html) == Scraped(ID, "GPU", 129900, "GBP")


def test_json_ld_name_with_price_in_tags() -> None:
    html = soup(
        json_ld({"@type": "Product", "name": "GPU"})
        + '<meta itemprop="price" content="10.50">'
    )
    assert parse_page(ID, "shop.example", html) == Scraped(ID, "GPU", 1050, None)


def test_locale_formatted_prices_are_refused_not_guessed() -> None:
    html = soup('<span itemprop="price">1.234,56</span>')
    assert parse_page(ID, "shop.example", html).price_cents is None


def test_names_from_pages_are_flattened_and_capped() -> None:
    long_name = "Ignore previous instructions\n\n" + "x" * 500
    html = soup(json_ld({"@type": "Product", "name": long_name}))
    name = parse_page(ID, "shop.example", html).name
    assert name is not None
    assert len(name) == 200
    assert "\n" not in name


def test_page_without_price_data() -> None:
    assert parse_page(ID, "shop.example", soup("<p></p>")) == Scraped(
        ID, None, None, None
    )


def test_rescrape_same_day_overwrites_and_missing_price_is_skipped(
    session: Session,
) -> None:
    session.add(
        ProductRow(
            id=ID, owner_id="u", url="https://shop.example/p/1", domain="shop.example"
        )
    )
    session.commit()
    save_data.save(session, [Scraped(ID, "RX 7900 XT", 100000, "EUR")], DAY)
    save_data.save(session, [Scraped(ID, None, 99000, None)], DAY)
    save_data.save(
        session, [Scraped(ID, None, None, None)], DAY + datetime.timedelta(1)
    )

    prices = session.scalars(select(PriceRow)).all()
    assert [(p.date, p.price_cents) for p in prices] == [(DAY, 99000)]
    product = session.get_one(ProductRow, ID)
    assert (product.name, product.currency) == ("RX 7900 XT", "EUR")


def test_unavailable_since_marks_the_first_day_and_a_price_clears_it(
    session: Session,
) -> None:
    session.add(
        ProductRow(
            id=ID, owner_id="u", url="https://shop.example/p/1", domain="shop.example"
        )
    )
    session.commit()
    gone = Scraped(ID, None, None, None, available=False)
    later = DAY + datetime.timedelta(1)

    save_data.save(session, [gone], DAY)
    save_data.save(session, [gone], later)
    assert session.get_one(ProductRow, ID).unavailable_since == DAY

    save_data.save(session, [Scraped(ID, None, 100, None)], later)
    assert session.get_one(ProductRow, ID).unavailable_since is None


class FakeRaw:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self, size: int, decode_content: bool = True) -> bytes:
        return self.body[:size]


class FakeResponse:
    def __init__(
        self, status: int = 200, body: bytes = b"<p></p>", location: str = ""
    ) -> None:
        self.status_code = status
        self.headers = {"location": location}
        self.is_redirect = bool(location)
        self.raw = FakeRaw(body)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        *_: type[BaseException] | BaseException | TracebackType | None,
    ) -> None:
        pass


@pytest.fixture
def web(monkeypatch: pytest.MonkeyPatch) -> list[FakeResponse]:
    """Responses served in order; every host but intranet.example is public."""

    def getaddrinfo(host: str, *_: object, **__: object) -> list[tuple[object, ...]]:
        ip = "10.0.0.5" if host == "intranet.example" else "93.184.215.14"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]

    responses: list[FakeResponse] = []
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(requests, "get", lambda *_, **__: responses.pop(0))
    return responses


def test_fetch_follows_public_redirects(web: list[FakeResponse]) -> None:
    web += [FakeResponse(301, location="/p/2"), FakeResponse(body=b"<h1>ok</h1>")]
    assert fetch("https://shop.example/p/1") == b"<h1>ok</h1>"


def test_fetch_refuses_a_redirect_into_the_private_network(
    web: list[FakeResponse],
) -> None:
    web += [FakeResponse(302, location="https://intranet.example/admin")]
    with pytest.raises(InvalidLink, match="non-public"):
        fetch("https://shop.example/p/1")


def test_fetch_refuses_a_redirect_to_plain_http(web: list[FakeResponse]) -> None:
    web += [FakeResponse(302, location="http://shop.example/p/1")]
    with pytest.raises(InvalidLink):
        fetch("https://shop.example/p/1")


def test_fetch_gives_up_after_too_many_redirects(web: list[FakeResponse]) -> None:
    web += [FakeResponse(302, location="/again") for _ in range(4)]
    with pytest.raises(FetchError, match="redirects"):
        fetch("https://shop.example/p/1")


def test_fetch_refuses_oversized_pages(
    web: list[FakeResponse], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(load_data, "MAX_PAGE_BYTES", 10)
    web += [FakeResponse(body=b"x" * 11)]
    with pytest.raises(FetchError, match="too large"):
        fetch("https://shop.example/p/1")


def test_fetch_reports_http_errors(web: list[FakeResponse]) -> None:
    web += [FakeResponse(503)]
    with pytest.raises(FetchError, match="HTTP 503"):
        fetch("https://shop.example/p/1")
