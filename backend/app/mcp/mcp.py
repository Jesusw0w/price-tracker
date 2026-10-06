"""MCP tools for reading price history and managing trackers.

Read: list_trackers, price_history, price_summary, refresh_status.
Write: add_tracker (Amazon.es only, max N), set_target_price,
request_refresh (with a cooldown).
Optional: is_good_deal, backed by Bedrock.

There are no delete tools. Every tool uses the same service layer as /api.
"""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from app.db.database import SessionLocal
from app.products import (
    AlreadyTracked,
    Asin,
    InvalidLink,
    PricePoint,
    PriceSummary,
    ProductSummary,
    UnknownProduct,
    price_history,
    price_summary,
    request_refresh,
    summarize,
    track,
    tracked_products,
)

Days = Annotated[int, Field(ge=1)]

mcp = FastMCP(name="Amazon Price Tracker")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def list_trackers() -> list[ProductSummary]:
    """List of every tracked Amazon.es product with its latest price.

    Prices are in EUR. Price and date are None for products not scraped yet.
    Call this first to find the ASINs the other tools take.
    """
    with SessionLocal() as session:
        return [summarize(p) for p in tracked_products(session)]


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_price_history(asin: Asin, days: Days) -> list[PricePoint]:
    """Daily EUR prices of a product over the last days, oldest first.

    Today is included. Days without a scrape are missing, not zero.
    """
    with SessionLocal() as session:
        try:
            return price_history(session, asin, days)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_price_summary(asin: Asin, days: Days) -> PriceSummary:
    """Latest, lowest, highest, mean and median EUR price over the last days.

    Today is included. Price fields are None if nothing was recorded in that window.
    """
    with SessionLocal() as session:
        try:
            return price_summary(session, asin, days)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_refresh_status(request_id: str) -> None:
    """Get refresh status."""
    pass


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
def add_tracker(url: str) -> ProductSummary:
    """Start tracking a product. Only Amazon.es links are supported for now."""
    with SessionLocal() as session:
        try:
            return summarize(track(session, url))
        except (InvalidLink, AlreadyTracked) as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"idempotentHint": True, "openWorldHint": False})
def set_target_price(asin: str, price: int):
    """Set a product's target price in cents."""
    pass


@mcp.tool(annotations={"destructiveHint": False, "idempotentHint": True})
def request_refresh(asin: str):
    """Request a status refresh."""
    with SessionLocal() as session:
        try:
            return request_refresh(session, asin)
        except (InvalidLink, AlreadyTracked) as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"readOnlyHint": True})
def is_a_good_deal(asin: str):
    """Identify if a product is currently a good deal."""
    pass
