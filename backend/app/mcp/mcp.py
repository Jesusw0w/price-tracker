"""MCP tools for reading price history and managing trackers.

Read: list_trackers, get_price_history, get_price_summary, get_refresh_status.
Write: add_tracker (any https shop, capped), request_refresh (with a cooldown).

There are no delete tools. Every tool uses the same service layer as /api.
"""

# Optional: is_a_good_deal, backed by Bedrock. | set_target_price
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from app.auth import OwnerTokenVerifier
from app.db.database import SessionLocal
from app.links import InvalidLink
from app.products import (
    AlreadyTracked,
    NotTracked,
    PricePoint,
    PriceSummary,
    ProductId,
    ProductSummary,
    RefreshInfo,
    TooManyTrackers,
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
ProductIds = Annotated[list[ProductId], Field(min_length=1, max_length=50)]

mcp = FastMCP(name="Price Tracker", mask_error_details=True, auth=OwnerTokenVerifier())


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def list_trackers() -> list[ProductSummary]:
    """List tracked products and their latest price. Call this first for ids.

    Price is null for products not scraped yet.
    """
    with SessionLocal() as session:
        return [summarize(p) for p in tracked_products(session)]


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_price_history(product_id: ProductId, days: Days) -> list[PricePoint]:
    """Daily prices in the product's currency, oldest first. Unscraped days omitted.

    Args:
        product_id: Id from list_trackers.
        days: Days to look back, plus today.
    """
    with SessionLocal() as session:
        try:
            return price_history(session, product_id, days)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_price_summary(product_id: ProductId, days: Days) -> PriceSummary:
    """Latest, lowest, highest, mean and median price, or nulls if no data.

    Args:
        product_id: Id from list_trackers.
        days: Days to look back, plus today.
    """
    with SessionLocal() as session:
        try:
            return price_summary(session, product_id, days)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_refresh_status(product_ids: ProductIds) -> list[RefreshInfo]:
    """Latest refresh of each product and the date of its newest price.

    Status is null if no refresh was ever requested. If it failed, error says why.

    Args:
        product_ids: Ids from list_trackers.
    """
    with SessionLocal() as session:
        try:
            return refresh_status(session, product_ids)
        except UnknownProduct as e:
            raise ToolError(str(e)) from e


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
def add_tracker(url: str) -> ProductSummary:
    """Track a product from an online shop. It has no price until refreshed.

    Shops without readable price data fail on refresh, and the error says why.

    Args:
        url: https link to the product page, or a bare ASIN for Amazon.es.
    """
    with SessionLocal() as session:
        try:
            return summarize(track(session, url))
        except (InvalidLink, AlreadyTracked, TooManyTrackers) as e:
            raise ToolError(str(e)) from e


# @mcp.tool(annotations={"idempotentHint": True, "openWorldHint": False})
# def set_target_price(product_id: ProductId, price: int) -> None:
#     """Set a product's target price in cents."""
#     pass


@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def request_refresh(product_ids: ProductIds) -> list[RefreshInfo]:
    """Queue price scrapes. Returns at once, so poll get_refresh_status.

    A product with a pending, running or recent request keeps it. If any id is
    unknown or untracked, nothing is queued. The scraper runs on a home machine
    and may be offline, so pending can last hours.

    Args:
        product_ids: Ids from list_trackers.
    """
    with SessionLocal() as session:
        try:
            return queue_refresh(session, product_ids)
        except (UnknownProduct, NotTracked) as e:
            raise ToolError(str(e)) from e


# @mcp.tool(annotations={"readOnlyHint": True})
# def is_a_good_deal(product_id: ProductId) -> None:
#     """Identify if a product is currently a good deal."""
#     pass
