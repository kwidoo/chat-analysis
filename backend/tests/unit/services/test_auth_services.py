"""
Unit tests for auth services demonstrating Liskov Substitution Principle

These tests show how our interfaces can be substituted with mock implementations,
adhering to the Liskov Substitution Principle (L in SOLID).
"""

import datetime
from typing import Any, Dict, List, Optional

import pytest
from interfaces.auth import IMFAService, ITokenService, IUserService
from services.default_auth_service import AuthServiceImpl


class MockTokenService(ITokenService):
    """Mock implementation of ITokenService for testing"""

    def __init__(self):
        self.tokens = {}  # user_id -> {access_token, refresh_token}
        self.token_payloads = {}  # token -> payload
        self.token_expiry = 3600
        self.refresh_expiry = 86400
        self.revoked_tokens = set()

    def generate_access_token(self, user_id: str) -> str:
        token = f"mock-access-token-{user_id}-{datetime.datetime.utcnow().timestamp()}"
        payload = {
            "sub": user_id,
            "type": "access",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=self.token_expiry),
        }
        self.token_payloads[token] = payload
        return token

    def generate_refresh_token(self, user_id: str) -> str:
        token = f"mock-refresh-token-{user_id}-{datetime.datetime.utcnow().timestamp()}"
        payload = {
            "sub": user_id,
            "type": "refresh",
            "jti": f"mock-id-{datetime.datetime.utcnow().timestamp()}",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=self.refresh_expiry),
        }
        self.token_payloads[token] = payload
        return token

    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        if token in self.revoked_tokens:
            return None

        payload = self.token_payloads.get(token)
        if not payload:
            return None

        if payload.get("type") != token_type:
            return None

        if payload.get("exp") < datetime.datetime.utcnow():
            return None

        return payload

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        payload = self.validate_token(refresh_token, "refresh")
        if not payload:
            return None

        user_id = payload["sub"]

        # Revoke old token
        self.revoke_token(refresh_token)

        # Generate new tokens
        access_token = self.generate_access_token(user_id)
        refresh_token = self.generate_refresh_token(user_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.token_expiry,
        }

    def revoke_token(self, refresh_token: str) -> bool:
        if refresh_token in self.token_payloads:
            self.revoked_tokens.add(refresh_token)
            return True
        return False

    def clean_expired_tokens(self) -> None:
        now = datetime.datetime.utcnow()
        expired_tokens = [
            token for token, payload in self.token_payloads.items() if payload.get("exp") < now
        ]
        for token in expired_tokens:
            del self.token_payloads[token]


class MockMFAService(IMFAService):
    """Mock implementation of IMFAService for testing"""

    def __init__(self):
        self.mfa_tokens = {}  # mfa_token -> user_id
        self.mfa_secrets = {}  # user_id -> secret

    def generate_secret(self) -> str:
        return "MOCK_SECRET_KEY123456"

    def generate_mfa_token(self, user_id: str) -> str:
        token = f"mock-mfa-token-{user_id}-{datetime.datetime.utcnow().timestamp()}"
        self.mfa_tokens[token] = user_id
        return token

    def verify_mfa_code(self, user_id: str, secret: str, code: str) -> bool:
        # Mock implementation always returns True for code "123456" and False otherwise
        return code == "123456"


class MockUser:
    """Mock user object for testing"""

    def __init__(
        self,
        id,
        username,
        password_hash,
        roles=None,
        mfa_enabled=False,
        mfa_secret=None,
    ):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.roles = roles or ["user"]
        self.mfa_enabled = mfa_enabled
        self.mfa_secret = mfa_secret


class MockUserService(IUserService):
    """Mock implementation of IUserService for testing"""

    def __init__(self, token_service, mfa_service):
        self.token_service = token_service
        self.mfa_service = mfa_service
        self.users = {}  # username -> user
        self.users_by_id = {}  # id -> user

        # Add a test user
        self.create_user("testuser", "password")

        # Add a test user with MFA
        user_with_mfa = self.create_user("mfa_user", "password")
        self.enable_mfa(user_with_mfa.id)

    def create_user(self, username: str, password: str, roles: Optional[List[str]] = None) -> Any:
        if username in self.users:
            raise ValueError(f"Username '{username}' is already taken")

        # Mock password hashing
        password_hash = f"hashed-{password}"

        # Create user
        user_id = str(len(self.users) + 1)
        user = MockUser(user_id, username, password_hash, roles)

        self.users[username] = user
        self.users_by_id[user_id] = user

        return user

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        user = self.users.get(username)
        if not user or user.password_hash != f"hashed-{password}":
            return None

        # Check if MFA is enabled
        if user.mfa_enabled and user.mfa_secret:
            # Generate an MFA token
            mfa_token = self.mfa_service.generate_mfa_token(user.id)

            return {"requires_mfa": True, "mfa_token": mfa_token}

        # No MFA, generate tokens
        access_token = self.token_service.generate_access_token(user.id)
        refresh_token = self.token_service.generate_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.token_service.token_expiry,
        }

    def get_user_by_id(self, user_id: str) -> Any:
        return self.users_by_id.get(user_id)

    def create_default_roles(self) -> None:
        pass  # Not needed for testing

    def enable_mfa(self, user_id: str) -> Optional[str]:
        user = self.users_by_id.get(user_id)
        if not user:
            return None

        # Generate a secret
        secret = self.mfa_service.generate_secret()

        # Save to user
        user.mfa_enabled = True
        user.mfa_secret = secret

        return secret

    def verify_mfa(self, mfa_token: str, mfa_code: str) -> Optional[Dict[str, Any]]:
        # Find user from token
        user_id = self.mfa_tokens.get(mfa_token)
        if not user_id:
            return None

        user = self.get_user_by_id(user_id)
        if not user or not user.mfa_secret:
            return None

        # Verify code
        if not self.mfa_service.verify_mfa_code(user.id, user.mfa_secret, mfa_code):
            return None

        # Generate tokens
        access_token = self.token_service.generate_access_token(user.id)
        refresh_token = self.token_service.generate_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.token_service.token_expiry,
        }


class TestAuthService:
    """Tests for AuthService using mock implementations"""

    @pytest.fixture
    def auth_service(self):
        """Create an AuthService with mock implementations"""
        token_service = MockTokenService()
        mfa_service = MockMFAService()
        user_service = MockUserService(token_service, mfa_service)

        return AuthServiceImpl(user_service, token_service, mfa_service)

    def test_create_user(self, auth_service):
        """Test creating a user"""
        user = auth_service.create_user("newuser", "password123")

        assert user is not None
        assert user.username == "newuser"
        assert user.roles == ["user"]

    def test_create_duplicate_user(self, auth_service):
        """Test creating a duplicate user"""
        # Create first user
        auth_service.create_user("unique_user", "password")

        # Try to create duplicate
        with pytest.raises(ValueError):
            auth_service.create_user("unique_user", "different_password")

    def test_authenticate_valid_user(self, auth_service):
        """Test authenticating a valid user"""
        # Create a user
        auth_service.create_user("auth_test", "valid_pass")

        # Authenticate
        result = auth_service.authenticate("auth_test", "valid_pass")

        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result

    def test_authenticate_invalid_credentials(self, auth_service):
        """Test authenticating with invalid credentials"""
        # Create a user
        auth_service.create_user("auth_test2", "correct_pass")

        # Try invalid password
        result = auth_service.authenticate("auth_test2", "wrong_pass")

        assert result is None

    def test_token_validation(self, auth_service):
        """Test token validation"""
        # Create a user and get tokens
        auth_service.create_user("token_test", "password")
        tokens = auth_service.authenticate("token_test", "password")

        # Validate access token
        payload = auth_service.validate_token(tokens["access_token"], "access")

        assert payload is not None
        assert payload["type"] == "access"

        # Try wrong token type
        invalid_payload = auth_service.validate_token(tokens["access_token"], "refresh")
        assert invalid_payload is None

    def test_token_refresh(self, auth_service):
        """Test refreshing tokens"""
        # Create a user and get tokens
        auth_service.create_user("refresh_test", "password")
        tokens = auth_service.authenticate("refresh_test", "password")

        # Refresh tokens
        new_tokens = auth_service.refresh_token(tokens["refresh_token"])

        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

        # Old refresh token should be revoked
        revoked_result = auth_service.refresh_token(tokens["refresh_token"])
        assert revoked_result is None

    def test_mfa_flow(self, auth_service):
        """Test MFA authentication flow"""
        # Get the user with MFA enabled
        user = auth_service.get_user_by_id("2")  # ID of mfa_user from MockUserService
        assert user is not None
        assert user.mfa_enabled

        # Start authentication
        result = auth_service.authenticate("mfa_user", "password")

        assert result is not None
        assert result.get("requires_mfa") is True
        assert "mfa_token" in result

        # Complete MFA verification with correct code
        mfa_result = auth_service.verify_mfa(result["mfa_token"], "123456")

        assert mfa_result is not None
        assert "access_token" in mfa_result
        assert "refresh_token" in mfa_result

        # Try MFA verification with wrong code
        wrong_result = auth_service.verify_mfa(result["mfa_token"], "999999")
        assert wrong_result is None
