import socket

import pytest

from app.links import InvalidLink, canonical_url, ensure_public, site


@pytest.mark.parametrize(
    ("link", "url"),
    [
        (
            "https://www.amazon.es/XFX-Radeon/dp/B0BNLSDRKB/ref=sr_1_2?k=amd",
            "https://www.amazon.es/dp/B0BNLSDRKB",
        ),
        (
            "https://www.amazon.de/gp/product/b0bnlsdrkb?th=1",
            "https://www.amazon.de/dp/B0BNLSDRKB",
        ),
        (" b0bnlsdrkb ", "https://www.amazon.es/dp/B0BNLSDRKB"),
        # Elsewhere the query can pick a variant, so only the fragment goes
        (
            "https://Shop.Example/p/gpu?variant=7#reviews",
            "https://shop.example/p/gpu?variant=7",
        ),
        ("https://shop.example:443", "https://shop.example/"),
    ],
)
def test_canonical_url(link: str, url: str) -> None:
    assert canonical_url(link) == url


@pytest.mark.parametrize(
    "link",
    [
        "http://shop.example/p/1",
        "ftp://shop.example/p/1",
        "file:///etc/passwd",
        "rtx 4070 ti",
        "https://localhost/admin",
        "https://router/",
        "https://printer.local/",
        "https://127.0.0.1/",
        "https://[::1]/",
        "https://192.168.1.1/",
        "https://user:pass@shop.example/",
        "https://shop.example:8080/",
        "https://shop.example:notaport/",
        "https://shop.example/" + "a" * 2048,
    ],
)
def test_canonical_url_refuses_links_that_could_reach_private_hosts(
    link: str,
) -> None:
    with pytest.raises(InvalidLink):
        canonical_url(link)


def test_site_drops_www() -> None:
    assert site("https://www.amazon.co.uk/dp/B0BNLSDRKB") == "amazon.co.uk"


def _resolves_to(monkeypatch: pytest.MonkeyPatch, *ips: str) -> None:
    def fake_getaddrinfo(*_: object, **__: object) -> list[tuple[object, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ips]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def test_ensure_public_accepts_public_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resolves_to(monkeypatch, "93.184.215.14")
    ensure_public("https://shop.example/p/1")


@pytest.mark.parametrize("ip", ["10.0.0.5", "127.0.0.1", "169.254.169.254", "::1"])
def test_ensure_public_refuses_names_resolving_to_private_addresses(
    monkeypatch: pytest.MonkeyPatch, ip: str
) -> None:
    _resolves_to(monkeypatch, "93.184.215.14", ip)
    with pytest.raises(InvalidLink, match="non-public"):
        ensure_public("https://shop.example/p/1")
