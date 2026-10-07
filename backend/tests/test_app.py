import datetime
import logging

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import products
from app.db.database import get_session
from app.db.models import PriceRow, ProductRow
from app.main import create_app
from app.scraper import save_data
from app.scraper.process_data import Scraped, check_prices, parse_page

TRACKED = "B0BMG3FBND"
DAY = datetime.date(2023, 2, 11)


@pytest.fixture
def client(session: Session) -> TestClient:
    session.add(ProductRow(asin=TRACKED, name="RX 7900 XT", added_at=DAY))
    session.add_all(
        [
            PriceRow(asin=TRACKED, date=DAY, price_cents=115000),
            PriceRow(
                asin=TRACKED, date=DAY - datetime.timedelta(1), price_cents=110000
            ),
        ]
    )
    session.commit()
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def test_products_carry_history_oldest_first_in_euros(client: TestClient) -> None:
    [product] = client.get("/api/products").json()
    assert product["url"] == f"https://www.amazon.es/dp/{TRACKED}"
    assert product["name"] == "RX 7900 XT"
    assert product["history"] == [
        {"date": "2023-02-10", "price": 1100.0},
        {"date": "2023-02-11", "price": 1150.0},
    ]


def test_track_and_untrack(client: TestClient) -> None:
    link = "https://www.amazon.es/dp/B0BNLSDRKB?psc=1"
    created = client.post("/api/products", json={"link": link})
    assert created.status_code == 201
    assert created.json() == {
        "asin": "B0BNLSDRKB",
        "url": "https://www.amazon.es/dp/B0BNLSDRKB",
        "name": None,
        "history": [],
    }
    assert client.post("/api/products", json={"link": link}).status_code == 409
    assert client.post("/api/products", json={"link": "nope"}).status_code == 422

    assert client.delete("/api/products/B0BNLSDRKB").status_code == 204
    assert client.delete("/api/products/B0BNLSDRKB").status_code == 404
    assert [p["asin"] for p in client.get("/api/products").json()] == [TRACKED]


def test_retracking_keeps_history(client: TestClient) -> None:
    assert client.delete(f"/api/products/{TRACKED}").status_code == 204
    assert client.get("/api/products").json() == []
    retracked = client.post("/api/products", json={"link": TRACKED})
    assert retracked.status_code == 201
    assert len(retracked.json()["history"]) == 2


def test_parse_page() -> None:
    html = BeautifulSoup(
        "<title>RX 7900 XT: Amazon.es: Informática</title>"
        '<div class="a-section aok-hidden twister-plus-buying-options-price-data">'
        '[{"priceAmount": 1167.45}]</div>',
        "html.parser",
    )
    assert parse_page(TRACKED, html) == Scraped(TRACKED, "RX 7900 XT", 116745)
    assert check_prices(BeautifulSoup("<p></p>", "html.parser")) is None


def test_rescrape_same_day_overwrites_and_missing_price_is_skipped(
    session: Session,
) -> None:
    session.add(ProductRow(asin=TRACKED))
    session.commit()
    save_data.save(session, [Scraped(TRACKED, "RX 7900 XT", 100000)], DAY)
    save_data.save(session, [Scraped(TRACKED, None, 99000)], DAY)
    save_data.save(session, [Scraped(TRACKED, None, None)], DAY + datetime.timedelta(1))

    prices = session.scalars(select(PriceRow)).all()
    assert [(p.date, p.price_cents) for p in prices] == [(DAY, 99000)]
    assert session.get_one(ProductRow, TRACKED).name == "RX 7900 XT"


def test_mcp_answers_stateless_json_at_mcp() -> None:
    # The with-block runs the lifespan; without it the MCP session manager never starts
    with TestClient(create_app()) as client:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    tools = response.json()["result"]["tools"]
    assert "list_trackers" in {t["name"] for t in tools}


def test_liveness_needs_no_database() -> None:
    assert TestClient(create_app()).get("/health").json() == {"status": "ok"}


def test_readiness_reports_database_reachability(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert client.get("/health/ready").json() == {"status": "ok"}

    def down(*_: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(session, "execute", down)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unreachable"}


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
    def boom(_: Session) -> list[products.Product]:
        raise OSError("database gone")

    monkeypatch.setattr("app.routers.products.tracked_products", boom)
    response = client.get("/api/products")
    assert response.status_code == 500
    rid = response.headers["X-Request-ID"]
    [error] = [r for r in caplog.records if r.exc_info]
    assert error.__dict__["request_id"] == rid
