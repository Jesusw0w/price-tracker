"""MCP tools for reading price history and managing trackers.

Read: list_trackers, get_price_history, get_price_summary, get_refresh_status.
Write: add_tracker (Amazon.es only, max N), request_refresh (with a cooldown).

There are no delete tools. Every tool uses the same service layer as /api.
"""

# Optional: is_a_good_deal, backed by Bedrock. | set_target_price
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from app.db.database import SessionLocal
from app.products import (
    AlreadyTracked,
    Asin,
    InvalidLink,
    NotTracked,
    PricePoint,
    PriceSummary,
    ProductSummary,
    RefreshInfo,
    UnknownProduct,
    price_history,
    price_summary,
    queue_refresh,
    refresh_status,
    summarize,
    track,
    tracked_products,
)

Days = Annotated[int, Field(ge=1)]

mcp = FastMCP(name="Amazon Price Tracker")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def list_trackers() -> list[ProductSummary]:
    """List tracked products and their latest EUR price. Call this first for ASINs.

    Price is null for products not scraped yet.
    """
    with SessionLocal() as session:
        return [summarize(p) for p in tracked_products(session)]


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_price_history(asin: Asin, days: Days) -> list[PricePoint]:
    """Daily EUR prices, oldest first. Days without a scrape are omitted.

    Args:
        asin: ASIN from list_trackers.
        days: Days to look back, plus today.
    """
    with SessionLocal() as session:
        try:
            return price_history(session, asin, days)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_price_summary(asin: Asin, days: Days) -> PriceSummary:
    """Latest, lowest, highest, mean and median EUR price, or nulls if no data.

    Args:
        asin: ASIN from list_trackers.
        days: Days to look back, plus today.
    """
    with SessionLocal() as session:
        try:
            return price_summary(session, asin, days)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_refresh_status(asin: Asin) -> RefreshInfo:
    """Latest refresh of a product and the date of its newest price.

    Status is null if no refresh was ever requested. If it failed, error says why.

    Args:
        asin: ASIN from list_trackers.
    """
    with SessionLocal() as session:
        try:
            return refresh_status(session, asin)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
def add_tracker(url: str) -> ProductSummary:
    """Track an Amazon.es product. A new product has no price until refreshed.

    Args:
        url: Amazon product link or bare ASIN.
    """
    with SessionLocal() as session:
        try:
            return summarize(track(session, url))
        except (InvalidLink, AlreadyTracked) as e:
            raise ToolError(str(e)) from e


# @mcp.tool(annotations={"idempotentHint": True, "openWorldHint": False})
# def set_target_price(asin: Asin, price: int) -> None:
#     """Set a product's target price in cents."""
#     pass


@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def request_refresh(asin: Asin) -> RefreshInfo:
    """Queue a price scrape. Returns at once, so poll get_refresh_status.

    If a request is already pending, running or recent, returns that one instead.

    Args:
        asin: ASIN from list_trackers.
    """
    with SessionLocal() as session:
        try:
            return queue_refresh(session, asin)
        except (UnknownProduct, NotTracked) as e:
            raise ToolError(str(e)) from e


# @mcp.tool(annotations={"readOnlyHint": True})
# def is_a_good_deal(asin: Asin) -> None:
#     """Identify if a product is currently a good deal."""
#     pass
