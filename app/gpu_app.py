from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Response, status
from pydantic import BaseModel

from app.products import (
    Product,
    load_products,
    load_tracked,
    parse_asin,
    save_tracked,
)

app = FastAPI(title="GPU Price Tracker")

Asin = Annotated[str, Path(pattern=r"^[A-Z0-9]{10}$")]


class NewProduct(BaseModel):
    link: str  # Amazon product URL or bare ASIN


@app.get("/api/products")
def list_products() -> list[Product]:
    return load_products(load_tracked())


@app.post("/api/products", status_code=status.HTTP_201_CREATED)
def track_product(body: NewProduct) -> Product:
    asin = parse_asin(body.link)
    if asin is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Paste an Amazon product link or a 10-character ASIN",
        )
    tracked = load_tracked()
    if asin in tracked:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already tracking this product")
    save_tracked([*tracked, asin])
    return load_products([asin])[0]


@app.delete("/api/products/{asin}", status_code=status.HTTP_204_NO_CONTENT)
def untrack_product(asin: Asin) -> Response:
    tracked = load_tracked()
    if asin not in tracked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not tracked")
    save_tracked([a for a in tracked if a != asin])
    return Response(status_code=status.HTTP_204_NO_CONTENT)
