import json
import os
import secrets
import time
from typing import Dict, List, Optional, Any

import requests
from flask import Flask, redirect, request, session, url_for
from pydantic import BaseModel

from services.auth_service import AuthService, User


class OAuthProvider(BaseModel):
    """Configuration for an OAuth provider."""
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str]
    redirect_path: str

    # Function to extract user data from provider response
    def extract_user_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized user info from provider-specific response."""
        if self.name == "google":
            return {
                "provider_user_id": data.get("sub"),
                "email": data.get("email"),
                "name": data.get("name"),
                "picture": data.get("picture"),
                "email_verified": data.get("email_verified", False),
            }
        elif self.name == "github":
            return {
                "provider_user_id": str(data.get("id")),
                "email": data.get("email"),
                "name": data.get("name"),
                "picture": data.get("avatar_url"),
                "email_verified": True,  # GitHub requires verified emails
            }
        # Add more providers as needed
        return {}


class OAuthIntegration:
    """Handles OAuth integration with multiple providers."""

    def __init__(self, auth_service: AuthService):
        """
        Initialize the OAuth integration service.

        Args:
            auth_service: The AuthService instance for user authentication
        """
        self.auth_service = auth_service
        self.providers: Dict[str, OAuthProvider] = {}

    def register_provider(self, provider: OAuthProvider):
        """Register an OAuth provider configuration."""
        self.providers[provider.name] = provider

    def init_app(self, app: Flask):
        """Set up OAuth routes in Flask app."""
        # Login route for each provider
        for provider_name, provider in self.providers.items():
            login_endpoint = f"oauth_login_{provider_name}"
            callback_endpoint = f"oauth_callback_{provider_name}"

            # Add login route
            app.add_url_rule(
                f"/auth/{provider_name}/login",
                login_endpoint,
                lambda p=provider_name: self._handle_login(p),
                methods=["GET"]
            )

            # Add callback route
            app.add_url_rule(
                f"/auth/{provider_name}/callback",
                callback_endpoint,
                lambda p=provider_name: self._handle_callback(p),
                methods=["GET"]
            )

        # Add session config
        app.config.setdefault('SESSION_TYPE', 'filesystem')
        app.config.setdefault('SESSION_PERMANENT', False)
        app.config.setdefault('SESSION_USE_SIGNER', True)
        app.config.setdefault('SESSION_KEY_PREFIX', 'oauth_')

        # Add utility routes
        app.add_url_rule("/auth/providers", "oauth_providers", self._list_providers, methods=["GET"])

    def _handle_login(self, provider_name: str):
        """Handle the initial OAuth login request."""
        provider = self.providers.get(provider_name)
        if not provider:
            return {"error": "Unknown provider"}, 400

        # Generate state parameter to prevent CSRF
        state = secrets.token_urlsafe(32)
        session["oauth_state"] = state

        # Build authorization URL
        params = {
            "client_id": provider.client_id,
            "redirect_uri": url_for(f"oauth_callback_{provider_name}", _external=True),
            "response_type": "code",
            "scope": " ".join(provider.scopes),
            "state": state,
        }

        # Add provider-specific parameters
        if provider_name == "google":
            params["access_type"] = "offline"  # For refresh token

        # Build the authorization URL with query parameters
        auth_url = provider.authorize_url + "?" + "&".join([f"{k}={v}" for k, v in params.items()])

        return redirect(auth_url)

    def _handle_callback(self, provider_name: str):
        """Handle the OAuth callback after user authentication."""
        provider = self.providers.get(provider_name)
        if not provider:
            return {"error": "Unknown provider"}, 400

        # Verify state parameter to prevent CSRF
        if request.args.get("state") != session.get("oauth_state"):
            return {"error": "Invalid state parameter"}, 400

        # Check for error response
        if "error" in request.args:
            return {"error": request.args.get("error")}, 400

        # Get authorization code
        code = request.args.get("code")
        if not code:
            return {"error": "No authorization code received"}, 400

        # Exchange authorization code for tokens
        token_params = {
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": url_for(f"oauth_callback_{provider_name}", _external=True),
        }

        try:
            token_response = requests.post(provider.token_url, data=token_params, timeout=10)
            token_data = token_response.json()

            if "error" in token_data:
                return {"error": token_data.get("error")}, 400

            # Get access token
            access_token = token_data.get("access_token")
            if not access_token:
                return {"error": "No access token received"}, 400

            # Get user info
            headers = {"Authorization": f"Bearer {access_token}"}
            userinfo_response = requests.get(provider.userinfo_url, headers=headers, timeout=10)
            userinfo = userinfo_response.json()

            # Extract standardized user info
            user_info = provider.extract_user_info(userinfo)

            # Find or create user
            user = self._find_or_create_user(provider_name, user_info)

            # Generate JWT tokens for our system
            tokens = self.auth_service.generate_token_pair(user)

            # Clear OAuth-related session data
            session.pop("oauth_state", None)

            # Return tokens with success response
            return {
                "message": "Authentication successful",
                **tokens
            }

        except Exception as e:
            return {"error": f"OAuth error: {str(e)}"}, 500

    def _find_or_create_user(self, provider_name: str, user_info: Dict[str, Any]) -> User:
        """Find an existing user or create a new one based on OAuth user info."""
        # In a real implementation, you'd have a database table for OAuth connections
        # For this example, we'll use the email as the primary identifier
        email = user_info.get("email")

        if not email:
            raise ValueError("Email is required from OAuth provider")

        # Look for an existing user with this email
        existing_user = next((u for u in self.auth_service._users.values()
                            if u.username == email), None)

        if existing_user:
            return existing_user

        # Create a new user (with a random password as they'll use OAuth to login)
        random_password = secrets.token_urlsafe(16)
        user = self.auth_service.create_user(
            username=email,
            password=random_password,  # They won't use this password
            roles=["user"]
        )

        return user

    def _list_providers(self):
        """Return a list of configured OAuth providers."""
        providers_list = [{"name": name} for name in self.providers.keys()]
        return {"providers": providers_list}


# Example provider configurations:
def create_google_provider(client_id: str, client_secret: str) -> OAuthProvider:
    """Create a Google OAuth provider configuration."""
    return OAuthProvider(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        authorize_url="https://accounts.google.com/o/oauth2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
        scopes=["openid", "email", "profile"],
        redirect_path="/auth/google/callback"
    )

def create_github_provider(client_id: str, client_secret: str) -> OAuthProvider:
    """Create a GitHub OAuth provider configuration."""
    return OAuthProvider(
        name="github",
        client_id=client_id,
        client_secret=client_secret,
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
        scopes=["read:user", "user:email"],
        redirect_path="/auth/github/callback"
    )
