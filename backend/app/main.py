from fastapi import FastAPI

from app.logs import AccessLog, setup_logging
from app.mcp.mcp import mcp
from app.routers import health, products


def create_app() -> FastAPI:
    """Create Backend FastAPI and MCP apps and add the necessary middleware and routes."""
    mcp_app = mcp.http_app(path="/mcp", stateless_http=True, json_response=True)
    app = FastAPI(title="Price Tracker", lifespan=mcp_app.lifespan)

    app.add_middleware(AccessLog)
    app.include_router(health.router)
    app.include_router(products.router)

    app.mount("/", mcp_app)

    return app


setup_logging()
app = create_app()
