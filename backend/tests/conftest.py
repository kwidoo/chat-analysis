import os
import sys
import tempfile

import pytest
from core.app_factory import create_app
from db.session import Base, db
from flask import Flask
from models.user import Role, User
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class MockFAISService:
    """Mock implementation of FAISS service for testing"""

    def __init__(self):
        self.indexes = {}

    def create_index(self, name, dimension):
        self.indexes[name] = {"dimension": dimension, "vectors": []}
        return True

    def add_vectors(self, index_name, ids, vectors):
        if index_name not in self.indexes:
            return False
        self.indexes[index_name]["vectors"].extend(list(zip(ids, vectors)))
        return True

    def search(self, index_name, query_vector, k=5):
        if index_name not in self.indexes:
            return []
        # Simulate search by returning dummy results
        return [(i, 0.9 - i * 0.1) for i in range(min(k, len(self.indexes[index_name]["vectors"])))]


class MockDaskClient:
    """Mock implementation of Dask client for testing"""

    def __init__(self):
        self.tasks = []

    def submit(self, fn, *args, **kwargs):
        task = {"fn": fn, "args": args, "kwargs": kwargs}
        self.tasks.append(task)
        return MockFuture(task)

    def gather(self, futures):
        return [f.result() for f in futures]


class MockFuture:
    """Mock Future object for Dask tasks"""

    def __init__(self, task):
        self.task = task

    def result(self):
        # For tests, just return a simple result
        return "success"


@pytest.fixture
def app():
    """Create and configure a Flask app for testing"""
    # Use an in-memory SQLite database for testing
    db_fd, db_path = tempfile.mkstemp()

    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    # Yield the app for tests to use
    with app.app_context():
        yield app

    # Clean up the database
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def db_session(app):
    """Create a new database session for testing"""
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)

    # Create tables
    Base.metadata.create_all(engine)

    yield session

    # Clean up after test
    session.remove()


@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app"""
    return app.test_cli_runner()


@pytest.fixture
def mock_faiss():
    """Provide a mock FAISS service"""
    return MockFAISService()


@pytest.fixture
def mock_dask():
    """Provide a mock Dask client"""
    return MockDaskClient()


@pytest.fixture
def auth_headers(app, db_session):
    """Create a test user and return authentication headers"""
    # Create a test user
    test_user = User(email="test@example.com", hashed_password="password123")
    db_session.add(test_user)
    db_session.commit()

    # Get auth token
    auth_service = app.di_container.get_auth_service()
    token = auth_service.create_access_token(test_user.id)

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(db_session):
    """Create and return a test user"""
    user = User(email="test@example.com", hashed_password="password123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
