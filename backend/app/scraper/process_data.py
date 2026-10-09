import json
import logging
import re
from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Final, NamedTuple

from bs4 import BeautifulSoup

AMAZON_PRICE_CLASS: Final[str] = (
    "a-section aok-hidden twister-plus-buying-options-price-data"
)
AMAZON_CURRENCIES: Final[dict[str, str]] = {
    "amazon.es": "EUR",
    "amazon.de": "EUR",
    "amazon.fr": "EUR",
    "amazon.it": "EUR",
    "amazon.co.uk": "GBP",
    "amazon.com": "USD",
}
# Names come from arbitrary pages and reach agents verbatim, so they stay short
MAX_NAME_LENGTH: Final[int] = 200
MAX_PRICE: Final[Decimal] = Decimal(10_000_000)
# schema.org ItemAvailability names and Open Graph's product:availability values,
# lowercased with spaces dropped
UNAVAILABLE: Final[frozenset[str]] = frozenset(
    {"outofstock", "soldout", "discontinued", "oos"}
)

log = logging.getLogger(__name__)


class Scraped(NamedTuple):
    product_id: int
    name: str | None
    price_cents: int | None
    currency: str | None
    available: bool = True  # False only when the page says so, not for a missing price


def is_blocked(domain: str, html: BeautifulSoup) -> bool:
    """Amazon answers bots with HTTP 200 and a captcha instead of the product."""
    return domain.startswith("amazon.") and bool(
        html.find("form", action=re.compile("validateCaptcha"))
    )


def parse_page(product_id: int, domain: str, html: BeautifulSoup) -> Scraped:
    """Name, price and currency of one page; any of them is ``None`` if missing."""
    if domain.startswith("amazon."):  # ponytail: a dict of parsers at the second site
        name, price, currency, unavailable = _amazon(domain, html)
    else:
        name, price, currency, unavailable = _structured(html)
    cents = _cents(price)
    if cents is None:
        log.warning(
            "%s for product %d",
            "Not available" if unavailable else "No price found",
            product_id,
        )
    return Scraped(
        product_id,
        _clean_name(name),
        cents,
        _currency(currency),
        available=cents is not None or not unavailable,
    )


def _amazon(
    domain: str, html: BeautifulSoup
) -> tuple[str | None, Any, str | None, bool]:
    title = html.title.text if html.title else None
    name = re.split(r"\s*:\s*Amazon\.", title)[0] if title else None
    data = html.find("div", {"class": AMAZON_PRICE_CLASS})
    try:
        offers = json.loads(data.text) if data else None
    except json.JSONDecodeError:
        offers = None
    # Grouped by buy box since 2025: {"desktop_buybox_group_1": [{...}]}
    if isinstance(offers, dict):
        offers = next(iter(offers.values()), None)
    price = (
        offers[0].get("priceAmount")
        if isinstance(offers, list) and offers and isinstance(offers[0], dict)
        else None
    )
    # "No disponible": the listing stays up with no offer
    unavailable = html.find(id="outOfStock") is not None
    return name, price, AMAZON_CURRENCIES.get(domain), unavailable


def _structured(html: BeautifulSoup) -> tuple[str | None, Any, Any, bool]:
    """Read schema.org JSON-LD first, then Open Graph and microdata tags."""
    products = list(_json_ld_products(html))
    for product in products:
        price, currency = _offer(product.get("offers"))
        if price is not None:
            return product.get("name"), price, currency, False
    # The price can sit in tags while the name is still in JSON-LD
    name = next((p["name"] for p in products if p.get("name")), None)
    title = html.title.text if html.title else None
    availability = [_availability(p.get("offers")) for p in products]
    availability.append(_meta(html, "product:availability", "og:availability"))
    return (
        name or _meta(html, "og:title") or title,
        _meta(html, "product:price:amount", "og:price:amount", "price"),
        _meta(html, "product:price:currency", "og:price:currency", "priceCurrency"),
        any(_says_unavailable(a) for a in availability),
    )


def _availability(offers: object) -> object:
    for offer in offers if isinstance(offers, list) else [offers]:
        if isinstance(offer, dict) and "availability" in offer:
            return offer["availability"]
    return None


def _says_unavailable(value: object) -> bool:
    """``https://schema.org/OutOfStock``, ``OutOfStock`` or ``out of stock``."""
    if not isinstance(value, str):
        return False
    return value.rsplit("/", 1)[-1].replace(" ", "").lower() in UNAVAILABLE


def _json_ld_products(html: BeautifulSoup) -> Iterator[dict[str, Any]]:
    for script in html.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue
        yield from (node for node in _nodes(data) if _has_type(node, "Product"))


def _nodes(data: object) -> Iterator[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            yield from _nodes(item)
    elif isinstance(data, dict):
        yield data
        yield from _nodes(data.get("@graph", []))
        yield from _nodes(data.get("hasVariant", []))


def _has_type(node: dict[str, Any], name: str) -> bool:
    kind = node.get("@type")
    return kind == name or (isinstance(kind, list) and name in kind)


def _offer(offers: object) -> tuple[Any, Any]:
    for offer in offers if isinstance(offers, list) else [offers]:
        if not isinstance(offer, dict):
            continue
        spec = offer.get("priceSpecification")
        source = spec if isinstance(spec, dict) and "price" in spec else offer
        price = source.get("price", offer.get("lowPrice"))  # lowPrice: AggregateOffer
        if price is not None:
            return price, source.get("priceCurrency", offer.get("priceCurrency"))
    return None, None


def _meta(html: BeautifulSoup, *keys: str) -> str | None:
    for key in keys:
        tag = html.find("meta", attrs={"property": key}) or html.find(
            True, attrs={"itemprop": key}
        )
        if tag is not None:
            value = tag.get("content") or tag.get_text()
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _cents(value: object) -> int | None:
    """Value x 100; ``None`` for anything not a plain positive decimal like ``"9.99"``.

    "1.234,56" is refused rather than guessed, since its meaning depends on locale.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    if not amount.is_finite() or not 0 < amount < MAX_PRICE:
        return None
    return int((amount * 100).to_integral_value(ROUND_HALF_UP))


def _currency(value: object) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z]{3}", value.strip()):
        return value.strip().upper()
    return None


def _clean_name(name: object) -> str | None:
    if not isinstance(name, str):
        return None
    return " ".join(name.split())[:MAX_NAME_LENGTH] or None
