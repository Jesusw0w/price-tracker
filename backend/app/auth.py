"""The owner's bearer token guards /api and /mcp; /health stays open for probes."""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastmcp.server.auth import AccessToken, TokenVerifier

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


def _is_owner(token: str) -> bool:
    expected = settings.api_token.get_secret_value()
    # Constant time, so response timing does not reveal how much of a guess matched
    return secrets.compare_digest(token.encode(), expected.encode())


def require_owner(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """FastAPI dependency for /api routes.

    Raises:
        HTTPException: 401 if the bearer token is missing or wrong.
    """
    if credentials is None or not _is_owner(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


class OwnerTokenVerifier(TokenVerifier):
    """FastMCP auth for /mcp, accepting the same token as /api."""

    async def verify_token(self, token: str) -> AccessToken | None:
        if not _is_owner(token):
            return None
        return AccessToken(token=token, client_id="owner", scopes=[])
