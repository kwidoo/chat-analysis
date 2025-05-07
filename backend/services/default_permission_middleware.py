from functools import wraps
from typing import Callable, Dict, List, Optional, Set, Union

import jwt
from flask import Flask, current_app, g, jsonify, request
from services.default_auth_service import AuthServiceImpl


class PermissionMiddleware:
    """Middleware for role-based access control using the AuthService."""

    def __init__(self, auth_service: AuthServiceImpl):
        """
        Initialize the PermissionMiddleware with an AuthService.

        Args:
            auth_service: The AuthService instance for validating tokens
        """
        self.auth_service = auth_service
        self.endpoints: Dict[str, Set[str]] = {}  # endpoint -> required roles

    def init_app(self, app: Flask):
        """Register the middleware with a Flask app."""
        app.before_request(self._check_permissions)

    def requires_roles(self, roles: List[str]):
        """
        Decorator for route functions that require specific roles.

        Args:
            roles: List of roles required to access the endpoint
        """

        def decorator(func: Callable):
            endpoint = f"{request.endpoint}"
            self.endpoints[endpoint] = set(roles)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def _check_permissions(self):
        """Check if the current request has the required permissions."""
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return None

        # Skip auth for endpoints that don't require it
        endpoint = request.endpoint
        if not endpoint or endpoint not in self.endpoints:
            return None

        # Get required roles for this endpoint
        required_roles = self.endpoints.get(endpoint, set())
        if not required_roles:  # No roles required
            return None

        # Get token from header
        token = self.auth_service.get_token_from_header(request)
        if not token:
            return jsonify({"error": "Authorization required"}), 401

        # Validate token
        try:
            payload = self.auth_service.validate_token(token)
            if not payload:
                return jsonify({"error": "Invalid token"}), 401

            # Check if token is an access token (not a refresh token)
            if payload.type != "access":
                return jsonify({"error": "Invalid token type"}), 401

            # Check if user has the required role
            user_roles = set(payload.roles)

            # 'admin' role has access to everything
            if "admin" in user_roles:
                g.user_id = payload.sub
                g.user_roles = payload.roles
                return None

            # Check specific required roles
            if required_roles.intersection(user_roles):
                g.user_id = payload.sub
                g.user_roles = payload.roles
                return None

            return jsonify({"error": "Insufficient permissions"}), 403

        except jwt.exceptions.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401


def requires_auth(roles: List[str] = None):
    """
    Decorator for route functions that require authentication and specific roles.

    This is a standalone decorator that can be used directly on route functions
    without needing to access the PermissionMiddleware instance.

    Args:
        roles: List of roles required to access the
        endpoint (default: None, which means any authenticated user)
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip auth for OPTIONS requests (CORS preflight)
            if request.method == "OPTIONS":
                return func(*args, **kwargs)

            # Get token from header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "Authorization required"}), 401

            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({"error": "Invalid authorization format"}), 401

            token = parts[1]

            # Validate token using the auth_service from the app
            try:
                auth_service = current_app.auth_service
                payload = auth_service.validate_token(token)

                if not payload:
                    return jsonify({"error": "Invalid token"}), 401

                # Check if token is an access token (not a refresh token)
                if payload.type != "access":
                    return jsonify({"error": "Invalid token type"}), 401

                # Store user info in g for the request
                g.user_id = payload.sub
                g.user_roles = payload.roles

                # Check roles if required
                if roles:
                    user_roles = set(payload.roles)
                    required_roles = set(roles)

                    # 'admin' role has access to everything
                    if "admin" in user_roles:
                        return func(*args, **kwargs)

                    # Check if user has any of the required roles
                    if not required_roles.intersection(user_roles):
                        return jsonify({"error": "Insufficient permissions"}), 403

                return func(*args, **kwargs)

            except (jwt.exceptions.InvalidTokenError, AttributeError):
                return jsonify({"error": "Invalid token"}), 401

        return wrapper

    return decorator
