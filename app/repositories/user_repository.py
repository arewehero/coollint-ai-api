from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Repository for User entity persistence."""

    def create_anonymous_user(self, db: Session) -> User:
        """Create a new anonymous user with a UUID v4 id.

        Returns the created User instance.
        """
        user = User(
            id=uuid.uuid4(),
            user_type="anonymous",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_user_by_id(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Retrieve a user by id, excluding soft-deleted users.

        Returns None if user does not exist or is soft-deleted.
        """
        return (
            db.query(User)
            .filter(User.id == user_id, User.deleted_at.is_(None))
            .first()
        )
