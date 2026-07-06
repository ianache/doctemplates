"""Local user record create/reuse-on-login business logic (D-07).

Called by 01-06-PLAN's `/auth/callback` route with the `sub` and `email`
claims from the validated OIDC token — kept here as a pure, directly
testable function so the route only has to call it correctly.
"""
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.user import User


def upsert_user(db: SQLAlchemySession, sub: str, email: str) -> User:
    """Create the local user record for `sub` on first login, or reuse
    (and refresh the email on) the existing one on subsequent logins."""
    user = db.query(User).filter_by(sub=sub).first()
    if user is None:
        user = User(sub=sub, email=email)
        db.add(user)
    elif user.email != email:
        user.email = email
    db.commit()
    db.refresh(user)
    return user
