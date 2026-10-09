from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.auth import UserDep
from app.db.database import SessionDep
from app.links import InvalidLink
from app.products import (
    AlreadyTracked,
    NotTracked,
    Product,
    ProductId,
    TooManyTrackers,
    UnknownProduct,
    archive_product,
    archived_products,
    delete_product,
    set_public,
    track,
    tracked_products,
)

router = APIRouter(prefix="/api/products", tags=["products"])


class NewProduct(BaseModel):
    link: str  # https product URL, or a bare ASIN for Amazon.es


class Visibility(BaseModel):
    public: bool


@router.get("")
def list_products(user: UserDep, session: SessionDep) -> list[Product]:
    """List your tracked products and everyone's public ones, with price history."""
    return tracked_products(session, user.sub)


@router.get("/archived")
def list_archived_products(user: UserDep, session: SessionDep) -> list[Product]:
    """List your untracked products with their price history. POST a URL to restore."""
    return archived_products(session, user.sub)


@router.post("", status_code=status.HTTP_201_CREATED)
def track_product(body: NewProduct, user: UserDep, session: SessionDep) -> Product:
    """Start tracking a product, privately. If you tracked it before, history is kept.

    \f
    Raises:
        HTTPException: 422 if the link is refused, 409 if already tracked or
            at the tracker cap.
    """
    try:
        return track(session, user.sub, body.link)
    except InvalidLink as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    except (AlreadyTracked, TooManyTrackers) as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e


@router.patch("/{product_id}")
def change_visibility(
    product_id: ProductId, body: Visibility, user: UserDep, session: SessionDep
) -> Product:
    """Share one of your products with every user, or make it private again.

    \f
    Raises:
        HTTPException: 404 if you own no such product.
    """
    try:
        return set_public(session, user.sub, product_id, body.public)
    except UnknownProduct as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def untrack_product(
    product_id: ProductId, user: UserDep, session: SessionDep, permanent: bool = False
) -> Response:
    """Archive one of your products: stop tracking it and keep its price history.

    With ``permanent``, delete the product and its history instead, tracked or not.

    \f
    Raises:
        HTTPException: 404 if you track no such product, or with ``permanent``,
            own no such product.
    """
    try:
        if permanent:
            delete_product(session, user.sub, product_id)
        else:
            archive_product(session, user.sub, product_id)
    except (UnknownProduct, NotTracked) as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)
