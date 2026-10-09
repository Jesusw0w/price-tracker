from typing import Annotated

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.auth import MemberDep, UserDep
from app.db.database import SessionDep
from app.db.models import MemberStatus, UserSettingsRow
from app.products import ProductId

router = APIRouter(prefix="/api/me", tags=["me"])

# The bounds keep one user from filling the database through their settings
ColourSlot = Annotated[int, Field(ge=0, lt=32)]


class Group(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=40)
    product_ids: list[ProductId] = Field(alias="productIds", max_length=500)
    collapsed: bool = False


class UserSettings(BaseModel):
    groups: list[Group] = Field(default=[], max_length=50)
    dashboard: list[tuple[ProductId, ColourSlot]] | None = Field(
        default=None, max_length=32
    )
    background: str | None = Field(default=None, max_length=200)
    # Percent opacity of the dashboard's cards; below 20 text on a photo gets unreadable
    opacity: int | None = Field(default=None, ge=20, le=100)


class Me(BaseModel):
    email: str
    status: MemberStatus
    owner: bool
    settings: UserSettings


@router.get("")
def me(user: UserDep, session: SessionDep) -> Me:
    """The signed-in user, whether they are approved yet, and their settings."""
    row = session.get(UserSettingsRow, user.sub)
    saved = UserSettings.model_validate(row.data) if row else UserSettings()
    return Me(email=user.email, status=user.status, owner=user.owner, settings=saved)


@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
def save_settings(body: UserSettings, user: MemberDep, session: SessionDep) -> Response:
    """Replace the user's dashboard settings."""
    data = body.model_dump(mode="json", by_alias=True)
    session.merge(UserSettingsRow(user_sub=user.sub, data=data))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
