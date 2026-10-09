import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import RedirectResponse

from app.auth import (
    LOGIN_COOKIE,
    LoginFailed,
    LoginPage,
    SessionCookie,
    end_session,
    finish_login,
    login_redirect,
    set_session_cookie,
)
from app.db.database import SessionDep

router = APIRouter(prefix="/api/auth", tags=["auth"])

log = logging.getLogger(__name__)


@router.get("/login")
def login(page: LoginPage = "login") -> RedirectResponse:
    """Redirect to Cognito's sign-in page, or with ``page=reset`` its password reset.

    Both end in a sign-in that comes back to /api/auth/callback.
    """
    return login_redirect(page)


@router.get("/callback")
def callback(
    session: SessionDep,
    code: str = "",
    state: str = "",
    login_cookie: Annotated[str | None, Cookie(alias=LOGIN_COOKIE)] = None,
) -> RedirectResponse:
    """Open a session for the user Cognito signed in, then go to the UI.

    \f
    Raises:
        HTTPException: 400 if the login can't be completed.
    """
    try:
        session_id = finish_login(session, code, state, login_cookie)
    except LoginFailed as e:
        log.warning("Login failed: %s", e)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Login failed, sign in again"
        ) from e
    response = RedirectResponse("/", status.HTTP_302_FOUND)
    set_session_cookie(response, session_id)
    return response


@router.post("/logout")
def logout(
    session: SessionDep, response: Response, session_id: SessionCookie = None
) -> dict[str, str]:
    """End the session. The UI then opens ``logout_url`` to end Cognito's too."""
    return {"logout_url": end_session(session, session_id, response)}
