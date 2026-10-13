import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import case, select

from app.auth import OwnerDep
from app.config import settings
from app.db.database import SessionDep
from app.db.models import MemberRow, MemberStatus

router = APIRouter(prefix="/api/members", tags=["members"])


class Member(BaseModel):
    sub: str
    email: str
    status: MemberStatus
    requested_at: datetime.datetime


class Decision(BaseModel):
    status: Literal["approved", "rejected"]


class Invite(BaseModel):
    email: EmailStr


class AccountExists(Exception):
    pass


def create_cognito_user(email: str) -> str:
    """Create the account; Cognito emails a temporary password. Returns its sub.

    Raises:
        AccountExists: The email already has an account.
    """
    # Lambda's runtime ships boto3; locally the call needs AWS credentials anyway
    import boto3  # type: ignore[import-not-found]

    cognito = boto3.client("cognito-idp")
    try:
        created: dict[str, Any] = cognito.admin_create_user(
            UserPoolId=settings.cognito_user_pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            DesiredDeliveryMediums=["EMAIL"],
        )
    except cognito.exceptions.UsernameExistsException as e:
        raise AccountExists from e
    attributes = created["User"]["Attributes"]
    return str(next(a["Value"] for a in attributes if a["Name"] == "sub"))


@router.get("")
def list_members(owner: OwnerDep, session: SessionDep) -> list[Member]:
    """Everyone who has signed in, requests waiting for you first."""
    waiting_first = case((MemberRow.status == "pending", 0), else_=1)
    rows = session.scalars(
        select(MemberRow)
        .where(MemberRow.sub != owner.sub)
        .order_by(waiting_first, MemberRow.requested_at.desc())
    )
    return [Member.model_validate(row, from_attributes=True) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def invite(body: Invite, owner: OwnerDep, session: SessionDep) -> Member:
    """Create an account for someone, already approved.

    Cognito emails them a temporary password; their first sign-in sets their own.

    \f
    Raises:
        HTTPException: 409 if the email already has an account (approve it in the
            list instead), 503 when the API has no user pool to create it in.
    """
    if not settings.cognito_user_pool_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Creating accounts needs the deployed API",
        )
    email = str(body.email)
    try:
        sub = create_cognito_user(email)
    except AccountExists as e:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This email already has an account"
        ) from e
    row = MemberRow(
        sub=sub,
        email=email,
        status="approved",
        requested_at=datetime.datetime.now(datetime.UTC),
    )
    session.add(row)
    session.commit()
    return Member.model_validate(row, from_attributes=True)


@router.patch("/{sub}")
def decide(sub: str, body: Decision, owner: OwnerDep, session: SessionDep) -> Member:
    """Approve someone, or decline or revoke their access.

    \f
    Raises:
        HTTPException: 404 for an unknown user, or for yourself, so the owner
            can't lock themselves out.
    """
    row = session.get(MemberRow, sub)
    if row is None or sub == owner.sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such member")
    row.status = body.status
    session.commit()
    return Member.model_validate(row, from_attributes=True)
