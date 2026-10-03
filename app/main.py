from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.models import init_db
from app.logs import AccessLog, setup_logging
from app.routers import products


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # At startup, not in create_app: importing the app must not touch the database
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Price Tracker", lifespan=lifespan)
    app.add_middleware(AccessLog)
    app.include_router(products.router)
    return app


setup_logging()
app = create_app()
