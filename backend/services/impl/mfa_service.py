"""
MFA Service Implementation

This module provides an implementation of the IMFAService interface
using TOTP (Time-based One-Time Passwords) for multi-factor authentication.
"""
import datetime
import logging
import uuid
import pyotp
from typing import Dict, Any, Optional

from interfaces.auth import IMFAService


class TOTPMFAServiceImpl(IMFAService):
    """TOTP implementation of the MFA service interface"""

    def __init__(self, issuer_name: str = "AI3 Application"):
        """Initialize the TOTP MFA service

        Args:
            issuer_name: The name of the issuer for TOTP URIs
        """
        self.issuer_name = issuer_name
        self.logger = logging.getLogger(__name__)

        # In-memory storage for MFA verification tokens
        # In production, this would be in a database
        # Format: {mfa_token: {"user_id": user_id, "exp": expiration_timestamp}}
        self._mfa_tokens = {}

        # MFA token expiration time (5 minutes)
        self.mfa_token_expiry = 300

    def generate_secret(self) -> str:
        """Generate a new MFA secret

        Returns:
            The generated secret
        """
        return pyotp.random_base32()

    def generate_mfa_token(self, user_id: str) -> str:
        """Generate a temporary MFA token for verification

        Args:
            user_id: The ID of the user to generate a token for

        Returns:
            The generated MFA token
        """
        # Create a unique token
        mfa_token = str(uuid.uuid4())

        # Store token with expiration
        expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.mfa_token_expiry)

        self._mfa_tokens[mfa_token] = {
            "user_id": str(user_id),
            "exp": expiry.timestamp()
        }

        return mfa_token

    def verify_mfa_code(self, user_id: str, secret: str, code: str) -> bool:
        """Verify an MFA code

        Args:
            user_id: The ID of the user
            secret: The user's MFA secret
            code: The code to verify

        Returns:
            True if the code is valid, False otherwise
        """
        try:
            # Create a TOTP instance
            totp = pyotp.TOTP(secret)

            # Verify the code
            return totp.verify(code)

        except Exception as e:
            self.logger.error(f"Error verifying MFA code: {e}")
            return False

    def verify_mfa_token(self, mfa_token: str) -> Optional[str]:
        """Verify an MFA token and return the user ID if valid

        Args:
            mfa_token: The MFA token to verify

        Returns:
            The user ID if valid, None otherwise
        """
        # Check if token exists
        if mfa_token not in self._mfa_tokens:
            return None

        # Check if token is expired
        token_data = self._mfa_tokens[mfa_token]
        now = datetime.datetime.utcnow().timestamp()
        if token_data["exp"] < now:
            # Clean up expired token
            del self._mfa_tokens[mfa_token]
            return None

        return token_data["user_id"]

    def invalidate_mfa_token(self, mfa_token: str) -> None:
        """Invalidate an MFA token

        Args:
            mfa_token: The MFA token to invalidate
        """
        if mfa_token in self._mfa_tokens:
            del self._mfa_tokens[mfa_token]

    def clean_expired_tokens(self) -> None:
        """Clean up expired MFA tokens"""
        now = datetime.datetime.utcnow().timestamp()

        # Find expired tokens
        expired_tokens = [
            token for token, data in self._mfa_tokens.items()
            if data["exp"] < now
        ]

        # Remove expired tokens
        for token in expired_tokens:
            del self._mfa_tokens[token]

        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired MFA tokens")
