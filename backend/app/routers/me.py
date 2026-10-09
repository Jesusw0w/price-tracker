from typing import Annotated

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.auth import UserDep
from app.db.database import SessionDep
from app.db.models import UserSettingsRow
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


class Me(BaseModel):
    email: str
    settings: UserSettings


@router.get("")
def me(user: UserDep, session: SessionDep) -> Me:
    """The signed-in user and their dashboard settings."""
    row = session.get(UserSettingsRow, user.sub)
    saved = UserSettings.model_validate(row.data) if row else UserSettings()
    return Me(email=user.email, settings=saved)


@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
def save_settings(body: UserSettings, user: UserDep, session: SessionDep) -> Response:
    """Replace the user's dashboard settings."""
    data = body.model_dump(mode="json", by_alias=True)
    session.merge(UserSettingsRow(user_sub=user.sub, data=data))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
