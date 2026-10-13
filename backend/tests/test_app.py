import base64
import datetime
import json
import logging
from typing import Final
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import auth, products
from app.config import settings
from app.db.database import get_session
from app.db.models import MemberRow, MemberStatus, PriceRow, ProductRow, SessionRow
from app.main import create_app
from app.routers import members

TRACKED: Final[int] = 1
DAY: Final[datetime.date] = datetime.date(2023, 2, 11)
USER: Final[str] = "alice-sub"
SESSION_ID: Final[str] = "alice-session"
# Session cookies are Secure, and the client only sends those over https
BASE_URL: Final[str] = "https://testserver"
OWNER: Final[dict[str, str]] = {
    "Authorization": f"Bearer {settings.api_token.get_secret_value()}"
}
MCP_ACCEPT: Final[dict[str, str]] = {"Accept": "application/json, text/event-stream"}
TOOLS_LIST: Final[dict[str, object]] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
}


def sign_in(
    session: Session,
    sub: str,
    session_id: str,
    days: int = 1,
    status: MemberStatus = "approved",
) -> None:
    now = datetime.datetime.now(datetime.UTC)
    session.merge(
        MemberRow(sub=sub, email=f"{sub}@example.com", status=status, requested_at=now)
    )
    session.add(
        SessionRow(
            id=auth._hash(session_id),
            user_sub=sub,
            email=f"{sub}@example.com",
            expires_at=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(days=days),
        )
    )
    session.commit()


@pytest.fixture
def anonymous(session: Session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app, base_url=BASE_URL)


@pytest.fixture
def client(session: Session, anonymous: TestClient) -> TestClient:
    session.add(
        ProductRow(
            id=TRACKED,
            owner_id=USER,
            url="https://www.amazon.es/dp/B0BMG3FBND",
            domain="amazon.es",
            name="RX 7900 XT",
            currency="EUR",
            added_at=DAY,
        )
    )
    session.add_all(
        [
            PriceRow(product_id=TRACKED, date=DAY, price_cents=115000),
            PriceRow(
                product_id=TRACKED,
                date=DAY - datetime.timedelta(1),
                price_cents=110000,
            ),
        ]
    )
    sign_in(session, USER, SESSION_ID)
    anonymous.cookies.set(auth.SESSION_COOKIE, SESSION_ID)
    return anonymous


def test_products_carry_history_oldest_first(client: TestClient) -> None:
    [product] = client.get("/api/products").json()
    assert product["url"] == "https://www.amazon.es/dp/B0BMG3FBND"
    assert (product["name"], product["currency"]) == ("RX 7900 XT", "EUR")
    assert (product["public"], product["mine"]) == (False, True)
    assert product["history"] == [
        {"date": "2023-02-10", "price": 1100.0},
        {"date": "2023-02-11", "price": 1150.0},
    ]


def test_track_and_untrack(client: TestClient) -> None:
    link = "https://shop.example/p/gpu?variant=7#reviews"
    created = client.post("/api/products", json={"link": link})
    assert created.status_code == 201
    new = created.json()
    assert new == {
        "id": new["id"],
        "url": "https://shop.example/p/gpu?variant=7",
        "name": None,
        "currency": None,
        "public": False,
        "mine": True,
        "unavailable_since": None,
        "history": [],
    }
    assert client.post("/api/products", json={"link": link}).status_code == 409
    assert client.post("/api/products", json={"link": "nope"}).status_code == 422
    refused = client.post("/api/products", json={"link": "https://192.168.1.1/"})
    assert refused.status_code == 422

    assert client.delete(f"/api/products/{new['id']}").status_code == 204
    assert client.delete(f"/api/products/{new['id']}").status_code == 404
    assert [p["id"] for p in client.get("/api/products").json()] == [TRACKED]


def test_archived_products_keep_history_and_restore_by_url(client: TestClient) -> None:
    assert client.get("/api/products/archived").json() == []
    assert client.delete(f"/api/products/{TRACKED}").status_code == 204
    assert client.get("/api/products").json() == []
    [archived] = client.get("/api/products/archived").json()
    assert (archived["id"], len(archived["history"])) == (TRACKED, 2)

    restored = client.post("/api/products", json={"link": archived["url"]})
    assert restored.status_code == 201
    assert len(restored.json()["history"]) == 2
    assert client.get("/api/products/archived").json() == []


def test_permanent_delete_removes_product_and_history(client: TestClient) -> None:
    product = client.get("/api/products").json()[0]
    assert client.delete(f"/api/products/{TRACKED}").status_code == 204
    assert client.delete(f"/api/products/{TRACKED}?permanent=true").status_code == 204
    assert client.get("/api/products/archived").json() == []
    assert client.delete(f"/api/products/{TRACKED}?permanent=true").status_code == 404

    readded = client.post("/api/products", json={"link": product["url"]})
    assert readded.status_code == 201
    assert readded.json()["history"] == []


def test_others_see_a_product_only_while_public_and_cannot_change_it(
    client: TestClient, session: Session
) -> None:
    sign_in(session, "bob-sub", "bob-session")
    bob = TestClient(client.app, base_url=BASE_URL)
    bob.cookies.set(auth.SESSION_COOKIE, "bob-session")
    assert bob.get("/api/products").json() == []

    shared = client.patch(f"/api/products/{TRACKED}", json={"public": True})
    assert shared.json()["public"] is True
    [seen] = bob.get("/api/products").json()
    assert (seen["id"], seen["mine"]) == (TRACKED, False)

    hide = bob.patch(f"/api/products/{TRACKED}", json={"public": False})
    assert hide.status_code == 404
    assert bob.delete(f"/api/products/{TRACKED}").status_code == 404
    assert bob.delete(f"/api/products/{TRACKED}?permanent=true").status_code == 404
    assert client.get("/api/products").json()[0]["public"] is True


def test_settings_are_saved_per_user_and_validated(client: TestClient) -> None:
    me = client.get("/api/me").json()
    assert me == {
        "email": f"{USER}@example.com",
        "status": "approved",
        "owner": False,
        "settings": {
            "groups": [],
            "dashboard": None,
            "background": None,
            "opacity": None,
        },
    }
    saved = {
        "groups": [{"id": "g1", "name": "GPUs", "productIds": [1], "collapsed": True}],
        "dashboard": [[1, 0]],
        "background": "anime.webp",
        "opacity": 45,
    }
    assert client.put("/api/me/settings", json=saved).status_code == 204
    assert client.get("/api/me").json()["settings"] == saved

    too_long = {"groups": [{"id": "g1", "name": "x" * 41, "productIds": []}]}
    assert client.put("/api/me/settings", json=too_long).status_code == 422
    assert client.put("/api/me/settings", json={"opacity": 5}).status_code == 422


@pytest.mark.parametrize("cookie", [None, "unknown-session"])
def test_api_refuses_calls_without_a_session(
    anonymous: TestClient, cookie: str | None
) -> None:
    if cookie:
        anonymous.cookies.set(auth.SESSION_COOKIE, cookie)
    assert anonymous.get("/api/products").status_code == 401
    assert anonymous.get("/api/me").status_code == 401
    assert anonymous.put("/api/me/settings", json={}).status_code == 401


def test_expired_session_is_refused(anonymous: TestClient, session: Session) -> None:
    sign_in(session, USER, "old", days=-1)
    anonymous.cookies.set(auth.SESSION_COOKIE, "old")
    assert anonymous.get("/api/me").status_code == 401


def test_a_new_account_waits_for_the_owners_approval(
    anonymous: TestClient, session: Session
) -> None:
    sign_in(session, "dan-sub", "dan-session", status="pending")
    anonymous.cookies.set(auth.SESSION_COOKIE, "dan-session")
    assert anonymous.get("/api/me").json()["status"] == "pending"
    assert anonymous.get("/api/products").status_code == 403
    assert anonymous.put("/api/me/settings", json={}).status_code == 403
    assert anonymous.get("/api/members").status_code == 403

    sign_in(session, settings.owner_sub, "owner-session")
    owner = TestClient(anonymous.app, base_url=BASE_URL)
    owner.cookies.set(auth.SESSION_COOKIE, "owner-session")
    assert owner.get("/api/me").json()["owner"] is True
    [request] = owner.get("/api/members").json()
    assert (request["email"], request["status"]) == ("dan-sub@example.com", "pending")

    approve = owner.patch("/api/members/dan-sub", json={"status": "approved"})
    assert approve.json()["status"] == "approved"
    assert anonymous.get("/api/products").status_code == 200

    owner.patch("/api/members/dan-sub", json={"status": "rejected"})
    assert anonymous.get("/api/products").status_code == 403
    mine = f"/api/members/{settings.owner_sub}"
    assert owner.patch(mine, json={"status": "rejected"}).status_code == 404


def test_the_owner_creates_an_account_that_is_already_approved(
    anonymous: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sign_in(session, settings.owner_sub, "owner-session")
    anonymous.cookies.set(auth.SESSION_COOKIE, "owner-session")
    taken = {"eve@example.com"}

    def create(email: str) -> str:
        if email in taken:
            raise members.AccountExists
        return f"{email}-sub"

    monkeypatch.setattr(members, "create_cognito_user", create)
    monkeypatch.setattr(settings, "cognito_user_pool_id", "")
    invite = {"email": "fay@example.com"}
    assert anonymous.post("/api/members", json=invite).status_code == 503

    monkeypatch.setattr(settings, "cognito_user_pool_id", "eu-west-1_pool")
    created = anonymous.post("/api/members", json=invite)
    assert created.status_code == 201
    assert (created.json()["sub"], created.json()["status"]) == (
        "fay@example.com-sub",
        "approved",
    )
    assert session.get_one(MemberRow, "fay@example.com-sub").status == "approved"
    taken_email = {"email": "eve@example.com"}
    assert anonymous.post("/api/members", json=taken_email).status_code == 409
    not_email = {"email": "nope"}
    assert anonymous.post("/api/members", json=not_email).status_code == 422


def test_the_owner_is_approved_on_first_sign_in(
    anonymous: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    claims = {"sub": settings.owner_sub, "email": "me@example.com"}
    fake_token_endpoint(monkeypatch, {**claims, "aud": settings.cognito_client_id})
    state = start_login(anonymous)
    anonymous.get("/api/auth/callback", params={"code": "c", "state": state})
    assert anonymous.get("/api/products").status_code == 200


def test_owner_token_does_not_open_the_api(anonymous: TestClient) -> None:
    assert anonymous.get("/api/products", headers=OWNER).status_code == 401


def fake_token_endpoint(
    monkeypatch: pytest.MonkeyPatch, claims: dict[str, str], status: int = 200
) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")

    class Reply:
        status_code = status

        def json(self) -> dict[str, str]:
            return {"id_token": f"header.{payload.decode()}.signature"}

    def post(url: str, data: dict[str, str], timeout: int) -> Reply:
        calls.append({"url": url, **data})
        return Reply()

    monkeypatch.setattr("app.auth.requests.post", post)
    return calls


def start_login(client: TestClient) -> str:
    response = client.get("/api/auth/login", follow_redirects=False)
    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == (
        f"https://{settings.cognito_domain}/oauth2/authorize"
    )
    query = parse_qs(location.query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == [f"{settings.public_url}/api/auth/callback"]
    return query["state"][0]


def test_login_opens_a_session_and_logout_ends_it(
    anonymous: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    claims = {"sub": "carol-sub", "email": "carol@example.com"}
    calls = fake_token_endpoint(
        monkeypatch, {**claims, "aud": settings.cognito_client_id}
    )
    state = start_login(anonymous)

    back = anonymous.get(
        "/api/auth/callback",
        params={"code": "the-code", "state": state},
        follow_redirects=False,
    )
    assert (back.status_code, back.headers["location"]) == (302, "/")
    [call] = calls
    assert (call["code"], len(call["code_verifier"])) == ("the-code", 86)
    me = anonymous.get("/api/me").json()
    assert (me["email"], me["status"]) == ("carol@example.com", "pending")

    out = anonymous.post("/api/auth/logout")
    assert out.json()["logout_url"].startswith(f"https://{settings.cognito_domain}/")
    assert anonymous.get("/api/me").status_code == 401


@pytest.mark.parametrize(
    ("page", "path"), [("reset", "/forgotPassword"), ("signup", "/signup")]
)
def test_reset_and_signup_start_a_login_on_cognitos_own_pages(
    anonymous: TestClient, page: str, path: str
) -> None:
    response = anonymous.get(
        "/api/auth/login", params={"page": page}, follow_redirects=False
    )
    location = urlsplit(response.headers["location"])
    assert (response.status_code, location.path) == (302, path)
    assert parse_qs(location.query)["code_challenge_method"] == ["S256"]
    assert response.headers["set-cookie"].startswith(f"{auth.LOGIN_COOKIE}=")
    assert anonymous.get("/api/auth/login", params={"page": "x"}).status_code == 422


@pytest.mark.parametrize(
    ("aud", "status", "wrong_state"),
    [
        (settings.cognito_client_id, 200, True),  # callback from another browser
        ("another-app", 200, False),
        (settings.cognito_client_id, 400, False),  # Cognito refused the code
    ],
)
def test_callback_refuses_logins_it_cannot_trust(
    anonymous: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    aud: str,
    status: int,
    wrong_state: bool,
) -> None:
    fake_token_endpoint(monkeypatch, {"sub": "eve", "aud": aud}, status)
    state = start_login(anonymous)
    params = {"code": "c", "state": "forged" if wrong_state else state}
    back = anonymous.get("/api/auth/callback", params=params, follow_redirects=False)
    assert back.status_code == 400
    assert anonymous.get("/api/me").status_code == 401


def test_mcp_answers_stateless_json_at_mcp() -> None:
    # The with-block runs the lifespan; without it the MCP session manager never starts
    with TestClient(create_app()) as client:
        response = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_ACCEPT, **OWNER})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    tools = response.json()["result"]["tools"]
    assert "list_trackers" in {t["name"] for t in tools}


@pytest.mark.parametrize(
    "auth_header", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic x"}]
)
def test_mcp_refuses_calls_without_the_owner_token(
    auth_header: dict[str, str],
) -> None:
    with TestClient(create_app()) as client:
        headers = {**MCP_ACCEPT, **auth_header}
        mcp = client.post("/mcp", json=TOOLS_LIST, headers=headers)
    assert mcp.status_code == 401


def test_mcp_is_off_without_an_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "owner_sub", "")
    with TestClient(create_app()) as client:
        mcp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_ACCEPT, **OWNER})
    assert mcp.status_code == 401


def test_liveness_needs_no_database() -> None:
    assert TestClient(create_app()).get("/health").json() == {"status": "ok"}


def test_readiness_reports_database_reachability(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert client.get("/health/ready").json() == {"status": "ok"}

    def down(*_: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(session, "execute", down)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unreachable"}


def test_calls_are_logged_with_their_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.access")
    rid = client.get("/api/products").headers["X-Request-ID"]
    [record] = [r for r in caplog.records if r.name == "app.access"]
    assert record.__dict__["request_id"] == rid
    assert record.getMessage().startswith("GET /api/products 200 ")


def test_unhandled_errors_are_logged_and_answered_500(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_: Session, __: str) -> list[products.Product]:
        raise OSError("database gone")

    monkeypatch.setattr("app.routers.products.tracked_products", boom)
    response = client.get("/api/products")
    assert response.status_code == 500
    rid = response.headers["X-Request-ID"]
    [error] = [r for r in caplog.records if r.exc_info]
    assert error.__dict__["request_id"] == rid
