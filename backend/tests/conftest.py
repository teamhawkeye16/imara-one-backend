"""
Pytest configuration and shared fixtures for IMARA ONE Search
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.config import settings
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.domain import Domain
from backend.app.models.document import Document

# Use in-memory SQLite database for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db_session):
    """Seed test data for search and retrieval tests."""
    domain = Domain(
        domain_name="docs.imaraone.com",
        is_allowed=True,
    )
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)

    doc1 = Document(
        domain_id=domain.id,
        url="https://docs.imaraone.com/privacy-guide",
        title="IMARA ONE Privacy Guide and Cybersecurity Architecture",
        meta_description="Comprehensive guide to privacy-first search and threat protection.",
        clean_text=(
            "IMARA ONE Search delivers independent privacy-first search protection without tracking users. "
            "Our cybersecurity ecosystem integrates zero knowledge queries, encrypted transit, and verifiable citations."
        ),
        content_hash="hash_1111111111111111111111111111111111111111111111111111111111111111",
        word_count=32,
    )

    doc2 = Document(
        domain_id=domain.id,
        url="https://docs.imaraone.com/threat-shield",
        title="IMARA ONE Shield Network Defense",
        meta_description="Intelligent network defense and automated threat detection.",
        clean_text=(
            "The IMARA ONE Shield component inspects network traffic and blocks malicious telemetry, "
            "safeguarding endpoints across the distributed cloud."
        ),
        content_hash="hash_2222222222222222222222222222222222222222222222222222222222222222",
        word_count=24,
    )

    db_session.add(doc1)
    db_session.add(doc2)
    db_session.commit()

    return db_session

