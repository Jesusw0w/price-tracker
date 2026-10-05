"""MCP tools for reading price history and managing trackers.

Read: list_trackers, price_history, price_summary, refresh_status.
Write: add_tracker (Amazon.es only, max N), set_target_price,
request_refresh (with a cooldown).
Optional: is_good_deal, backed by Bedrock.

There are no delete tools. Every tool uses the same service layer as /api.
"""

from fastmcp import FastMCP

mcp = FastMCP(name="Amazon Price Tracker")


@mcp.tool(name="list_trackers", description="Get a list of trackers.")
def get_tracker_list():
    """"""
    pass


@mcp.tool(name="price_history", description="Get the price history.")
def get_price_history(tracker_id: str, days: int):
    """"""
    pass


@mcp.tool(name="price_summary", description="Get the price summary.")
def get_price_summary(tracker_id: str):
    """"""
    pass


@mcp.tool(name="refresh_status", description="Get refresh status.")
def get_refresh_status(request_id: str):
    """"""
    pass


@mcp.tool(
    name="add_tracker",
    description="Start tracking an Amazon.es product.",
)
def add_tracker(url: str):
    """Only Amazon.es links are supported for now."""
    pass


@mcp.tool(name="set_target_price", description="Set a new target price in cents.")
def set_target_price(tracker_id: str, price: int):
    """Set a product's target price in cents."""
    pass


@mcp.tool(name="request_refresh", description="Request a status refresh.")
def request_refresh(tracker_id: str):
    """"""
    pass


@mcp.tool(
    name="is_good_deal",
    description="Identify if a product is currently a good deal."
)
def is_a_good_deal(tracker_id: str):
    """"""
    pass
