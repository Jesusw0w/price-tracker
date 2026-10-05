"""MCP tools for reading price history and managing trackers.

Read: list_trackers, price_history, price_summary, refresh_status.
Write: add_tracker (Amazon.es only, max N), set_target_price,
request_refresh (with a cooldown).
Optional: is_good_deal, backed by Bedrock.

There are no delete tools. Every tool uses the same service layer as /api.
"""

from fastmcp import FastMCP

# from ..products import
mcp = FastMCP(name="Amazon Price Tracker")


@mcp.tool(description="Get a list of trackers.")
def get_list_trackers():
    """"""
    pass


@mcp.tool(description="Get the price history.")
def get_price_history(tracker_id: str, days: int):
    """"""
    pass


@mcp.tool(description="Get the price summary.")
def get_price_summary(tracker_id: str):
    """"""
    pass


@mcp.tool(description="Get refresh status.")
def get_refresh_status(request_id: str):
    """"""
    pass


@mcp.tool(
    description="Start tracking an Amazon.es product.",
)
def add_tracker(url: str):
    """Only Amazon.es links are supported for now."""
    pass


@mcp.tool(description="Set a new target price in cents.")
def set_target_price(tracker_id: str, price: int):
    """Set a product's target price in cents."""
    pass


@mcp.tool(description="Request a status refresh.")
def request_refresh(tracker_id: str):
    """"""
    pass


@mcp.tool(description="Identify if a product is currently a good deal.")
def is_a_good_deal(tracker_id: str):
    """"""
    pass
