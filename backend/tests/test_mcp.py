import datetime
from collections.abc import AsyncIterator
from typing import Any, Final

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from mcp.types import TextContent
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import PriceRow, ProductRow
from app.mcp.mcp import mcp

pytestmark = pytest.mark.anyio

TRACKED: Final[int] = 1
UNTRACKED: Final[int] = 2
SOMEONE_ELSES: Final[int] = 3
TRACKED_URL: Final[str] = "https://www.amazon.es/dp/B0BMG3FBND"
NEW_URL: Final[str] = "https://shop.example/p/gpu"
TODAY: Final[datetime.date] = datetime.date.today()


@pytest.fixture
async def client(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Client[FastMCPTransport]]:
    session.add_all(
        [
            ProductRow(
                id=TRACKED,
                owner_id=settings.owner_sub,
                url=TRACKED_URL,
                domain="amazon.es",
                name="RX 7900 XT",
                currency="EUR",
            ),
            ProductRow(
                id=UNTRACKED,
                owner_id=settings.owner_sub,
                url="https://shop.example/p/old",
                domain="shop.example",
                tracked=False,
            ),
            ProductRow(
                id=SOMEONE_ELSES,
                owner_id="someone-else",
                url="https://shop.example/p/private",
                domain="shop.example",
            ),
            PriceRow(product_id=TRACKED, date=TODAY, price_cents=110000),
            PriceRow(
                product_id=TRACKED,
                date=TODAY - datetime.timedelta(2),
                price_cents=120000,
            ),
        ]
    )
    session.commit()
    monkeypatch.setattr("app.mcp.mcp.SessionLocal", sessionmaker(session.get_bind()))
    async with Client(mcp) as client:
        yield client


async def call(
    client: Client[FastMCPTransport], tool: str, args: dict[str, Any]
) -> dict[str, Any]:
    result = await client.call_tool(tool, args)
    assert result.structured_content is not None
    return result.structured_content


async def test_tool_names_and_read_only_hints(
    client: Client[FastMCPTransport],
) -> None:
    tools = await client.list_tools()
    read_only = {t.name for t in tools if (a := t.annotations) and a.read_only_hint}
    writes = {t.name for t in tools} - read_only
    assert read_only == {
        "list_trackers",
        "get_price_history",
        "get_price_summary",
        "get_refresh_status",
    }
    assert writes == {"add_tracker", "request_refresh"}


async def test_list_trackers_gives_latest_price(
    client: Client[FastMCPTransport],
) -> None:
    assert await call(client, "list_trackers", {}) == {
        "result": [
            {
                "id": TRACKED,
                "url": TRACKED_URL,
                "name": "RX 7900 XT",
                "currency": "EUR",
                "price": 1100.0,
                "price_date": TODAY.isoformat(),
                "unavailable_since": None,
            }
        ]
    }


async def test_price_history_is_oldest_first(client: Client[FastMCPTransport]) -> None:
    args = {"product_id": TRACKED, "days": 7}
    history = await call(client, "get_price_history", args)
    assert history == {
        "result": [
            {"date": (TODAY - datetime.timedelta(2)).isoformat(), "price": 1200.0},
            {"date": TODAY.isoformat(), "price": 1100.0},
        ]
    }


async def test_price_summary_covers_only_the_window(
    client: Client[FastMCPTransport],
) -> None:
    args = {"product_id": TRACKED, "days": 1}
    summary = await call(client, "get_price_summary", args)
    assert (summary["lowest_price"], summary["highest_price"]) == (1100.0, 1100.0)


async def test_new_trackers_can_be_refreshed_once_per_cooldown(
    client: Client[FastMCPTransport],
) -> None:
    added = await call(client, "add_tracker", {"url": NEW_URL + "#specs"})
    new = added["id"]
    assert added == {
        "id": new,
        "url": NEW_URL,
        "name": None,
        "currency": None,
        "price": None,
        "price_date": None,
        "unavailable_since": None,
    }
    ids = {"product_ids": [new]}
    [status] = (await call(client, "get_refresh_status", ids))["result"]
    assert status["status"] is None

    both = {"product_ids": [new, TRACKED]}
    queued = await call(client, "request_refresh", both)
    assert [r["status"] for r in queued["result"]] == ["pending", "pending"]
    assert await call(client, "request_refresh", both) == queued
    assert await call(client, "get_refresh_status", both) == queued


@pytest.mark.parametrize(
    ("tool", "args", "message"),
    [
        ("get_price_summary", {"product_id": 9, "days": 7}, "No product"),
        ("get_refresh_status", {"product_ids": [9]}, "No product"),
        ("get_price_history", {"product_id": SOMEONE_ELSES, "days": 7}, "No product"),
        ("request_refresh", {"product_ids": [TRACKED, UNTRACKED]}, "Not tracked"),
        ("add_tracker", {"url": TRACKED_URL}, "Already tracking"),
        ("add_tracker", {"url": "http://shop.example/p/1"}, "https://"),
        ("add_tracker", {"url": "https://10.0.0.1/admin"}, "public website"),
        # Rejected by the input schema before the tool runs
        ("get_price_history", {"product_id": 0, "days": 7}, "greater than"),
        ("get_price_history", {"product_id": TRACKED, "days": 0}, "greater than"),
        ("request_refresh", {"product_ids": []}, "at least 1"),
        ("request_refresh", {"product_ids": [TRACKED] * 51}, "at most 50"),
    ],
)
async def test_errors_reach_the_agent_with_a_reason(
    client: Client[FastMCPTransport], tool: str, args: dict[str, Any], message: str
) -> None:
    result = await client.call_tool(tool, args, raise_on_error=False)
    assert result.is_error
    [content] = result.content
    assert isinstance(content, TextContent)
    assert message in content.text
