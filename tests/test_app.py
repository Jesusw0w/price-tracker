import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app import products
from app.gpu_app import app
from app.scraper.process_data import ProcessData

TRACKED = "B0BMG3FBND"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    tracked = tmp_path / "tracked.json"
    tracked.write_text(json.dumps([TRACKED]))
    monkeypatch.setattr(products, "tracked_path", tracked)
    return TestClient(app)


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
    assert not product["name"].endswith(" ")
    dates = [p["date"] for p in product["history"]]
    assert dates == sorted(set(dates))


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
