from typing import Final
from urllib.parse import urljoin

import requests

from app.links import ensure_public

TIMEOUT_S: Final[int] = 30
MAX_REDIRECTS: Final[int] = 3
MAX_PAGE_BYTES: Final[int] = 5_000_000
HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/141.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


class FetchError(Exception):
    pass


def fetch(url: str) -> bytes:
    """Download one page; bytes, so the parser can honour the page's own charset.

    Raises:
        InvalidLink: The URL, or a redirect, points somewhere non-public.
        FetchError: An HTTP error, too many redirects or an oversized page.
        requests.RequestException: The connection failed or timed out.
    """
    for _ in range(MAX_REDIRECTS + 1):
        # Redirects are followed by hand so every hop is checked, not just the first
        ensure_public(url)
        with requests.get(
            url, headers=HEADERS, timeout=TIMEOUT_S, allow_redirects=False, stream=True
        ) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            if response.status_code != 200:
                raise FetchError(f"HTTP {response.status_code}")
            body: bytes = response.raw.read(MAX_PAGE_BYTES + 1, decode_content=True)
            if len(body) > MAX_PAGE_BYTES:
                raise FetchError("Page is too large")
            return body
    raise FetchError(f"More than {MAX_REDIRECTS} redirects")
