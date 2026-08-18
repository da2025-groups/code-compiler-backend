import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """TestClient with in-memory DB, bypassing real .env seeding."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models import user, question, submission  # noqa

    # StaticPool forces all threads to share one SQLite connection so the worker
    # thread processing ASGI requests sees the same in-memory DB as the fixture thread.
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine)

    import app.database as db_module
    db_module.engine = test_engine
    db_module.SessionLocal = TestSession

    # Patch seed_admin to no-op so tests don't need real admin creds; restore after
    import app.seed as seed_module
    original_seed = seed_module.seed_admin
    seed_module.seed_admin = lambda db: None

    from app.main import app
    with TestClient(app) as c:
        yield c

    seed_module.seed_admin = original_seed  # restore so test_seed.py gets the real function
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_docs_endpoint_returns_200(client):
    """GET /docs returns 200 (FastAPI Swagger UI)."""
    response = client.get("/docs")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


def test_openapi_json_returns_200(client):
    """GET /openapi.json returns 200 and reports the correct app title."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Code Compiler Platform"
    # Stub routers have no endpoints yet; route paths appear in CC-7 through CC-12
