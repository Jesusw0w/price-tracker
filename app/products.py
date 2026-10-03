import datetime
import json
import re

import pandas as pd
from pydantic import BaseModel

from app.config import historical_data_path, tracked_path

ASIN_RE = re.compile(r"(?:/dp/|/gp/product/|^)([A-Z0-9]{10})(?:[/?#]|$)", re.IGNORECASE)


class PricePoint(BaseModel):
    date: datetime.date
    price: float  # euros


class Product(BaseModel):
    asin: str
    url: str
    name: str | None  # None until first scraped
    history: list[PricePoint]  # oldest first


def parse_asin(link: str) -> str | None:
    """Return the upper-cased ASIN from a product URL or bare ASIN, else ``None``."""
    match = ASIN_RE.search(link.strip())
    return match.group(1).upper() if match else None


def product_url(asin: str) -> str:
    return f"https://www.amazon.es/dp/{asin}"


def load_tracked() -> list[str]:
    if not tracked_path.exists():
        return []
    asins: list[str] = json.loads(tracked_path.read_text(encoding="utf-8"))
    return asins


def save_tracked(asins: list[str]) -> None:
    # single-writer JSON file, move to a real store with the Lambda migration
    tracked_path.parent.mkdir(parents=True, exist_ok=True)
    tracked_path.write_text(json.dumps(asins, indent=2) + "\n", encoding="utf-8")


def read_raw_history() -> pd.DataFrame:
    """The CSV as stored, or an empty frame before the first scrape."""
    if not historical_data_path.exists():
        return pd.DataFrame(columns=["GPU", "URL", "Price", "Date"])
    return pd.read_csv(historical_data_path, sep="|")


def load_history() -> pd.DataFrame:
    """Cleaned price history: one row per product per day, sorted by date."""
    df = read_raw_history()
    return (
        pd.DataFrame(
            {
                "asin": df["URL"].str.extract(r"/dp/([A-Z0-9]{10})")[0],
                "name": df["GPU"].str.strip(),
                "date": pd.to_datetime(df["Date"], format="mixed").dt.date,
                "price": pd.to_numeric(df["Price"], errors="coerce"),
            }
        )
        .dropna()
        .drop_duplicates(["asin", "date"], keep="last")
        .sort_values("date")
    )


def load_products(asins: list[str]) -> list[Product]:
    """Products for ``asins`` in order; unscraped ASINs get an empty history."""
    history = load_history()
    products = []
    for asin in asins:
        rows = history[history["asin"] == asin]
        products.append(
            Product(
                asin=asin,
                url=product_url(asin),
                name=rows["name"].iloc[-1] if len(rows) else None,
                history=[
                    PricePoint(date=d, price=p)
                    for d, p in zip(rows["date"], rows["price"], strict=True)
                ],
            )
        )
    return products
