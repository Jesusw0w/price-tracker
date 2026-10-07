"""Checks on product links before they are stored or fetched.

Links come from users and agents, and the scraper fetches them from inside a home
network, so nothing that could reach a private address gets through.
"""

import ipaddress
import re
import socket
from typing import Final
from urllib.parse import SplitResult, urlsplit, urlunsplit

MAX_URL_LENGTH: Final[int] = 2048

_BARE_ASIN: Final[re.Pattern[str]] = re.compile(r"[A-Z0-9]{10}", re.IGNORECASE)
_AMAZON_ASIN: Final[re.Pattern[str]] = re.compile(
    r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?#]|$)", re.IGNORECASE
)
_LOCAL_SUFFIXES: Final[tuple[str, ...]] = (
    ".local",
    ".localhost",
    ".internal",
    ".lan",
    ".home.arpa",
)


class InvalidLink(ValueError):
    pass


def _split(link: str) -> SplitResult:
    if len(link) > MAX_URL_LENGTH:
        raise InvalidLink("Link is too long")
    parts = urlsplit(link)
    try:
        port = parts.port
    except ValueError as e:
        raise InvalidLink("Link has an invalid port") from e
    host = parts.hostname or ""
    if parts.scheme != "https" or not host:
        raise InvalidLink("Paste an https:// product link")
    if parts.username or parts.password or port not in (None, 443):
        raise InvalidLink("Link must not carry credentials or a custom port")
    if "." not in host or host.endswith(_LOCAL_SUFFIXES) or _is_ip(host):
        raise InvalidLink("Link must point to a public website")
    return parts


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def site(url: str) -> str:
    """The host without ``www.``, e.g. ``amazon.es``."""
    return (urlsplit(url).hostname or "").removeprefix("www.")


def canonical_url(link: str) -> str:
    """Return the form a product is stored under.

    Amazon links shrink to ``/dp/<ASIN>`` and a bare ASIN means Amazon.es. Other
    links only lose their fragment: a query string can select a variant.

    Raises:
        InvalidLink: Not an https link to a public host name.
    """
    link = link.strip()
    if _BARE_ASIN.fullmatch(link):
        return f"https://www.amazon.es/dp/{link.upper()}"
    parts = _split(link)
    host = parts.hostname or ""
    if site(link).startswith("amazon.") and (asin := _AMAZON_ASIN.search(parts.path)):
        return f"https://{host}/dp/{asin.group(1).upper()}"
    return urlunsplit(("https", host, parts.path or "/", parts.query, ""))


def ensure_public(url: str) -> None:
    """Refuse a URL unless every address its host resolves to is public.

    Raises:
        InvalidLink: The URL breaks the link rules or resolves somewhere private.
    """
    host = _split(url).hostname or ""
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise InvalidLink(f"Cannot resolve {host}") from e
    # ponytail: checked before requests resolves again, so DNS rebinding in between
    # still gets through; pin the IP in the connection if links ever come from others
    for *_, sockaddr in addresses:
        if not ipaddress.ip_address(sockaddr[0]).is_global:
            raise InvalidLink(f"{host} resolves to a non-public address")
