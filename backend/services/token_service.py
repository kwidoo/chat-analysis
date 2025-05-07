"""
JWT Token Service Implementation

This module provides an implementation of the ITokenService interface
using JSON Web Tokens (JWT) for authentication.
"""

import datetime
import logging
import jwt
import uuid
from typing import Dict, Any, Optional

from interfaces.auth import ITokenService


class JWTTokenServiceImpl(ITokenService):
    """JWT implementation of the token service interface"""

    def __init__(self, secret_key: str, token_expiry: int = 3600, refresh_expiry: int = 604800):
        """Initialize the JWT token service

        Args:
            secret_key: The secret key for signing tokens
            token_expiry: Access token expiration time in seconds (default: 1 hour)
            refresh_expiry: Refresh token expiration time in seconds (default: 7 days)
        """
        self.secret_key = secret_key
        self.token_expiry = token_expiry
        self.refresh_expiry = refresh_expiry
        self.logger = logging.getLogger(__name__)

        # In-memory token storage (in production, this would be in a database)
        # Format: {refresh_token_id: {"user_id": user_id, "exp": expiration_timestamp}}
        self._refresh_tokens = {}

    def generate_access_token(self, user_id: str) -> str:
        """Generate an access token for a user

        Args:
            user_id: The ID of the user to generate a token for

        Returns:
            The generated access token
        """
        now = datetime.datetime.utcnow()
        expiry = now + datetime.timedelta(seconds=self.token_expiry)

        payload = {"exp": expiry, "iat": now, "sub": str(user_id), "type": "access"}

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        # Convert bytes to string if necessary (depending on PyJWT version)
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate a refresh token for a user

        Args:
            user_id: The ID of the user to generate a token for

        Returns:
            The generated refresh token
        """
        now = datetime.datetime.utcnow()
        expiry = now + datetime.timedelta(seconds=self.refresh_expiry)

        # Generate a refresh token ID
        refresh_token_id = str(uuid.uuid4())

        payload = {
            "exp": expiry,
            "iat": now,
            "sub": str(user_id),
            "jti": refresh_token_id,  # JWT ID - unique identifier
            "type": "refresh",
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        # Convert bytes to string if necessary
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        # Store the refresh token for validation
        self._refresh_tokens[refresh_token_id] = {
            "user_id": str(user_id),
            "exp": expiry.timestamp(),
        }

        return token

    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Validate a token and return its payload

        Args:
            token: The token to validate
            token_type: The type of token ('access' or 'refresh')

        Returns:
            The payload of the token if valid, None otherwise
        """
        try:
            # Decode the token
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Check token type
            if payload.get("type") != token_type:
                self.logger.warning(
                    f"Token type mismatch: expected {token_type}, got {payload.get('type')}"
                )
                return None

            # For refresh tokens, also check if it's in our store
            if token_type == "refresh" and "jti" in payload:
                if payload["jti"] not in self._refresh_tokens:
                    self.logger.warning(f"Refresh token not found in store: {payload['jti']}")
                    return None

            return payload

        except jwt.ExpiredSignatureError:
            self.logger.warning("Token validation failed: expired signature")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Token validation failed: {e}")
            return None

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token using a refresh token

        This method handles rotation of refresh tokens for security.

        Args:
            refresh_token: The refresh token to use

        Returns:
            Dictionary with new access and refresh tokens, or None if invalid
        """
        # Validate the refresh token
        payload = self.validate_token(refresh_token, token_type="refresh")
        if not payload:
            return None

        user_id = payload["sub"]
        token_id = payload["jti"]

        # Revoke the old refresh token
        if token_id in self._refresh_tokens:
            del self._refresh_tokens[token_id]

        # Generate new tokens
        new_access_token = self.generate_access_token(user_id)
        new_refresh_token = self.generate_refresh_token(user_id)

        # Return the new tokens
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "expires_in": self.token_expiry,
        }

    def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token

        Args:
            refresh_token: The refresh token to revoke

        Returns:
            True if the token was revoked, False otherwise
        """
        try:
            # Decode the token without validation to get the token ID
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=["HS256"])
            token_id = payload.get("jti")

            # Remove the token from the store if it exists
            if token_id in self._refresh_tokens:
                del self._refresh_tokens[token_id]
                return True

            return False

        except jwt.PyJWTError as e:
            self.logger.warning(f"Failed to revoke token: {e}")
            return False

    def clean_expired_tokens(self) -> None:
        """Clean up expired tokens from storage"""
        now = datetime.datetime.utcnow().timestamp()

        # Find expired tokens
        expired_tokens = [
            token_id for token_id, data in self._refresh_tokens.items() if data["exp"] < now
        ]

        # Remove expired tokens
        for token_id in expired_tokens:
            del self._refresh_tokens[token_id]

        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
