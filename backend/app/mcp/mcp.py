"""MCP with tools to add new trackings, trigger ad-hoc data updates and product tracking management."""
"""Read scope
  list_trackers
  get_price_history(tracker_id, days)
  get_price_summary(tracker_id)
  get_refresh_status(request_id)

Write scope
  add_tracker(url)      Amazon.es only, max N
  set_target_price(tracker_id, price)
  request_refresh(tracker_id)   cooldown

Optional
  is_good_deal(tracker_id)  → Bedrock

No delete tools. Same service layer as /api."""
from fastmcp import FastMCP

mcp = FastMCP(name="Amazon Price Tracker")

@mcp.tool(
    name="list_trackers",
    description="Get a list of trackers."
)
def get_tracker_list():
    """"""
    pass

@mcp.tool(
    name="price_history",
    description="Get the price history."
)
def get_price_history(tracker_id: str, days: int):
    """"""
    pass

@mcp.tool(
    name="price_summary",
    description="Get the price summary."
)
def get_price_summary(tracker_id: str):
    """"""
    pass
    @mcp.tool(
        name="price_summary",
        description="Get the price summary."
    )

@mcp.tool(
    name="refresh_status",
    description="Get refresh status."
)
def get_refresh_status(request_id:str):
    """"""
    pass

@mcp.tool(
    name="add_tracker",
    description="Add one or multiple new trackings (Amazon ES only)."
)
def add_tracker(url: str):
    """Add a new tracker to the list. Currenly only supports Amazon ES"""
    pass

@mcp.tool(
    name="set_target_price",
    description="Set a new target price."
)
def set_target_price(tracker_id:str,price:int):
    """Set a new target price for one or more products."""
    pass

@mcp.tool(
    name="request_refresh",
    description="Request a status refresh."
)
def request_refresh(tracker_id:str):
    """"""
    pass

@mcp.tool(
    name="is_good_deal",
    description="Identify if a product is currently a good deal."
)
def is_a_good_deal():
    """"""
    pass
