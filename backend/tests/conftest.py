"""
Pytest configuration and fixtures for backend tests.
"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set test environment variables before importing config
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'
os.environ["ADMIN_EMAIL"] = "admin@test.com"
os.environ["ADMIN_PASSWORD"] = "TestAdmin123!"
# Generate a valid Fernet key for TOTP encryption (base64-encoded 32 bytes)
os.environ["TOTP_ENCRYPTION_KEY"] = "P0LYDU58oBna0xcCcu-fgUPuS02-HzzJRarCoSA1ySA="

from authentication.auth import create_access_token, get_password_hash  # noqa: E402
from repositories.database import Base, get_db  # noqa: E402
import repositories.db_models as db_models  # noqa: E402

# Test database engine (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_session):
    """Alias for db_session for backward compatibility."""
    return db_session


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden database dependency."""
    from main import app
    from helpers.rate_limiter import limiter

    # Reset rate limiter storage before each test to prevent rate limit errors
    limiter.reset()

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
def test_user(db_session) -> db_models.User:
    """Create a test user."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="test@example.com",
        username="testuser",
        display_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_global_admin=False,
        # Consent fields (Law 25 compliance)
        consent_terms_accepted=True,
        consent_privacy_accepted=True,
        consent_terms_version="1.0",
        consent_privacy_version="1.0",
        consent_timestamp=now,
        marketing_consent=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> db_models.User:
    """Create a global admin user."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="admin@example.com",
        username="adminuser",
        display_name="Admin User",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_global_admin=True,
        # Consent fields (Law 25 compliance)
        consent_terms_accepted=True,
        consent_privacy_accepted=True,
        consent_terms_version="1.0",
        consent_privacy_version="1.0",
        consent_timestamp=now,
        marketing_consent=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_category(db_session) -> db_models.Category:
    """Create a test category."""
    category = db_models.Category(
        name_en="Test Category",
        name_fr="Catégorie Test",
        description_en="A test category",
        description_fr="Une catégorie de test",
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def test_idea(db_session, test_user, test_category) -> db_models.Idea:
    """Create an approved test idea."""
    idea = db_models.Idea(
        title="Test Idea",
        description="Test idea description that is long enough to pass validation.",
        category_id=test_category.id,
        user_id=test_user.id,
        status=db_models.IdeaStatus.APPROVED,
    )
    db_session.add(idea)
    db_session.commit()
    db_session.refresh(idea)
    return idea


@pytest.fixture
def pending_idea(db_session, test_user, test_category) -> db_models.Idea:
    """Create a pending test idea."""
    idea = db_models.Idea(
        title="Pending Idea",
        description="A pending idea description that is long enough for validation.",
        category_id=test_category.id,
        user_id=test_user.id,
        status=db_models.IdeaStatus.PENDING,
    )
    db_session.add(idea)
    db_session.commit()
    db_session.refresh(idea)
    return idea


@pytest.fixture
def test_tag(db_session) -> db_models.Tag:
    """Create a test tag."""
    tag = db_models.Tag(
        name="testtag",
        display_name="TestTag",
    )
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Get authentication headers for test user."""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user) -> dict:
    """Get authentication headers for admin user."""
    token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_votes(db_session, test_user):
    """Factory fixture to create votes for an idea."""

    def _create_votes(idea_id: int, upvotes: int = 0, downvotes: int = 0):
        """Create specified number of upvotes and downvotes."""
        users_created = []

        for i in range(upvotes):
            user = db_models.User(
                email=f"upvoter{i}@example.com",
                username=f"upvoter{i}",
                display_name=f"Upvoter {i}",
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_global_admin=False,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            users_created.append(user)

            vote = db_models.Vote(
                idea_id=idea_id,
                user_id=user.id,
                vote_type=db_models.VoteType.UPVOTE,
            )
            db_session.add(vote)

        for i in range(downvotes):
            user = db_models.User(
                email=f"downvoter{i}@example.com",
                username=f"downvoter{i}",
                display_name=f"Downvoter {i}",
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_global_admin=False,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            users_created.append(user)

            vote = db_models.Vote(
                idea_id=idea_id,
                user_id=user.id,
                vote_type=db_models.VoteType.DOWNVOTE,
            )
            db_session.add(vote)

        db_session.commit()
        return users_created

    return _create_votes


@pytest.fixture
def other_user(db_session) -> db_models.User:
    """Create another test user (for permission tests)."""
    user = db_models.User(
        email="other@example.com",
        username="otheruser",
        display_name="Other User",
        hashed_password=get_password_hash("otherpassword123"),
        is_active=True,
        is_global_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def deleted_idea(db_session, test_user, test_category, admin_user) -> db_models.Idea:
    """Create a soft-deleted test idea."""
    from datetime import UTC, datetime

    idea = db_models.Idea(
        title="Deleted Idea",
        description="A soft-deleted idea for testing purposes.",
        category_id=test_category.id,
        user_id=test_user.id,
        status=db_models.IdeaStatus.APPROVED,
        deleted_at=datetime.now(UTC),
        deleted_by=admin_user.id,
        deletion_reason="Test deletion",
    )
    db_session.add(idea)
    db_session.commit()
    db_session.refresh(idea)
    return idea


@pytest.fixture
def rejected_idea(db_session, test_user, test_category) -> db_models.Idea:
    """Create a rejected test idea."""
    idea = db_models.Idea(
        title="Rejected Idea",
        description="A rejected idea for testing purposes.",
        category_id=test_category.id,
        user_id=test_user.id,
        status=db_models.IdeaStatus.REJECTED,
        admin_comment="Does not meet community guidelines",
    )
    db_session.add(idea)
    db_session.commit()
    db_session.refresh(idea)
    return idea


@pytest.fixture
def test_quality(db_session) -> db_models.Quality:
    """Create a test quality."""
    quality = db_models.Quality(
        key="test_quality",
        name_en="Test Quality",
        name_fr="Qualité Test",
        description_en="A test quality",
        description_fr="Une qualité de test",
        icon="star",
        color="blue-500",
        is_default=True,
        is_active=True,
        display_order=1,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


@pytest.fixture
def official_user(db_session) -> db_models.User:
    """Create an official user."""
    user = db_models.User(
        email="official@example.com",
        username="officialuser",
        display_name="Official User",
        hashed_password=get_password_hash("officialpassword123"),
        is_active=True,
        is_global_admin=False,
        is_official=True,
        official_title="City Planner",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def official_auth_headers(official_user) -> dict:
    """Get authentication headers for official user."""
    token = create_access_token(data={"sub": official_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_with_password(db_session) -> db_models.User:
    """Create a test user with a known password for account deletion tests."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="deleteme@example.com",
        username="deletemeuser",
        display_name="Delete Me User",
        hashed_password=get_password_hash("TestPassword123!"),
        is_active=True,
        is_global_admin=False,
        consent_terms_accepted=True,
        consent_privacy_accepted=True,
        consent_terms_version="1.0",
        consent_privacy_version="1.0",
        consent_timestamp=now,
        marketing_consent=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_comment(db_session, test_user, test_idea) -> db_models.Comment:
    """Create a test comment."""
    comment = db_models.Comment(
        content="This is a test comment for the idea.",
        idea_id=test_idea.id,
        user_id=test_user.id,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


@pytest.fixture
def test_vote(db_session, test_user, test_idea) -> db_models.Vote:
    """Create a test vote."""
    vote = db_models.Vote(
        idea_id=test_idea.id,
        user_id=test_user.id,
        vote_type=db_models.VoteType.UPVOTE,
    )
    db_session.add(vote)
    db_session.commit()
    db_session.refresh(vote)
    return vote


@pytest.fixture
def test_user_vote(db_session, test_user_with_password, test_idea) -> db_models.Vote:
    """Create a vote for test_user_with_password."""
    vote = db_models.Vote(
        idea_id=test_idea.id,
        user_id=test_user_with_password.id,
        vote_type=db_models.VoteType.UPVOTE,
    )
    db_session.add(vote)
    db_session.commit()
    db_session.refresh(vote)
    return vote
