"""Cognito sign-in and server-side sessions guard /api; the owner token guards /mcp.

The backend runs the OAuth code flow itself and keeps only a random session id in an
HttpOnly cookie, so no token the page's JavaScript could leak ever reaches the browser.
"""

import base64
import datetime
import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Annotated, Any, Literal
from urllib.parse import urlencode

import requests
from fastapi import Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from fastmcp.server.auth import AccessToken, TokenVerifier
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionDep
from app.db.models import SessionRow

# __Host- makes browsers refuse the cookie unless Secure, Path=/ and host-only
SESSION_COOKIE = "__Host-session"
LOGIN_COOKIE = "__Host-login"
LOGIN_MINUTES = 10
TOKEN_TIMEOUT_S = 10

LoginPage = Literal["login", "reset"]
# Cognito's hosted pages that end in a sign-in; all take /oauth2/authorize's parameters
_LOGIN_PATHS: dict[LoginPage, str] = {
    "login": "oauth2/authorize",
    "reset": "forgotPassword",
}


class LoginFailed(Exception):
    pass


@dataclass(frozen=True)
class User:
    sub: str
    email: str


def _hash(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()


def _redirect_uri() -> str:
    return f"{settings.public_url}/api/auth/callback"


def login_redirect(page: LoginPage = "login") -> RedirectResponse:
    """Start the code flow: keep state and PKCE verifier, send the user to Cognito."""
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.cognito_client_id,
            "redirect_uri": _redirect_uri(),
            "scope": "openid email",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    response = RedirectResponse(
        f"https://{settings.cognito_domain}/{_LOGIN_PATHS[page]}?{query}",
        status.HTTP_302_FOUND,
    )
    response.set_cookie(
        LOGIN_COOKIE,
        f"{state}.{verifier}",  # token_urlsafe never emits "."
        max_age=LOGIN_MINUTES * 60,
        secure=True,
        httponly=True,
        samesite="lax",  # Strict would drop it on Cognito's redirect back
    )
    return response


def _id_claims(code: str, verifier: str) -> dict[str, Any]:
    try:
        response = requests.post(
            f"https://{settings.cognito_domain}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.cognito_client_id,
                "code": code,
                "redirect_uri": _redirect_uri(),
                "code_verifier": verifier,
            },
            timeout=TOKEN_TIMEOUT_S,
        )
    except requests.RequestException as e:
        raise LoginFailed(f"Token endpoint unreachable: {e}") from e
    if response.status_code != 200:
        raise LoginFailed(f"Token endpoint answered {response.status_code}")
    # Straight from the token endpoint over TLS, so the signature check can be
    # skipped (OIDC Core 3.1.3.7); the audience still has to be ours
    payload = response.json()["id_token"].split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    claims: dict[str, Any] = json.loads(base64.urlsafe_b64decode(padded))
    if claims.get("aud") != settings.cognito_client_id or not claims.get("sub"):
        raise LoginFailed("ID token is not for this app")
    return claims


def finish_login(
    session: Session, code: str, state: str, login_cookie: str | None
) -> str:
    """Exchange the code for the user's identity and open a session.

    Returns:
        The new session id, for the session cookie.

    Raises:
        LoginFailed: The state doesn't match this browser's login, or Cognito
            refused the code.
    """
    expected, _, verifier = (login_cookie or "").partition(".")
    # Ties the callback to the login this browser started, so an attacker can't
    # sign a victim into the attacker's account
    if not expected or not secrets.compare_digest(state, expected):
        raise LoginFailed("Login state mismatch")
    claims = _id_claims(code, verifier)

    now = datetime.datetime.now(datetime.UTC)
    session.execute(delete(SessionRow).where(SessionRow.expires_at < now))
    session_id = secrets.token_urlsafe(32)
    session.add(
        SessionRow(
            id=_hash(session_id),
            user_sub=claims["sub"],
            email=claims.get("email", ""),
            expires_at=now + datetime.timedelta(days=settings.session_days),
        )
    )
    session.commit()
    return session_id


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=settings.session_days * 86400,
        secure=True,
        httponly=True,
        samesite="strict",  # other sites can't make the browser send it: no CSRF
    )
    response.delete_cookie(LOGIN_COOKIE, secure=True, httponly=True, samesite="lax")


def end_session(session: Session, session_id: str | None, response: Response) -> str:
    """Delete the session and its cookie; return Cognito's logout URL.

    Cognito keeps its own login cookie, so the browser must visit the URL too, or
    the next sign-in goes through without a password.
    """
    if session_id:
        session.execute(delete(SessionRow).where(SessionRow.id == _hash(session_id)))
        session.commit()
    response.delete_cookie(
        SESSION_COOKIE, secure=True, httponly=True, samesite="strict"
    )
    query = urlencode(
        {
            "client_id": settings.cognito_client_id,
            "logout_uri": f"{settings.public_url}/",
        }
    )
    return f"https://{settings.cognito_domain}/logout?{query}"


SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]


def require_user(session: SessionDep, session_id: SessionCookie = None) -> User:
    """FastAPI dependency for /api routes.

    Raises:
        HTTPException: 401 if the session cookie is missing, unknown or expired.
    """
    row = None
    if session_id:
        row = session.scalar(
            select(SessionRow).where(
                SessionRow.id == _hash(session_id),
                SessionRow.expires_at > datetime.datetime.now(datetime.UTC),
            )
        )
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return User(sub=row.user_sub, email=row.email)


UserDep = Annotated[User, Depends(require_user)]


class OwnerTokenVerifier(TokenVerifier):
    """FastMCP auth for /mcp: the owner's token, acting as ``settings.owner_sub``."""

    async def verify_token(self, token: str) -> AccessToken | None:
        expected = settings.api_token.get_secret_value()
        # Constant time, so response timing does not reveal how much of a guess matched
        if not settings.owner_sub or not secrets.compare_digest(
            token.encode(), expected.encode()
        ):
            return None
        return AccessToken(token=token, client_id=settings.owner_sub, scopes=[])
