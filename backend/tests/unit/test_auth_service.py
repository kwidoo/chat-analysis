import time

import pytest
from services.auth_service import AuthService


class TestAuthService:
    """Test cases for AuthService authentication and token functionality."""

    @pytest.fixture
    def auth_service(self):
        """Create an AuthService instance for testing."""
        # Use a test secret key and shorter token expiry times for faster testing
        return AuthService(
            secret_key="test-secret-key",
            token_expiry=5,  # 5 seconds
            refresh_expiry=10,  # 10 seconds
        )

    @pytest.fixture
    def test_user(self, auth_service):
        """Create a test user for authentication tests."""
        return auth_service.create_user(
            username="testuser", password="testpassword", roles=["user", "editor"]
        )

    def test_create_user(self, auth_service):
        """Test user creation functionality."""
        # Create a user
        user = auth_service.create_user("user1", "password123", ["user"])

        # Validate user properties
        assert user.username == "user1"
        assert user.roles == ["user"]
        assert user.active is True
        assert user.id is not None
        # Password should be hashed, not stored in plaintext
        assert user.password_hash != "password123"

        # Trying to create a user with the same username should raise an error
        with pytest.raises(ValueError):
            auth_service.create_user("user1", "anotherpassword")

    def test_authenticate_user(self, auth_service, test_user):
        """Test user authentication functionality."""
        # Successful authentication
        user = auth_service.authenticate("testuser", "testpassword")
        assert user is not None
        assert user.id == test_user.id

        # Failed authentication - wrong password
        user = auth_service.authenticate("testuser", "wrongpassword")
        assert user is None

        # Failed authentication - user doesn't exist
        user = auth_service.authenticate("nonexistentuser", "testpassword")
        assert user is None

    def test_token_generation(self, auth_service, test_user):
        """Test token generation and validation."""
        # Generate tokens
        tokens = auth_service.generate_token_pair(test_user)

        # Verify token structure
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "bearer"

        # Validate access token
        access_token = tokens["access_token"]
        payload = auth_service.validate_token(access_token)
        assert payload is not None
        assert payload.sub == test_user.id
        assert payload.type == "access"
        assert "user" in payload.roles
        assert "editor" in payload.roles

    def test_token_refresh(self, auth_service, test_user):
        """Test refreshing tokens."""
        # Generate initial tokens
        tokens = auth_service.generate_token_pair(test_user)

        # Refresh tokens
        new_tokens = auth_service.refresh_token(tokens["refresh_token"])
        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        # The original refresh token should be revoked
        revoked_refresh = auth_service.refresh_token(tokens["refresh_token"])
        assert revoked_refresh is None

        # The new refresh token should work
        newest_tokens = auth_service.refresh_token(new_tokens["refresh_token"])
        assert newest_tokens is not None

    def test_token_revocation(self, auth_service, test_user):
        """Test token revocation functionality."""
        # Revoke refresh token
        revoked = auth_service.revoke_token(
            auth_service.generate_token_pair(test_user)["refresh_token"]
        )
        assert revoked is True

        # Attempt to use revoked token
        new_tokens = auth_service.refresh_token(
            auth_service.generate_token_pair(test_user)["refresh_token"]
        )
        assert new_tokens is None

        # Attempt to revoke access token (should fail as only refresh tokens can be revoked)
        revoked = auth_service.revoke_token(
            auth_service.generate_token_pair(test_user)["access_token"]
        )
        assert revoked is False

    def test_token_expiry(self, auth_service, test_user):
        """Test token expiry functionality."""
        # Generate tokens with short expiry
        tokens = auth_service.generate_token_pair(test_user)

        # Token should be valid initially
        payload = auth_service.validate_token(tokens["access_token"])
        assert payload is not None

        # Wait for token to expire
        time.sleep(6)  # 1 second more than token_expiry

        # Token should now be invalid
        expired_payload = auth_service.validate_token(tokens["access_token"])
        assert expired_payload is None

    def test_clean_expired_tokens(self, auth_service, test_user):
        """Test cleaning up expired refresh tokens."""

        # Token should be registered in user's refresh_tokens
        refresh_tokens_count = len(test_user.refresh_tokens)
        assert refresh_tokens_count > 0

        # Wait for token to expire
        time.sleep(11)  # 1 second more than refresh_expiry

        # Clean up expired tokens
        auth_service.clean_expired_tokens()

        # User should have no active refresh tokens
        assert len(test_user.refresh_tokens) == 0
