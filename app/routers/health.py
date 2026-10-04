import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import SessionDep

router = APIRouter(prefix="/health", tags=["health"])

log = logging.getLogger(__name__)


@router.get("")
def liveness() -> dict[str, str]:
    """Process is up. Never touches the database, so an outage cannot stall startup."""
    return {"status": "ok"}


@router.get("/ready")
def readiness(session: SessionDep) -> dict[str, str]:
    """Database is reachable.

    \f
    :raises HTTPException: 503 if the database cannot be reached.
    """
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        log.warning("Database unreachable: %s", e)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Database unreachable"
        ) from e
    return {"status": "ok"}
