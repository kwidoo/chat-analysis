"""
Unit tests for User model functionality
"""

import datetime
import uuid

import pytest
from models.user import RefreshToken, Role, User
from sqlalchemy.exc import IntegrityError


class TestUserModel:
    """Test cases for User model"""

    def test_user_creation(self, db_session):
        """Test creating a new user"""
        # Create a user
        user = User(email="test@example.com", hashed_password="hashed_password123", active=True)
        db_session.add(user)
        db_session.commit()

        # Retrieve the user
        retrieved_user = db_session.query(User).filter_by(email="test@example.com").first()

        # Verify user was created correctly
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.hashed_password == "hashed_password123"
        assert retrieved_user.active is True
        assert retrieved_user.id is not None

    def test_user_unique_email(self, db_session):
        """Test that user email must be unique"""
        # Create initial user
        user1 = User(email="duplicate@example.com", hashed_password="password1")
        db_session.add(user1)
        db_session.commit()

        # Try to create another user with the same email
        user2 = User(email="duplicate@example.com", hashed_password="password2")
        db_session.add(user2)

        # Should raise an integrity error for duplicate email
        with pytest.raises(IntegrityError):
            db_session.commit()

        # Rollback the failed transaction
        db_session.rollback()

    def test_user_metadata_json(self, db_session):
        """Test user metadata_json field"""
        # Create user with metadata
        user = User(
            email="metadata@example.com",
            hashed_password="password",
            metadata_json={"preferences": {"theme": "dark", "notifications": True}},
        )
        db_session.add(user)
        db_session.commit()

        # Retrieve and verify metadata
        retrieved_user = db_session.query(User).filter_by(email="metadata@example.com").first()
        assert retrieved_user.metadata_json["preferences"]["theme"] == "dark"
        assert retrieved_user.metadata_json["preferences"]["notifications"] is True

        # Update metadata
        retrieved_user.metadata_json["preferences"]["theme"] = "light"
        db_session.commit()

        # Verify update
        updated_user = db_session.query(User).filter_by(email="metadata@example.com").first()
        assert updated_user.metadata_json["preferences"]["theme"] == "light"


class TestRoleAssignment:
    """Test cases for Role assignment and user-role relationships"""

    def test_role_creation(self, db_session):
        """Test creating roles"""
        # Create admin role
        admin_role = Role(name="admin", description="Administrator role")
        db_session.add(admin_role)

        # Create user role
        user_role = Role(name="user", description="Standard user role")
        db_session.add(user_role)
        db_session.commit()

        # Verify roles were created
        roles = db_session.query(Role).all()
        assert len(roles) == 2
        role_names = [role.name for role in roles]
        assert "admin" in role_names
        assert "user" in role_names

    def test_assign_roles_to_user(self, db_session):
        """Test assigning roles to a user"""
        # Create roles
        admin_role = Role(name="admin", description="Administrator role")
        user_role = Role(name="user", description="Standard user role")
        db_session.add_all([admin_role, user_role])
        db_session.commit()

        # Create user
        user = User(email="roletest@example.com", hashed_password="password")

        # Assign roles to user
        user.roles.append(admin_role)
        user.roles.append(user_role)
        db_session.add(user)
        db_session.commit()

        # Verify user has the correct roles
        retrieved_user = db_session.query(User).filter_by(email="roletest@example.com").first()
        assert len(retrieved_user.roles) == 2
        role_names = [role.name for role in retrieved_user.roles]
        assert "admin" in role_names
        assert "user" in role_names

    def test_role_names_property(self, db_session):
        """Test the role_names property"""
        # Create roles
        admin_role = Role(name="admin", description="Administrator role")
        user_role = Role(name="user", description="Standard user role")
        db_session.add_all([admin_role, user_role])
        db_session.commit()

        # Create user with roles
        user = User(email="propertiestest@example.com", hashed_password="password")
        user.roles.append(admin_role)
        db_session.add(user)
        db_session.commit()

        # Test role_names property
        retrieved_user = (
            db_session.query(User).filter_by(email="propertiestest@example.com").first()
        )
        assert "admin" in retrieved_user.role_names
        assert "user" not in retrieved_user.role_names

    def test_has_role_method(self, db_session):
        """Test has_role method"""
        # Create roles
        admin_role = Role(name="admin", description="Administrator role")
        user_role = Role(name="user", description="Standard user role")
        db_session.add_all([admin_role, user_role])
        db_session.commit()

        # Create user with roles
        user = User(email="hasrole@example.com", hashed_password="password")
        user.roles.append(user_role)  # Only add user role, not admin
        db_session.add(user)
        db_session.commit()

        # Test has_role method
        retrieved_user = db_session.query(User).filter_by(email="hasrole@example.com").first()
        assert retrieved_user.has_role("user") is True
        assert (
            retrieved_user.has_role("admin") is False
        )  # Should be false as user doesn't have admin role


class TestRefreshToken:
    """Test cases for RefreshToken functionality"""

    def test_refresh_token_creation(self, db_session):
        """Test creating a refresh token for a user"""
        # Create user
        user = User(email="tokentest@example.com", hashed_password="password")
        db_session.add(user)
        db_session.commit()

        # Create refresh token
        token_id = str(uuid.uuid4())
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        refresh_token = RefreshToken(id=token_id, user_id=user.id, expires_at=expires_at)
        db_session.add(refresh_token)
        db_session.commit()

        # Verify token was created
        retrieved_token = db_session.query(RefreshToken).filter_by(id=token_id).first()
        assert retrieved_token is not None
        assert retrieved_token.user_id == user.id
        assert retrieved_token.revoked is False

    def test_token_relationship(self, db_session):
        """Test the relationship between users and refresh tokens"""
        # Create user
        user = User(email="relationship@example.com", hashed_password="password")
        db_session.add(user)
        db_session.commit()

        # Create refresh tokens
        token1 = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
        )
        token2 = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=14),
        )
        db_session.add_all([token1, token2])
        db_session.commit()

        # Verify relationships
        retrieved_user = db_session.query(User).filter_by(email="relationship@example.com").first()
        assert len(retrieved_user.refresh_tokens) == 2

        # Test retrieving the user from the token
        retrieved_token = db_session.query(RefreshToken).filter_by(id=token1.id).first()
        assert retrieved_token.user.email == "relationship@example.com"

    def test_revoke_token(self, db_session):
        """Test revoking a refresh token"""
        # Create user
        user = User(email="revoke@example.com", hashed_password="password")
        db_session.add(user)
        db_session.commit()

        # Create refresh token
        token_id = str(uuid.uuid4())
        refresh_token = RefreshToken(
            id=token_id,
            user_id=user.id,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
        )
        db_session.add(refresh_token)
        db_session.commit()

        # Revoke the token
        refresh_token.revoked = True
        db_session.commit()

        # Verify token was revoked
        retrieved_token = db_session.query(RefreshToken).filter_by(id=token_id).first()
        assert retrieved_token.revoked is True

    def test_cascade_delete(self, db_session):
        """Test that deleting a user cascades to its refresh tokens"""
        # Create user
        user = User(email="cascade@example.com", hashed_password="password")
        db_session.add(user)
        db_session.commit()

        # Create refresh token
        token_id = str(uuid.uuid4())
        refresh_token = RefreshToken(
            id=token_id,
            user_id=user.id,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
        )
        db_session.add(refresh_token)
        db_session.commit()

        # Verify token exists
        assert db_session.query(RefreshToken).filter_by(id=token_id).count() == 1

        # Delete the user
        db_session.delete(user)
        db_session.commit()

        # Verify token was deleted with the user
        assert db_session.query(RefreshToken).filter_by(id=token_id).count() == 0
