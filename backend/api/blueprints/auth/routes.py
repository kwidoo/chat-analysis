from flask import current_app, jsonify, request, g

from api.blueprints.auth import auth_bp
from services.auth_service import UserCredentials
from services.permission_middleware import requires_auth


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.json
        user_data = UserCredentials(**data)

        # Create user with the auth service
        user = current_app.auth_service.create_user(
            username=user_data.username,
            password=user_data.password
        )

        # Generate tokens for the new user
        tokens = current_app.auth_service.generate_token_pair(user)

        return jsonify({
            "message": "User registered successfully",
            **tokens
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Registration failed"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate a user and issue JWT tokens."""
    try:
        data = request.json
        user_data = UserCredentials(**data)

        # Authenticate user
        user = current_app.auth_service.authenticate(
            username=user_data.username,
            password=user_data.password
        )

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate tokens
        tokens = current_app.auth_service.generate_token_pair(user)

        return jsonify({
            "message": "Login successful",
            **tokens
        })

    except Exception as e:
        return jsonify({"error": "Login failed"}), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh an access token using a valid refresh token."""
    try:
        data = request.json
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400

        # Refresh the token
        tokens = current_app.auth_service.refresh_token(refresh_token)

        if not tokens:
            return jsonify({"error": "Invalid or expired refresh token"}), 401

        return jsonify({
            "message": "Token refreshed successfully",
            **tokens
        })

    except Exception as e:
        return jsonify({"error": "Token refresh failed"}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Revoke the user's refresh token."""
    try:
        data = request.json
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400

        # Revoke the refresh token
        revoked = current_app.auth_service.revoke_token(refresh_token)

        if not revoked:
            return jsonify({"error": "Invalid token"}), 401

        return jsonify({"message": "Logged out successfully"})

    except Exception as e:
        return jsonify({"error": "Logout failed"}), 500


@auth_bp.route('/me', methods=['GET'])
@requires_auth()
def get_profile():
    """Get the authenticated user's profile."""
    try:
        # User ID is stored in g.user_id by the requires_auth decorator
        user_id = g.user_id
        user = current_app.auth_service.get_user_by_id(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "id": user.id,
            "username": user.username,
            "roles": user.roles
        })

    except Exception as e:
        return jsonify({"error": "Failed to get user profile"}), 500


@auth_bp.route('/roles', methods=['GET'])
@requires_auth(roles=['admin'])
def get_roles():
    """Get a list of all available roles (admin only)."""
    # This is a simplified example - in a real application, roles would be stored in a database
    roles = [
        {"name": "user", "description": "Regular user with basic access"},
        {"name": "editor", "description": "Can edit and create content"},
        {"name": "admin", "description": "Full administrative access"}
    ]

    return jsonify({"roles": roles})
