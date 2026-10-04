from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status
from pydantic import BaseModel

from app.db.database import SessionDep
from app.db.models import ProductRow
from app.products import Product, parse_asin, to_product, tracked_products

router = APIRouter(prefix="/api/products", tags=["products"])

Asin = Annotated[str, Path(pattern=r"^[A-Z0-9]{10}$")]


class NewProduct(BaseModel):
    link: str  # Amazon product URL or bare ASIN


@router.get("")
def list_products(session: SessionDep) -> list[Product]:
    """List tracked products with their price history."""
    return tracked_products(session)


@router.post("", status_code=status.HTTP_201_CREATED)
def track_product(body: NewProduct, session: SessionDep) -> Product:
    """Start tracking a product, or resume one tracked before with its history.

    \f
    :raises HTTPException: 422 if the link has no ASIN, 409 if already tracked.
    """
    asin = parse_asin(body.link)
    if asin is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Paste an Amazon product link or a 10-character ASIN",
        )
    row = session.get(ProductRow, asin)
    if row is None:
        row = ProductRow(asin=asin)
        session.add(row)
    elif row.tracked:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already tracking this product")
    row.tracked = True
    session.commit()
    return to_product(row)


@router.delete("/{asin}", status_code=status.HTTP_204_NO_CONTENT)
def untrack_product(asin: Asin, session: SessionDep) -> Response:
    """Stop tracking a product. Its price history is kept.

    \f
    :raises HTTPException: 404 if not tracked.
    """
    row = session.get(ProductRow, asin)
    if row is None or not row.tracked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not tracked")
    row.tracked = False
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
