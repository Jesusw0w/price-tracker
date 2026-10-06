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
    Asin,
    PricePoint,
    PriceSummary,
    ProductSummary,
    UnknownProduct,
    price_history,
    price_summary,
    summarize,
    tracked_products,
)

mcp = FastMCP(name="Amazon Price Tracker")


@mcp.tool(annotations={"readOnlyHint": True})
def list_trackers() -> list[ProductSummary]:
    """List of every tracked Amazon.es product with its latest price.

    Prices are in EUR. Price and date are None for products not scraped yet.
    Call this first to find the ASINs the other tools take.
    """
    with SessionLocal() as session:
        return [summarize(p) for p in tracked_products(session)]


@mcp.tool(annotations={"readOnlyHint": True})
def get_price_history(asin: str, days: int) -> list[PricePoint]:
    """Get the price history for a product for the last x days, today included.

    Prices are in EUR.
    """
    with SessionLocal() as session:
        return price_history(session=session, asin=asin, days=days)


@mcp.tool(annotations={"readOnlyHint": True})
def get_price_summary(asin: Asin, days: Annotated[int, Field(ge=1)]) -> PriceSummary:
    """Get the price summary."""
    with SessionLocal() as session:
        try:
            return price_summary(session, asin, days)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool
def get_refresh_status(request_id: str):
    """Get refresh status."""
    pass


@mcp.tool
def add_tracker(url: str):
    """Start tracking a product. Only Amazon.es links are supported for now."""
    pass


@mcp.tool
def set_target_price(asin: str, price: int):
    """Set a product's target price in cents."""
    pass


@mcp.tool
def request_refresh(asin: str):
    """Request a status refresh."""
    pass


@mcp.tool
def is_a_good_deal(asin: str):
    """Identify if a product is currently a good deal."""
    pass
