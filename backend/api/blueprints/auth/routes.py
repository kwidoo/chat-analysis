import pyotp
from flask import Blueprint, current_app, g, jsonify, request
from services.default_mfa_service import TOTPMFAServiceImpl
from services.default_permission_middleware import requires_auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        # Create user with the auth service
        user = current_app.auth_service.create_user(username=username, password=password)

        # Generate tokens for the new user
        tokens = current_app.auth_service.generate_token_pair(user)

        return jsonify({"message": "User registered successfully", **tokens}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Registration failed: {e}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and issue JWT tokens."""
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        # Authenticate user
        auth_result = current_app.auth_service.authenticate(username=username, password=password)

        if not auth_result:
            return jsonify({"error": "Invalid credentials"}), 401

        # Check if MFA is required
        if auth_result.get("requires_mfa", False):
            return (
                jsonify(
                    {
                        "message": "MFA verification required",
                        "requires_mfa": True,
                        "mfa_token": auth_result.get("mfa_token"),
                    }
                ),
                200,
            )

        # No MFA required, return tokens
        return jsonify({"message": "Login successful", **auth_result})

    except Exception as e:
        return jsonify({"error": f"Login error: {e}"}), 500


@auth_bp.route("/verify-mfa", methods=["POST"])
def verify_mfa():
    """Validate MFA code and issue JWT tokens upon successful verification."""
    try:
        data = request.json
        mfa_token = data.get("mfa_token")
        mfa_code = data.get("mfa_code")

        if not mfa_token or not mfa_code:
            return jsonify({"error": "MFA token and code are required"}), 400

        # Verify the MFA code
        tokens = current_app.auth_service.verify_mfa(mfa_token=mfa_token, mfa_code=mfa_code)

        if not tokens:
            return jsonify({"error": "Invalid or expired MFA code"}), 401

        return jsonify({"message": "MFA verification successful", **tokens})

    except Exception:
        return jsonify({"error": "MFA verification failed"}), 500


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """Refresh an access token using a valid refresh token."""
    try:
        data = request.json
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400

        # Refresh the token
        tokens = current_app.auth_service.refresh_token(refresh_token)

        if not tokens:
            return jsonify({"error": "Invalid or expired refresh token"}), 401

        return jsonify({"message": "Token refreshed successfully", **tokens})

    except Exception as e:
        return jsonify({"error": f"Token refresh failed: {e}"}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Revoke the user's refresh token."""
    try:
        data = request.json
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400

        # Revoke the refresh token
        revoked = current_app.auth_service.revoke_token(refresh_token)

        if not revoked:
            return jsonify({"error": "Invalid token"}), 401

        return jsonify({"message": "Logged out successfully"})

    except Exception as e:
        return jsonify({"error": f"Logout failed: {e}"}), 500


@auth_bp.route("/me", methods=["GET"])
@requires_auth()
def get_profile():
    """Get the authenticated user's profile."""
    try:
        # User ID is stored in g.user_id by the requires_auth decorator
        user_id = g.user_id
        user = current_app.auth_service.get_user_by_id(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Return user profile data
        return jsonify(
            {
                "id": user.id,
                "username": user.username,
                "roles": user.role_names if hasattr(user, "role_names") else user.roles,
            }
        )

    except Exception as e:
        return jsonify({"error": f"Failed to get user profile: {str(e)}"}), 500


@auth_bp.route("/enable-mfa", methods=["POST"])
@requires_auth()
def enable_mfa():
    """Enable MFA for the authenticated user."""
    try:
        # User ID is stored in g.user_id by the requires_auth decorator
        user_id = g.user_id

        # Enable MFA and get the secret key
        secret = current_app.auth_service.enable_mfa(user_id)

        if not secret:
            return jsonify({"error": "Failed to enable MFA"}), 500

        # Generate URI for QR code generation on the client
        user = current_app.auth_service.get_user_by_id(user_id)
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.username,
            issuer_name=current_app.config.get("MFA_ISSUER_NAME", "AI3 Application"),
        )

        return jsonify({"message": "MFA enabled successfully", "secret": secret, "uri": uri})

    except Exception as e:
        return jsonify({"error": f"Failed to enable MFA: {str(e)}"}), 500


@auth_bp.route("/roles", methods=["GET"])
@requires_auth(roles=["admin"])
def get_roles():
    """Get a list of all available roles (admin only)."""
    # This is a simplified example - in a real application, roles would be stored in a database
    roles = [
        {"name": "user", "description": "Regular user with basic access"},
        {"name": "editor", "description": "Can edit and create content"},
        {"name": "admin", "description": "Full administrative access"},
    ]

    return jsonify({"roles": roles})
