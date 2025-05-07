"""
Auth Service Implementation

This module provides a composite implementation of the IAuthService interface
that delegates to specialized services (user, token, MFA) following the
Interface Segregation Principle (I in SOLID).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import jwt
import pyotp
from interfaces.auth import IAuthService, IMFAService, ITokenService, IUserService
from models.user import User


class MFAVerification(IMFAService):
    """Implementation of the IMFAService interface for Multi-Factor Authentication."""

    def __init__(self):
        self.issuer_name = "AI3App"

    def generate_mfa_secret(self, user_id: str) -> str:
        """Generate a new MFA secret for a user."""
        secret = pyotp.random_base32()
        return secret

    def get_mfa_provisioning_uri(self, user_id: str, secret: str) -> str:
        """Generate a provisioning URI for the user's MFA setup."""
        return pyotp.totp.TOTP(secret).provisioning_uri(name=user_id, issuer_name=self.issuer_name)

    def verify_mfa_code(self, secret: str, code: str) -> bool:
        """Verify the provided MFA code against the secret."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)


class TokenService(ITokenService):
    """Implementation of the ITokenService interface for JWT token management."""

    def __init__(
        self, secret_key: str, access_token_expiry: int = 15, refresh_token_expiry: int = 1440
    ):
        """Initialize the TokenService with secret key and token expiry durations."""
        self.secret_key = secret_key
        self.access_token_expiry = access_token_expiry  # in minutes
        self.refresh_token_expiry = refresh_token_expiry  # in minutes

    def generate_access_token(self, user_id: str) -> str:
        """Generate a new access token for a user."""
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=self.access_token_expiry),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate a new refresh token for a user."""
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=self.refresh_token_expiry),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Validate a token and return its payload if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token using a valid refresh token."""
        payload = self.validate_token(refresh_token, token_type="refresh")
        if not payload:
            return None
        user_id = payload.get("sub")
        return {
            "access_token": self.generate_access_token(user_id),
            "refresh_token": self.generate_refresh_token(user_id),
        }

    def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token (not implemented in this example)."""
        # Token revocation would require a persistent store to track revoked tokens.
        return True

    def clean_expired_tokens(self) -> None:
        """Clean up expired tokens (not implemented in this example)."""
        pass


class AuthServiceImpl(IAuthService):
    """Composite implementation of the auth service interface

    This class delegates to specialized services for specific responsibilities,
    implementing the Interface Segregation Principle.
    """

    def __init__(
        self,
        user_service: IUserService,
        token_service: ITokenService,
        mfa_service: IMFAService,
    ):
        """Initialize the auth service

        Args:
            user_service: Service for user management operations
            token_service: Service for token management operations
            mfa_service: Service for MFA operations
        """
        self.user_service = user_service
        self.token_service = token_service
        self.mfa_service = mfa_service
        self.logger = logging.getLogger(__name__)

    def create_user(self, username: str, password: str, roles: Optional[List[str]] = None) -> User:
        """Create a new user

        Args:
            username: The username for the new user
            password: The password for the new user
            roles: Optional list of roles to assign to the user

        Returns:
            The created user object

        Raises:
            ValueError: If user creation fails, e.g., username already exists
        """
        return self.user_service.create_user(username, password, roles)

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a user and issue tokens

        Args:
            username: The username to authenticate
            password: The password to authenticate

        Returns:
            Authentication result containing tokens or MFA details if needed
        """
        return self.user_service.authenticate(username, password)

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token using a refresh token

        Args:
            refresh_token: The refresh token to use

        Returns:
            Dictionary with new access and refresh tokens, or None if invalid
        """
        return self.token_service.refresh_token(refresh_token)

    def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token

        Args:
            refresh_token: The refresh token to revoke

        Returns:
            True if the token was revoked, False otherwise
        """
        return self.token_service.revoke_token(refresh_token)

    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Validate a token and return its payload

        Args:
            token: The token to validate
            token_type: The type of token ('access' or 'refresh')

        Returns:
            The payload of the token if valid, None otherwise
        """
        return self.token_service.validate_token(token, token_type)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID

        Args:
            user_id: The ID of the user to get

        Returns:
            The user object or None if not found
        """
        return self.user_service.get_user_by_id(user_id)

    def enable_mfa(self, user_id: str) -> Optional[str]:
        """Enable MFA for a user and return the secret

        Args:
            user_id: The ID of the user

        Returns:
            The MFA secret if successful, None otherwise
        """
        return self.user_service.enable_mfa(user_id)

    def verify_mfa(self, mfa_token: str, mfa_code: str) -> Optional[Dict[str, Any]]:
        """Verify an MFA code and issue tokens if valid

        Args:
            mfa_token: The MFA token from the first authentication step
            mfa_code: The MFA code from the user's authenticator app

        Returns:
            Tokens if verification is successful, None otherwise
        """
        return self.user_service.verify_mfa(mfa_token, mfa_code)

    def generate_token_pair(self, user: User) -> Dict[str, Any]:
        """Generate access and refresh tokens for a user

        Args:
            user: The user to generate tokens for

        Returns:
            Dictionary with access and refresh tokens
        """
        access_token = self.token_service.generate_access_token(user.id)
        refresh_token = self.token_service.generate_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.token_service.token_expiry,
        }

    def create_default_roles(self) -> None:
        """Create default roles for the application"""
        self.user_service.create_default_roles()

    def clean_expired_tokens(self) -> None:
        """Clean up expired tokens from storage"""
        self.token_service.clean_expired_tokens()
