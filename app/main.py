from fastapi import FastAPI

from app.logs import AccessLog, setup_logging
from app.routers import products


def create_app() -> FastAPI:
    app = FastAPI(title="Price Tracker")
    app.add_middleware(AccessLog)
    app.include_router(products.router)
    return app


setup_logging()
app = create_app()
