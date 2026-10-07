import datetime
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from mcp.types import TextContent
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import PriceRow, ProductRow
from app.mcp.mcp import mcp

pytestmark = pytest.mark.anyio

TRACKED = "B0BMG3FBND"
UNTRACKED = "B000000001"
NEW = "B0BNLSDRKB"
TODAY = datetime.date.today()


@pytest.fixture
async def client(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Client[FastMCPTransport]]:
    session.add_all(
        [
            ProductRow(asin=TRACKED, name="RX 7900 XT"),
            ProductRow(asin=UNTRACKED, tracked=False),
            PriceRow(asin=TRACKED, date=TODAY, price_cents=110000),
            PriceRow(
                asin=TRACKED, date=TODAY - datetime.timedelta(2), price_cents=120000
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
                "asin": TRACKED,
                "name": "RX 7900 XT",
                "price": 1100.0,
                "price_date": TODAY.isoformat(),
            }
        ]
    }


async def test_price_history_is_oldest_first(client: Client[FastMCPTransport]) -> None:
    history = await call(client, "get_price_history", {"asin": TRACKED, "days": 7})
    assert history == {
        "result": [
            {"date": (TODAY - datetime.timedelta(2)).isoformat(), "price": 1200.0},
            {"date": TODAY.isoformat(), "price": 1100.0},
        ]
    }


async def test_price_summary_covers_only_the_window(
    client: Client[FastMCPTransport],
) -> None:
    summary = await call(client, "get_price_summary", {"asin": TRACKED, "days": 1})
    assert (summary["lowest_price"], summary["highest_price"]) == (1100.0, 1100.0)


async def test_new_trackers_can_be_refreshed_once_per_cooldown(
    client: Client[FastMCPTransport],
) -> None:
    added = await call(client, "add_tracker", {"url": f"https://amazon.es/dp/{NEW}"})
    assert added == {"asin": NEW, "name": None, "price": None, "price_date": None}
    [status] = (await call(client, "get_refresh_status", {"asins": [NEW]}))["result"]
    assert status["status"] is None

    queued = await call(client, "request_refresh", {"asins": [NEW, TRACKED]})
    assert [r["status"] for r in queued["result"]] == ["pending", "pending"]
    assert await call(client, "request_refresh", {"asins": [NEW, TRACKED]}) == queued
    assert await call(client, "get_refresh_status", {"asins": [NEW, TRACKED]}) == queued


@pytest.mark.parametrize(
    ("tool", "args", "message"),
    [
        ("get_price_summary", {"asin": "B000000009", "days": 7}, "No product"),
        ("get_refresh_status", {"asins": ["B000000009"]}, "No product"),
        ("request_refresh", {"asins": [TRACKED, UNTRACKED]}, "Not tracked"),
        ("add_tracker", {"url": TRACKED}, "Already tracking"),
        ("add_tracker", {"url": "https://www.amazon.es/s?k=rtx"}, "ASIN"),
        # Rejected by the input schema before the tool runs
        ("get_price_history", {"asin": TRACKED.lower(), "days": 7}, "pattern"),
        ("get_price_history", {"asin": TRACKED, "days": 0}, "greater than"),
        ("request_refresh", {"asins": []}, "at least 1"),
        ("request_refresh", {"asins": [TRACKED] * 51}, "at most 50"),
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
