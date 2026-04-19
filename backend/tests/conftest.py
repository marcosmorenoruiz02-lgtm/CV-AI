"""Shared fixtures for backend API tests."""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Test data prefix for cleanup
TEST_PREFIX = "TEST_"

@pytest.fixture(scope="session")
def mongo_client():
    """MongoDB client for direct DB operations."""
    client = MongoClient(MONGO_URL)
    yield client
    client.close()

@pytest.fixture(scope="session")
def db(mongo_client):
    """Database instance."""
    return mongo_client[DB_NAME]

@pytest.fixture(scope="session")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="session")
def test_user_and_session(db):
    """Create a test user and valid session in MongoDB."""
    timestamp = int(datetime.now().timestamp() * 1000)
    user_id = f"{TEST_PREFIX}user_{timestamp}"
    session_token = f"{TEST_PREFIX}session_{timestamp}"
    email = f"test.user.{timestamp}@example.com"
    
    # Create user with mode field
    user_doc = {
        "user_id": user_id,
        "email": email,
        "name": "Test User",
        "picture": "https://via.placeholder.com/150",
        "headline": "Senior Product Designer",
        "skills": ["React", "Product Design", "User Research", "Figma"],
        "experience": [
            {
                "role": "Senior Product Designer",
                "company": "Atlas",
                "period": "2022 - Present",
                "description": "Lead design system development"
            }
        ],
        "cv_raw_text": "",
        "mode": "professional",  # New field for dual-mode support
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db.users.insert_one(user_doc)
    
    # Create valid session (expires in 7 days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db.user_sessions.insert_one(session_doc)
    
    yield {
        "user_id": user_id,
        "session_token": session_token,
        "email": email,
        "name": "Test User"
    }
    
    # Cleanup
    db.users.delete_many({"user_id": {"$regex": f"^{TEST_PREFIX}"}})
    db.user_sessions.delete_many({"session_token": {"$regex": f"^{TEST_PREFIX}"}})
    db.analyses.delete_many({"user_id": {"$regex": f"^{TEST_PREFIX}"}})
    db.generated_cvs.delete_many({"user_id": {"$regex": f"^{TEST_PREFIX}"}})

@pytest.fixture(scope="session")
def expired_session(db, test_user_and_session):
    """Create an expired session for testing session expiry."""
    timestamp = int(datetime.now().timestamp() * 1000)
    expired_token = f"{TEST_PREFIX}expired_session_{timestamp}"
    
    # Create expired session (expired 1 hour ago)
    expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    session_doc = {
        "user_id": test_user_and_session["user_id"],
        "session_token": expired_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db.user_sessions.insert_one(session_doc)
    
    return expired_token

@pytest.fixture
def authenticated_client(api_client, test_user_and_session):
    """Session with auth header."""
    api_client.headers.update({
        "Authorization": f"Bearer {test_user_and_session['session_token']}"
    })
    return api_client

@pytest.fixture
def auth_headers(test_user_and_session):
    """Just the auth headers dict."""
    return {"Authorization": f"Bearer {test_user_and_session['session_token']}"}
