import os
import pytest

# ── Env vars MUST be set before any app import ────────────────────────────────
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["EMAIL_ADDRESS"] = "test@test.com"
os.environ["EMAIL_PASSWORD"] = "test-pass"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-testing-okay"

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Import Base and models so metadata is populated
from app.db.session import Base, get_db
import app.models.candidate   # noqa: registers models
import app.models.interview   # noqa: registers models
import app.models.ai_call      # noqa: registers models
from app.main import app

# Single shared in-memory engine for the whole test session
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # same connection shared across threads — required for in-memory SQLite
)
_SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def setup_tables():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db(setup_tables):
    session = _SessionFactory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """TestClient with get_db overridden to use the test session."""
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    # raise_server_exceptions=False so our global handler returns JSON instead of re-raising
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "reecruto-admin"})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
