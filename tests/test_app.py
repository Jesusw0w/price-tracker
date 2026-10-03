import json
import logging
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app import products
from app.main import create_app
from app.scraper.process_data import ProcessData

TRACKED = "B0BMG3FBND"

# Quirks of real scrapes: trailing space, timestamp vs date, re-scrape, N/A price
HISTORY = """GPU|URL|Price|Date
RX 7900 XT |https://www.amazon.es/X/dp/B0BMG3FBND/ref=1|1167.45|2023-02-11 10:00:00
RX 7900 XT |https://www.amazon.es/dp/B0BMG3FBND|1150.0|2023-02-11
RX 7900 XT |https://www.amazon.es/dp/B0BMG3FBND|N/A|2023-02-12
RX 7900 XT |https://www.amazon.es/dp/B0BMG3FBND|1100.0|2023-02-10
"""


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    tracked = tmp_path / "tracked.json"
    tracked.write_text(json.dumps([TRACKED]))
    history = tmp_path / "history.csv"
    history.write_text(HISTORY, encoding="utf-8")
    monkeypatch.setattr(products, "tracked_path", tracked)
    monkeypatch.setattr(products, "historical_data_path", history)
    return TestClient(create_app())


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


def test_products_carry_cleaned_history(client: TestClient) -> None:
    [product] = client.get("/api/products").json()
    assert product["url"] == f"https://www.amazon.es/dp/{TRACKED}"
    assert product["name"] == "RX 7900 XT"
    assert product["history"] == [
        {"date": "2023-02-10", "price": 1100.0},
        {"date": "2023-02-11", "price": 1150.0},
    ]


def test_starts_empty_without_data_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tracked = tmp_path / "new" / "tracked.json"
    monkeypatch.setattr(products, "tracked_path", tracked)
    monkeypatch.setattr(products, "historical_data_path", tmp_path / "none.csv")
    client = TestClient(create_app())
    assert client.get("/api/products").json() == []
    created = client.post("/api/products", json={"link": TRACKED}).json()
    assert created["history"] == []
    assert json.loads(tracked.read_text()) == [TRACKED]


def test_track_and_untrack(client: TestClient) -> None:
    link = "https://www.amazon.es/dp/B0BNLSDRKB?psc=1"
    created = client.post("/api/products", json={"link": link})
    assert created.status_code == 201
    assert created.json()["asin"] == "B0BNLSDRKB"
    assert client.post("/api/products", json={"link": link}).status_code == 409
    assert client.post("/api/products", json={"link": "nope"}).status_code == 422

    assert client.delete("/api/products/B0BNLSDRKB").status_code == 204
    assert client.delete("/api/products/B0BNLSDRKB").status_code == 404
    assert [p["asin"] for p in client.get("/api/products").json()] == [TRACKED]


def test_check_prices() -> None:
    html = BeautifulSoup(
        '<div class="a-section aok-hidden twister-plus-buying-options-price-data">'
        '[{"priceAmount": 989.0}]</div>',
        "html.parser",
    )
    assert ProcessData.check_prices(html) == [{"priceAmount": 989.0}]
    assert ProcessData.check_prices(BeautifulSoup("<p></p>", "html.parser")) is None


def test_calls_are_logged_with_their_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.access")
    rid = client.get("/api/products").headers["X-Request-ID"]
    [record] = [r for r in caplog.records if r.name == "app.access"]
    assert record.__dict__["request_id"] == rid
    assert record.getMessage().startswith("GET /api/products 200 ")


def test_unhandled_errors_are_logged_and_answered_500(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom() -> list[str]:
        raise OSError("disk gone")

    monkeypatch.setattr("app.routers.products.load_tracked", boom)
    response = client.get("/api/products")
    assert response.status_code == 500
    rid = response.headers["X-Request-ID"]
    [error] = [r for r in caplog.records if r.exc_info]
    assert error.__dict__["request_id"] == rid
