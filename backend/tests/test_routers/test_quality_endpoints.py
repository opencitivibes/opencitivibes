"""
Unit tests for quality-related API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from authentication.auth import create_access_token
from repositories.db_models import (
    Category,
    Idea,
    Quality,
    User,
    Vote,
    VoteQuality,
    VoteType,
)


@pytest.fixture
def test_quality(db_session: Session) -> Quality:
    """Create a test quality."""
    quality = Quality(
        key="community_benefit",
        name_en="Benefits everyone",
        name_fr="Bénéficie à tous",
        icon="heart",
        color="rose",
        is_default=True,
        is_active=True,
        display_order=1,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


@pytest.fixture
def other_quality(db_session: Session) -> Quality:
    """Create another test quality."""
    quality = Quality(
        key="urgent",
        name_en="Addresses urgent problem",
        name_fr="Problème urgent",
        icon="alert-triangle",
        color="red",
        is_default=True,
        is_active=True,
        display_order=2,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


@pytest.fixture
def other_user_auth_headers(other_user: User) -> dict:
    """Get auth headers for other_user fixture."""
    token = create_access_token(data={"sub": other_user.email})
    return {"Authorization": f"Bearer {token}"}


class TestCategoryQualitiesEndpoint:
    """Tests for GET /categories/{id}/qualities."""

    def test_returns_qualities_for_category(
        self,
        client: TestClient,
        test_category: Category,
        test_quality: Quality,
    ):
        """Should return qualities for a category."""
        response = client.get(f"/api/categories/{test_category.id}/qualities")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["key"] == "community_benefit"
        assert data[0]["name_en"] == "Benefits everyone"
        assert data[0]["name_fr"] == "Bénéficie à tous"
        assert data[0]["icon"] == "heart"
        assert data[0]["color"] == "rose"

    def test_returns_404_for_nonexistent_category(self, client: TestClient):
        """Should return 404 for non-existent category."""
        response = client.get("/api/categories/9999/qualities")
        assert response.status_code == 404


class TestDefaultQualitiesEndpoint:
    """Tests for GET /categories/qualities/defaults."""

    def test_returns_default_qualities(
        self,
        client: TestClient,
        test_quality: Quality,
    ):
        """Should return default qualities."""
        response = client.get("/api/categories/qualities/defaults")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["key"] == "community_benefit"

    def test_returns_empty_when_no_defaults(self, client: TestClient):
        """Should return empty list when no default qualities exist."""
        response = client.get("/api/categories/qualities/defaults")

        assert response.status_code == 200
        assert response.json() == []


class TestVoteWithQualitiesEndpoint:
    """Tests for POST /votes/{idea_id} with qualities."""

    def test_vote_with_qualities(
        self,
        client: TestClient,
        test_idea: Idea,
        other_user_auth_headers: dict,
        test_quality: Quality,
    ):
        """Should create vote with qualities."""
        response = client.post(
            f"/api/votes/{test_idea.id}",
            json={"vote_type": "upvote", "quality_ids": [test_quality.id]},
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vote_type"] == "upvote"

    def test_vote_without_qualities(
        self,
        client: TestClient,
        test_idea: Idea,
        other_user_auth_headers: dict,
    ):
        """Should create vote without qualities."""
        response = client.post(
            f"/api/votes/{test_idea.id}",
            json={"vote_type": "upvote"},
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200

    def test_downvote_ignores_qualities(
        self,
        client: TestClient,
        test_idea: Idea,
        other_user_auth_headers: dict,
        test_quality: Quality,
    ):
        """Should ignore qualities for downvotes."""
        response = client.post(
            f"/api/votes/{test_idea.id}",
            json={"vote_type": "downvote", "quality_ids": [test_quality.id]},
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["vote_type"] == "downvote"


class TestGetVoteQualitiesEndpoint:
    """Tests for GET /votes/{idea_id}/qualities."""

    def test_returns_quality_ids(
        self,
        client: TestClient,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        other_user_auth_headers: dict,
        test_quality: Quality,
    ):
        """Should return quality IDs for user's vote."""
        # Create vote with quality
        vote = Vote(
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.flush()
        db_session.add(VoteQuality(vote_id=vote.id, quality_id=test_quality.id))
        db_session.commit()

        response = client.get(
            f"/api/votes/{test_idea.id}/qualities",
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200
        # API returns quality keys (strings), not IDs
        assert response.json() == [test_quality.key]

    def test_returns_empty_for_no_vote(
        self,
        client: TestClient,
        test_idea: Idea,
        other_user_auth_headers: dict,
    ):
        """Should return empty list when no vote exists."""
        response = client.get(
            f"/api/votes/{test_idea.id}/qualities",
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == []


class TestUpdateVoteQualitiesEndpoint:
    """Tests for PUT /votes/{idea_id}/qualities."""

    def test_updates_qualities(
        self,
        client: TestClient,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        other_user_auth_headers: dict,
        test_quality: Quality,
        other_quality: Quality,
    ):
        """Should update qualities for existing upvote."""
        # Create upvote
        vote = Vote(
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.commit()

        response = client.put(
            f"/api/votes/{test_idea.id}/qualities",
            json={"quality_keys": [test_quality.key, other_quality.key]},
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # API returns quality keys (strings), not IDs
        assert test_quality.key in data
        assert other_quality.key in data

    def test_returns_404_for_no_vote(
        self,
        client: TestClient,
        test_idea: Idea,
        other_user_auth_headers: dict,
        test_quality: Quality,
    ):
        """Should return 404 when no vote exists."""
        response = client.put(
            f"/api/votes/{test_idea.id}/qualities",
            json={"quality_keys": [test_quality.key]},
            headers=other_user_auth_headers,
        )

        assert response.status_code == 404


class TestGetMyVoteEndpoint:
    """Tests for GET /votes/{idea_id}/my-vote."""

    def test_returns_vote_with_qualities(
        self,
        client: TestClient,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        other_user_auth_headers: dict,
        test_quality: Quality,
    ):
        """Should return vote with qualities."""
        vote = Vote(
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.flush()
        db_session.add(VoteQuality(vote_id=vote.id, quality_id=test_quality.id))
        db_session.commit()

        response = client.get(
            f"/api/votes/{test_idea.id}/my-vote",
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vote_type"] == "upvote"
        # API returns quality keys (strings), not IDs
        assert data["qualities"] == [test_quality.key]

    def test_returns_null_for_no_vote(
        self,
        client: TestClient,
        test_idea: Idea,
        other_user_auth_headers: dict,
    ):
        """Should return null when no vote exists."""
        response = client.get(
            f"/api/votes/{test_idea.id}/my-vote",
            headers=other_user_auth_headers,
        )

        assert response.status_code == 200
        assert response.json() is None


class TestIdeaQualityCountsEndpoint:
    """Tests for GET /ideas/{idea_id}/quality-counts."""

    def test_returns_quality_counts(
        self,
        client: TestClient,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should return quality counts for idea."""
        vote = Vote(
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.flush()
        db_session.add(VoteQuality(vote_id=vote.id, quality_id=test_quality.id))
        db_session.commit()

        response = client.get(f"/api/ideas/{test_idea.id}/quality-counts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["counts"]) == 1
        assert data["counts"][0]["quality_id"] == test_quality.id
        assert data["counts"][0]["quality_key"] == "community_benefit"
        assert data["counts"][0]["count"] == 1
        assert data["total_votes_with_qualities"] == 1

    def test_returns_empty_for_no_quality_votes(
        self,
        client: TestClient,
        test_idea: Idea,
    ):
        """Should return empty counts for idea without quality votes."""
        response = client.get(f"/api/ideas/{test_idea.id}/quality-counts")

        assert response.status_code == 200
        data = response.json()
        assert data["counts"] == []
        assert data["total_votes_with_qualities"] == 0

    def test_returns_404_for_nonexistent_idea(self, client: TestClient):
        """Should return 404 for non-existent idea."""
        response = client.get("/api/ideas/9999/quality-counts")
        assert response.status_code == 404
