import datetime
import uuid
from typing import List

from db.session import db
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

# Many-to-many relationship between users and roles
user_roles = Table(
    "user_roles",
    db.Model.metadata,
    Column("user_id", String(36), ForeignKey("users.id")),
    Column("role_id", String(36), ForeignKey("roles.id")),
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_unicode_ci",
)


class Role(db.Model):
    """Role model for role-based access control."""

    __tablename__ = "roles"
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))

    def __repr__(self):
        return f"<Role {self.name}>"


class RefreshToken(db.Model):
    """Model for storing refresh tokens."""

    __tablename__ = "refresh_tokens"
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id = Column(String(36), primary_key=True)  # JWT ID (jti)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken {self.id} for user {self.user_id}>"


class User(db.Model):
    """User model for authentication and authorization."""

    __tablename__ = "users"
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime)

    # MFA fields
    mfa_secret = Column(String(255), nullable=True)
    mfa_enabled = Column(Boolean, default=False)

    # Relationships
    roles = relationship("Role", secondary=user_roles, backref="users")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    # JSON field for storing additional user metadata
    # Using SQLAlchemy-JSON for cross-database compatibility
    # Renamed from meta_data to avoid conflict with SQLAlchemy's metadata
    metadata_json = Column(MutableDict.as_mutable(JSON), default=dict)

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def role_names(self) -> List[str]:
        """Get list of role names for the user."""
        return [role.name for role in self.roles]

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return role_name in self.role_names or "admin" in self.role_names
