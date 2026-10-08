from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.auth import require_owner
from app.db.database import SessionDep
from app.db.models import ProductRow
from app.links import InvalidLink
from app.products import (
    AlreadyTracked,
    Product,
    ProductId,
    TooManyTrackers,
    track,
    tracked_products,
)

router = APIRouter(
    prefix="/api/products", tags=["products"], dependencies=[Depends(require_owner)]
)


class NewProduct(BaseModel):
    link: str  # https product URL, or a bare ASIN for Amazon.es


@router.get("")
def list_products(session: SessionDep) -> list[Product]:
    """List tracked products with their price history."""
    return tracked_products(session)


@router.post("", status_code=status.HTTP_201_CREATED)
def track_product(body: NewProduct, session: SessionDep) -> Product:
    """Start tracking a product. If it was tracked before, its price history is kept.

    \f
    Raises:
        HTTPException: 422 if the link is refused, 409 if already tracked or
            at the tracker cap.
    """
    try:
        return track(session, body.link)
    except InvalidLink as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    except (AlreadyTracked, TooManyTrackers) as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def untrack_product(product_id: ProductId, session: SessionDep) -> Response:
    """Stop tracking a product. Its price history is kept.

    \f
    Raises:
        HTTPException: 404 if not tracked.
    """
    row = session.get(ProductRow, product_id)
    if row is None or not row.tracked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not tracked")
    row.tracked = False
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
