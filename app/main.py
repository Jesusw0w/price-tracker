from fastapi import FastAPI

from app.logs import AccessLog, setup_logging
from app.routers import products


def create_app() -> FastAPI:
    app = FastAPI(title="Price Tracker")
    app.add_middleware(AccessLog)
    app.include_router(products.router)
    return app


# Process-wide, not per app: setup_logging adds a handler on every call
setup_logging()
app = create_app()
