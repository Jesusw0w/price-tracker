from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.db.database import SessionDep
from app.db.models import ProductRow
from app.products import (
    AlreadyTracked,
    Asin,
    InvalidLink,
    Product,
    track,
    tracked_products,
)

router = APIRouter(prefix="/api/products", tags=["products"])


class NewProduct(BaseModel):
    link: str  # Amazon product URL or bare ASIN


@router.get("")
def list_products(session: SessionDep) -> list[Product]:
    """List tracked products with their price history."""
    return tracked_products(session)


@router.post("", status_code=status.HTTP_201_CREATED)
def track_product(body: NewProduct, session: SessionDep) -> Product:
    """Start tracking a product. If it was tracked before, its price history is kept.

    \f
    Raises:
        HTTPException: 422 if the link has no ASIN, 409 if already tracked.
    """
    try:
        return track(session, body.link)
    except InvalidLink as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    except AlreadyTracked as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e


@router.delete("/{asin}", status_code=status.HTTP_204_NO_CONTENT)
def untrack_product(asin: Asin, session: SessionDep) -> Response:
    """Stop tracking a product. Its price history is kept.

    \f
    Raises:
        HTTPException: 404 if not tracked.
    """
    row = session.get(ProductRow, asin)
    if row is None or not row.tracked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not tracked")
    row.tracked = False
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
