"""
Auth Service Interfaces

This module defines interfaces for authentication-related services,
implementing the Interface Segregation Principle (I in SOLID).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any


class IUserService(ABC):
    """Interface for user management operations"""

    @abstractmethod
    def create_user(self, username: str, password: str, roles: Optional[List[str]] = None) -> Any:
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
        pass

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a user with username and password

        Args:
            username: The username to authenticate
            password: The password to authenticate

        Returns:
            Authentication result containing tokens or MFA details if needed
            Format: {
                "access_token": str,
                "refresh_token": str,
                "requires_mfa": bool,
                "mfa_token": Optional[str],
                "expires_in": int
            }
        """
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Any:
        """Get a user by ID

        Args:
            user_id: The ID of the user to get

        Returns:
            The user object or None if not found
        """
        pass

    @abstractmethod
    def create_default_roles(self) -> None:
        """Create default roles for the application"""
        pass


class ITokenService(ABC):
    """Interface for token management operations"""

    @abstractmethod
    def generate_access_token(self, user_id: str) -> str:
        """Generate an access token for a user

        Args:
            user_id: The ID of the user to generate a token for

        Returns:
            The generated access token
        """
        pass

    @abstractmethod
    def generate_refresh_token(self, user_id: str) -> str:
        """Generate a refresh token for a user

        Args:
            user_id: The ID of the user to generate a token for

        Returns:
            The generated refresh token
        """
        pass

    @abstractmethod
    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Validate a token and return its payload

        Args:
            token: The token to validate
            token_type: The type of token ('access' or 'refresh')

        Returns:
            The payload of the token if valid, None otherwise
        """
        pass

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token using a refresh token

        This method should handle the rotation of refresh tokens for security.

        Args:
            refresh_token: The refresh token to use

        Returns:
            Dictionary with new access and refresh tokens, or None if invalid
            Format: {
                "access_token": str,
                "refresh_token": str,
                "expires_in": int
            }
        """
        pass

    @abstractmethod
    def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token

        Args:
            refresh_token: The refresh token to revoke

        Returns:
            True if the token was revoked, False otherwise
        """
        pass

    @abstractmethod
    def clean_expired_tokens(self) -> None:
        """Clean up expired tokens from storage"""
        pass


class IMFAService(ABC):
    """Interface for Multi-Factor Authentication operations"""

    @abstractmethod
    def generate_secret(self) -> str:
        """Generate a new MFA secret

        Returns:
            The generated secret
        """
        pass

    @abstractmethod
    def generate_mfa_token(self, user_id: str) -> str:
        """Generate a temporary MFA token for verification

        Args:
            user_id: The ID of the user to generate a token for

        Returns:
            The generated MFA token
        """
        pass

    @abstractmethod
    def verify_mfa_code(self, user_id: str, secret: str, code: str) -> bool:
        """Verify an MFA code

        Args:
            user_id: The ID of the user
            secret: The user's MFA secret
            code: The code to verify

        Returns:
            True if the code is valid, False otherwise
        """
        pass


class IAuthService(ABC):
    """Composite interface for authentication operations

    This interface combines functionality from IUserService, ITokenService, and IMFAService
    for backward compatibility. In new code, prefer using the more specific interfaces.
    """

    @abstractmethod
    def create_user(self, username: str, password: str, roles: Optional[List[str]] = None) -> Any:
        """Create a new user"""
        pass

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a user and issue tokens"""
        pass

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token using a refresh token"""
        pass

    @abstractmethod
    def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        pass

    @abstractmethod
    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Validate a token and return its payload"""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Any:
        """Get a user by ID"""
        pass

    @abstractmethod
    def enable_mfa(self, user_id: str) -> Optional[str]:
        """Enable MFA for a user and return the secret"""
        pass

    @abstractmethod
    def verify_mfa(self, mfa_token: str, mfa_code: str) -> Optional[Dict[str, Any]]:
        """Verify an MFA code and issue tokens if valid"""
        pass

    @abstractmethod
    def generate_token_pair(self, user: Any) -> Dict[str, Any]:
        """Generate access and refresh tokens for a user"""
        pass

    @abstractmethod
    def create_default_roles(self) -> None:
        """Create default roles for the application"""
        pass

    @abstractmethod
    def clean_expired_tokens(self) -> None:
        """Clean up expired tokens from storage"""
        pass
