import json
import logging
from typing import Any, NamedTuple

from bs4 import BeautifulSoup

PRICE_DATA_CLASS = "a-section aok-hidden twister-plus-buying-options-price-data"
TITLE_SUFFIX = ": Amazon.es: Informática"

log = logging.getLogger(__name__)


class Scraped(NamedTuple):
    asin: str
    name: str | None
    price_cents: int | None


def parse_page(asin: str, html: BeautifulSoup) -> Scraped:
    """Today's name and price for one page; either is ``None`` if missing."""
    prices = check_prices(html)
    return Scraped(
        asin=asin,
        name=html.title.text.replace(TITLE_SUFFIX, "").strip() if html.title else None,
        price_cents=round(prices[0]["priceAmount"] * 100) if prices else None,
    )


def check_prices(html: BeautifulSoup) -> Any:  # noqa: ANN401  # raw Amazon JSON
    """Amazon's embedded price JSON, or ``None`` if missing or malformed."""
    price_data = html.find("div", {"class": PRICE_DATA_CLASS})
    if price_data is None:
        log.warning("No price data on %s", html.title)
        return None
    try:
        return json.loads(price_data.text.strip())
    except json.JSONDecodeError:
        log.warning("Price data not readable for %s", html.title)
        return None
