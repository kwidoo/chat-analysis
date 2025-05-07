"""
User Service Implementation

This module provides an implementation of the IUserService interface
managing user accounts, authentication and role management.
"""

import logging
from typing import Any, Dict, List, Optional

import bcrypt
from db.session import db
from interfaces.auth import IMFAService, ITokenService, IUserService
from models.user import User
from sqlalchemy.orm.exc import NoResultFound


class UserServiceImpl(IUserService):
    """Implementation of the user service interface"""

    def __init__(self, token_service: ITokenService, mfa_service: IMFAService):
        """Initialize the user service

        Args:
            token_service: Token service for generating authentication tokens
            mfa_service: MFA service for multi-factor authentication
        """
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
        # Check if username already exists
        existing_user = db.session.query(User).filter_by(username=username).first()
        if existing_user:
            raise ValueError(f"Username '{username}' is already taken")

        # Hash the password
        password_hash = self._hash_password(password)

        # Set default roles if none provided
        roles = roles or ["user"]

        # Create the user
        user = User(
            username=username,
            password_hash=password_hash,
            roles=roles,
            mfa_enabled=False,
            mfa_secret=None,
        )

        # Save the user to the database
        db.session.add(user)
        db.session.commit()

        self.logger.info(f"Created user: {username} with roles: {roles}")

        return user

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a user with username and password

        Args:
            username: The username to authenticate
            password: The password to authenticate

        Returns:
            Authentication result containing tokens or MFA details if needed
        """
        try:
            # Find the user
            user = db.session.query(User).filter_by(username=username).one()

            # Check the password
            if not self._verify_password(password, user.password_hash):
                self.logger.warning(f"Failed login attempt for user: {username} (invalid password)")
                return None

            # Check if MFA is enabled
            if user.mfa_enabled and user.mfa_secret:
                # Generate an MFA token for verification
                mfa_token = self.mfa_service.generate_mfa_token(user.id)

                return {"requires_mfa": True, "mfa_token": mfa_token}

            # No MFA required, generate tokens
            access_token = self.token_service.generate_access_token(user.id)
            refresh_token = self.token_service.generate_refresh_token(user.id)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": self.token_service.token_expiry,
            }

        except NoResultFound:
            self.logger.warning(f"Login attempt for non-existent user: {username}")
            return None
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID

        Args:
            user_id: The ID of the user to get

        Returns:
            The user object or None if not found
        """
        try:
            return db.session.query(User).filter_by(id=user_id).one()
        except NoResultFound:
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    def create_default_roles(self) -> None:
        """Create default roles for the application"""
        # This is just to ensure we have our basic roles set up
        # In a production system, roles would be stored in a separate table
        roles = ["user", "editor", "admin"]

        self.logger.info(f"Default roles setup completed: {roles}")

    def enable_mfa(self, user_id: str) -> Optional[str]:
        """Enable MFA for a user

        Args:
            user_id: The ID of the user

        Returns:
            The MFA secret if successful, None otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None

            # Generate a new MFA secret
            secret = self.mfa_service.generate_secret()

            # Save the secret to the user
            user.mfa_secret = secret
            user.mfa_enabled = True
            db.session.commit()

            return secret

        except Exception as e:
            self.logger.error(f"Error enabling MFA for user {user_id}: {e}")
            return None

    def verify_mfa(self, mfa_token: str, mfa_code: str) -> Optional[Dict[str, Any]]:
        """Verify an MFA code and generate tokens if valid

        Args:
            mfa_token: The MFA token from the first authentication step
            mfa_code: The MFA code from the user's authenticator app

        Returns:
            Tokens if verification is successful, None otherwise
        """
        # Verify the MFA token and get the user ID
        user_id = self.mfa_service.verify_mfa_token(mfa_token)
        if not user_id:
            self.logger.warning("Invalid or expired MFA token")
            return None

        # Get the user
        user = self.get_user_by_id(user_id)
        if not user or not user.mfa_secret:
            self.logger.warning(f"User not found or MFA not enabled for user {user_id}")
            return None

        # Verify the MFA code
        if not self.mfa_service.verify_mfa_code(user.id, user.mfa_secret, mfa_code):
            self.logger.warning(f"Invalid MFA code for user {user_id}")
            return None

        # Invalidate the MFA token (one-time use)
        self.mfa_service.invalidate_mfa_token(mfa_token)

        # Generate access and refresh tokens
        access_token = self.token_service.generate_access_token(user.id)
        refresh_token = self.token_service.generate_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.token_service.token_expiry,
        }

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt

        Args:
            password: The password to hash

        Returns:
            The hashed password
        """
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

        # Convert bytes to string for storage
        return hashed.decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a hash

        Args:
            password: The password to verify
            password_hash: The hash to verify against

        Returns:
            True if the password matches the hash, False otherwise
        """
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
