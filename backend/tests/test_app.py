import datetime
import logging
from typing import Final

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import products
from app.config import settings
from app.db.database import get_session
from app.db.models import PriceRow, ProductRow
from app.main import create_app

TRACKED: Final[int] = 1
DAY: Final[datetime.date] = datetime.date(2023, 2, 11)
OWNER: Final[dict[str, str]] = {
    "Authorization": f"Bearer {settings.api_token.get_secret_value()}"
}
MCP_ACCEPT: Final[dict[str, str]] = {"Accept": "application/json, text/event-stream"}
TOOLS_LIST: Final[dict[str, object]] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
}


@pytest.fixture
def client(session: Session) -> TestClient:
    session.add(
        ProductRow(
            id=TRACKED,
            url="https://www.amazon.es/dp/B0BMG3FBND",
            domain="amazon.es",
            name="RX 7900 XT",
            currency="EUR",
            added_at=DAY,
        )
    )
    session.add_all(
        [
            PriceRow(product_id=TRACKED, date=DAY, price_cents=115000),
            PriceRow(
                product_id=TRACKED,
                date=DAY - datetime.timedelta(1),
                price_cents=110000,
            ),
        ]
    )
    session.commit()
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app, headers=OWNER)


def test_products_carry_history_oldest_first(client: TestClient) -> None:
    [product] = client.get("/api/products").json()
    assert product["url"] == "https://www.amazon.es/dp/B0BMG3FBND"
    assert (product["name"], product["currency"]) == ("RX 7900 XT", "EUR")
    assert product["history"] == [
        {"date": "2023-02-10", "price": 1100.0},
        {"date": "2023-02-11", "price": 1150.0},
    ]


def test_track_and_untrack(client: TestClient) -> None:
    link = "https://shop.example/p/gpu?variant=7#reviews"
    created = client.post("/api/products", json={"link": link})
    assert created.status_code == 201
    new = created.json()
    assert new == {
        "id": new["id"],
        "url": "https://shop.example/p/gpu?variant=7",
        "name": None,
        "currency": None,
        "history": [],
    }
    assert client.post("/api/products", json={"link": link}).status_code == 409
    assert client.post("/api/products", json={"link": "nope"}).status_code == 422
    refused = client.post("/api/products", json={"link": "https://192.168.1.1/"})
    assert refused.status_code == 422

    assert client.delete(f"/api/products/{new['id']}").status_code == 204
    assert client.delete(f"/api/products/{new['id']}").status_code == 404
    assert [p["id"] for p in client.get("/api/products").json()] == [TRACKED]


def test_retracking_keeps_history(client: TestClient) -> None:
    assert client.delete(f"/api/products/{TRACKED}").status_code == 204
    assert client.get("/api/products").json() == []
    retracked = client.post("/api/products", json={"link": "B0BMG3FBND"})
    assert retracked.status_code == 201
    assert len(retracked.json()["history"]) == 2


def test_mcp_answers_stateless_json_at_mcp() -> None:
    # The with-block runs the lifespan; without it the MCP session manager never starts
    with TestClient(create_app()) as client:
        response = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_ACCEPT, **OWNER})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    tools = response.json()["result"]["tools"]
    assert "list_trackers" in {t["name"] for t in tools}


@pytest.mark.parametrize(
    "auth", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic x"}]
)
def test_api_and_mcp_refuse_calls_without_the_owner_token(
    auth: dict[str, str],
) -> None:
    with TestClient(create_app()) as client:
        api = client.get("/api/products", headers=auth)
        mcp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_ACCEPT, **auth})
    assert api.status_code == 401
    assert api.headers["WWW-Authenticate"] == "Bearer"
    assert mcp.status_code == 401


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
