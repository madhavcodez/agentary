import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.deps import get_db
from app.main import app


# Use the real secretairy DB for integration tests
TEST_DB_URL = "postgresql://soundscore:soundscore@localhost:5432/secretairy"
engine = create_engine(TEST_DB_URL, future=True)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_gemini():
    with patch("app.services.gemini.get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_qdrant():
    with patch("app.services.qdrant_store.get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client
