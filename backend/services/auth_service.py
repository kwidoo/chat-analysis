import datetime
import uuid
from typing import Dict, List, Optional, Tuple, Any

import bcrypt
import jwt
from flask import current_app, Request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str  # Subject (user ID)
    exp: int  # Expiration time
    iat: int  # Issued at
    jti: str  # JWT ID (unique identifier)
    type: str  # Token type (access or refresh)
    roles: List[str] = []  # User roles


class UserCredentials(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: str
    username: str
    password_hash: str
    active: bool
    roles: List[str] = []
    refresh_tokens: Dict[str, Dict] = {}  # token_id -> {exp, revoked}


class AuthService:
    """Service for handling authentication and authorization using JWT tokens."""

    def __init__(self, secret_key: str, token_expiry: int = 3600, refresh_expiry: int = 86400 * 7):
        """
        Initialize the AuthService.

        Args:
            secret_key: Secret key for JWT token signing
            token_expiry: Access token expiry time in seconds (default: 1 hour)
            refresh_expiry: Refresh token expiry time in seconds (default: 7 days)
        """
        self.secret_key = secret_key
        self.token_expiry = token_expiry
        self.refresh_expiry = refresh_expiry
        self._users = {}  # In-memory user store (replace with DB in production)

    def create_user(self, username: str, password: str, roles: List[str] = ["user"]) -> User:
        """Create a new user with the given credentials and roles."""
        if username in [user.username for user in self._users.values()]:
            raise ValueError(f"Username '{username}' already exists")

        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        user = User(
            id=user_id,
            username=username,
            password_hash=password_hash,
            active=True,
            roles=roles,
            refresh_tokens={}
        )

        self._users[user_id] = user
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with the given credentials."""
        user = next((u for u in self._users.values() if u.username == username and u.active), None)

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return user

        return None

    def generate_token_pair(self, user: User) -> Dict[str, str]:
        """Generate a new access and refresh token pair for the user."""
        now = datetime.datetime.utcnow()

        # Create access token
        access_jti = str(uuid.uuid4())
        access_exp = now + datetime.timedelta(seconds=self.token_expiry)
        access_payload = {
            'sub': user.id,
            'exp': int(access_exp.timestamp()),
            'iat': int(now.timestamp()),
            'jti': access_jti,
            'type': 'access',
            'roles': user.roles
        }
        access_token = jwt.encode(access_payload, self.secret_key, algorithm='HS256')

        # Create refresh token
        refresh_jti = str(uuid.uuid4())
        refresh_exp = now + datetime.timedelta(seconds=self.refresh_expiry)
        refresh_payload = {
            'sub': user.id,
            'exp': int(refresh_exp.timestamp()),
            'iat': int(now.timestamp()),
            'jti': refresh_jti,
            'type': 'refresh'
        }
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm='HS256')

        # Store refresh token reference
        user.refresh_tokens[refresh_jti] = {
            'exp': int(refresh_exp.timestamp()),
            'revoked': False
        }

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': self.token_expiry
        }

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Generate a new token pair using a valid refresh token."""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=['HS256'])
            token_data = TokenPayload(**payload)

            # Validate token type
            if token_data.type != 'refresh':
                return None

            # Get user
            user = self._users.get(token_data.sub)
            if not user or not user.active:
                return None

            # Check if refresh token exists and is not revoked
            token_info = user.refresh_tokens.get(token_data.jti)
            if not token_info or token_info.get('revoked', False):
                return None

            # Revoke the used refresh token (rotation)
            user.refresh_tokens[token_data.jti]['revoked'] = True

            # Generate new token pair
            return self.generate_token_pair(user)

        except (ExpiredSignatureError, InvalidTokenError):
            return None

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validate a JWT token and return the payload if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_data = TokenPayload(**payload)

            # Verify user exists and is active
            user = self._users.get(token_data.sub)
            if not user or not user.active:
                return None

            # If it's a refresh token, verify it's not revoked
            if token_data.type == 'refresh':
                token_info = user.refresh_tokens.get(token_data.jti)
                if not token_info or token_info.get('revoked', False):
                    return None

            return token_data

        except (ExpiredSignatureError, InvalidTokenError):
            return None

    def revoke_token(self, token: str) -> bool:
        """Revoke a refresh token so it can no longer be used."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_data = TokenPayload(**payload)

            if token_data.type != 'refresh':
                return False

            user = self._users.get(token_data.sub)
            if not user:
                return False

            if token_data.jti in user.refresh_tokens:
                user.refresh_tokens[token_data.jti]['revoked'] = True
                return True

            return False

        except (ExpiredSignatureError, InvalidTokenError):
            return False

    def clean_expired_tokens(self):
        """Clean up expired refresh tokens from user records."""
        now = int(datetime.datetime.utcnow().timestamp())

        for user in self._users.values():
            # Create a list of expired token IDs
            expired_tokens = [
                token_id for token_id, token_data in user.refresh_tokens.items()
                if token_data['exp'] < now
            ]

            # Remove expired tokens
            for token_id in expired_tokens:
                del user.refresh_tokens[token_id]

    def get_token_from_header(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        return parts[1]

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve a user by their ID."""
        return self._users.get(user_id)
