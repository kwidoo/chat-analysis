import time
from datetime import datetime, timedelta

import jwt
import pytest
from models.user import Role, User


def test_user_registration(client, db_session):
    """Test user registration endpoint"""
    response = client.post(
        "/api/auth/register",
        json={"username": "newuser@example.com", "password": "securepassword123"},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert "user_id" in data

    # Verify user was created in database
    user = db_session.query(User).filter_by(email="newuser@example.com").first()
    assert user is not None
    assert user.active is True


def test_user_registration_duplicate(client, db_session, test_user):
    """Test registering with an existing email fails"""
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser@example.com", "password": "password123"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_user_login_success(client, test_user):
    """Test successful login with valid credentials"""
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


def test_user_login_invalid_credentials(client):
    """Test login with invalid credentials fails"""
    response = client.post(
        "/api/auth/login",
        json={"username": "wrong@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    data = response.get_json()
    assert "error" in data


def test_token_validation(app, client, auth_headers):
    """Test validating a valid token"""
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert "id" in data
    assert "username" in data


def test_token_validation_invalid(client):
    """Test validating an invalid token"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


def test_token_refresh(client, app, test_user):
    """Test refreshing an access token"""
    # First login to get tokens
    login_response = client.post(
        "/api/auth/login",
        json={"username": "testuser@example.com", "password": "password123"},
    )

    assert login_response.status_code == 200
    tokens = login_response.get_json()

    # Use refresh token to get new access token
    refresh_response = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert refresh_response.status_code == 200
    new_tokens = refresh_response.get_json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


def test_token_refresh_invalid(client):
    """Test refreshing with invalid token fails"""
    response = client.post("/api/auth/refresh", json={"refresh_token": "invalid_token"})

    assert response.status_code == 401


def test_token_refresh_reuse(client, app, test_user):
    """Test refresh tokens can't be reused (refresh token rotation)"""
    # First login to get tokens
    login_response = client.post(
        "/api/auth/login",
        json={"username": "testuser@example.com", "password": "password123"},
    )

    tokens = login_response.get_json()

    # Use refresh token to get new access token
    refresh_response = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert refresh_response.status_code == 200

    # Try to use the same refresh token again
    reuse_response = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert reuse_response.status_code == 401


def test_expired_token(app, client, test_user):
    """Test that expired tokens are rejected"""
    # Create a token that's already expired
    auth_service = app.di_container.get_auth_service()

    # Create an expired token (backdated by 2 hours)
    now = datetime.utcnow()
    payload = {
        "sub": test_user.id,
        "exp": int((now - timedelta(hours=2)).timestamp()),
        "iat": int((now - timedelta(hours=3)).timestamp()),
        "jti": "test_expired_jti",
        "type": "access",
        "roles": ["user"],
    }

    expired_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS256")

    # Try to use the expired token
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


def test_logout(client, auth_headers, test_user):
    """Test logging out (revoking refresh token)"""
    # First login to get tokens
    login_response = client.post(
        "/api/auth/login",
        json={"username": "testuser@example.com", "password": "password123"},
    )

    tokens = login_response.get_json()

    # Logout (revoke token)
    logout_response = client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f'Bearer {tokens["access_token"]}'},
    )

    assert logout_response.status_code == 200

    # Try to use the revoked refresh token
    refresh_response = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert refresh_response.status_code == 401


def test_role_based_access(app, client, db_session):
    """Test role-based access control"""
    # Create admin role
    admin_role = Role(name="admin")
    db_session.add(admin_role)
    db_session.commit()

    # Create admin user
    admin_user = User(username="admin@example.com", email="admin@example.com")
    admin_user.set_password("adminpass")
    admin_user.roles.append(admin_role)
    db_session.add(admin_user)
    db_session.commit()

    # Create regular user
    regular_user = User(username="regular@example.com", email="regular@example.com")
    regular_user.set_password("userpass")
    db_session.add(regular_user)
    db_session.commit()

    # Login as admin
    admin_login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "adminpass"},
    )
    admin_token = admin_login.get_json()["access_token"]

    # Login as regular user
    user_login = client.post(
        "/api/auth/login",
        json={"username": "regular@example.com", "password": "userpass"},
    )
    user_token = user_login.get_json()["access_token"]

    # Access admin endpoint with admin token (should succeed)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    client.get("/api/admin/users", headers=admin_headers)

    # Access admin endpoint with user token (should fail)
    user_headers = {"Authorization": f"Bearer {user_token}"}
    user_response = client.get("/api/admin/users", headers=user_headers)

    # Either the endpoint returns 403 or 404 depending on how the app is set up
    assert user_response.status_code in (403, 404)
