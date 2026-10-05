"""MCP tools for reading price history and managing trackers.

Read: list_trackers, price_history, price_summary, refresh_status.
Write: add_tracker (Amazon.es only, max N), set_target_price,
request_refresh (with a cooldown).
Optional: is_good_deal, backed by Bedrock.

There are no delete tools. Every tool uses the same service layer as /api.
"""

from fastmcp import FastMCP

from app.db.database import SessionLocal
from app.products import ProductSummary, summarize, tracked_products

mcp = FastMCP(name="Amazon Price Tracker")


@mcp.tool(annotations={"readOnlyHint": True})
def list_trackers() -> list[ProductSummary]:
    """List of every tracked Amazon.es product with its latest price.

    Prices are in EUR. Price and date are None for products not scraped yet.
    Call this first to find the ASINs the other tools take.
    """
    with SessionLocal() as session:
        return [summarize(p) for p in tracked_products(session)]


@mcp.tool
def get_price_history(tracker_id: str, days: int):
    """Get the price history."""
    pass


@mcp.tool
def get_price_summary(tracker_id: str):
    """Get the price summary."""
    pass


@mcp.tool
def get_refresh_status(request_id: str):
    """Get refresh status."""
    pass


@mcp.tool
def add_tracker(url: str):
    """Start tracking a product. Only Amazon.es links are supported for now."""
    pass


@mcp.tool
def set_target_price(tracker_id: str, price: int):
    """Set a product's target price in cents."""
    pass


@mcp.tool
def request_refresh(tracker_id: str):
    """Request a status refresh."""
    pass


@mcp.tool
def is_a_good_deal(tracker_id: str):
    """Identify if a product is currently a good deal."""
    pass
