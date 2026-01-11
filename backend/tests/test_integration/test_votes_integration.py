"""
Integration tests for votes router.

Tests the complete voting flow:
1. Upvote an idea
2. Downvote an idea
3. Toggle vote (remove then re-add)
4. Get vote status
5. Update vote qualities
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import repositories.db_models as db_models


@pytest.fixture
def other_user_idea(
    db_session: Session, other_user: db_models.User, test_category: db_models.Category
) -> db_models.Idea:
    """Create an idea by other_user so test_user can vote on it."""
    idea = db_models.Idea(
        title="Other User Idea",
        description="An idea created by another user for voting tests.",
        category_id=test_category.id,
        user_id=other_user.id,
        status=db_models.IdeaStatus.APPROVED,
    )
    db_session.add(idea)
    db_session.commit()
    db_session.refresh(idea)
    return idea


def test_vote_upvote(
    client: TestClient, other_user_idea: db_models.Idea, auth_headers: dict
):
    """Test upvoting an idea."""
    vote_data = {
        "vote_type": "upvote",
    }
    response = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vote_type"] == "upvote"
    assert data["idea_id"] == other_user_idea.id


def test_vote_downvote(
    client: TestClient, other_user_idea: db_models.Idea, auth_headers: dict
):
    """Test downvoting an idea."""
    vote_data = {
        "vote_type": "downvote",
    }
    response = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vote_type"] == "downvote"
    assert data["idea_id"] == other_user_idea.id


def test_vote_unauthorized(client: TestClient, test_idea: db_models.Idea):
    """Test voting without authentication fails."""
    vote_data = {
        "vote_type": "upvote",
    }
    response = client.post(f"/api/votes/{test_idea.id}", json=vote_data)
    assert response.status_code == 401


def test_vote_nonexistent_idea(client: TestClient, auth_headers: dict):
    """Test voting on non-existent idea fails."""
    vote_data = {
        "vote_type": "upvote",
    }
    response = client.post("/api/votes/99999", json=vote_data, headers=auth_headers)
    assert response.status_code == 404


def test_toggle_vote(
    client: TestClient, other_user_idea: db_models.Idea, auth_headers: dict
):
    """Test toggling vote from upvote to downvote."""
    # First upvote
    vote_data = {"vote_type": "upvote"}
    response = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response.status_code == 200

    # Then downvote (toggle)
    vote_data = {"vote_type": "downvote"}
    response = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vote_type"] == "downvote"


def test_remove_vote(
    client: TestClient, other_user_idea: db_models.Idea, auth_headers: dict
):
    """Test removing a vote."""
    # First vote
    vote_data = {"vote_type": "upvote"}
    response = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response.status_code == 200

    # Remove vote
    response = client.delete(f"/api/votes/{other_user_idea.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Vote removed successfully"


def test_get_my_vote(
    client: TestClient, other_user_idea: db_models.Idea, auth_headers: dict
):
    """Test getting current user's vote on an idea."""
    # First vote
    vote_data = {"vote_type": "upvote"}
    client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )

    # Get vote status
    response = client.get(
        f"/api/votes/{other_user_idea.id}/my-vote", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vote_type"] == "upvote"
    assert data["idea_id"] == other_user_idea.id


def test_get_my_vote_no_vote(
    client: TestClient, test_idea: db_models.Idea, auth_headers: dict
):
    """Test getting vote status when user hasn't voted."""
    response = client.get(f"/api/votes/{test_idea.id}/my-vote", headers=auth_headers)
    # Should return None/null
    assert response.status_code == 200
    assert response.json() is None


def test_vote_with_qualities(
    client: TestClient,
    other_user_idea: db_models.Idea,
    auth_headers: dict,
    test_quality: db_models.Quality,
):
    """Test upvoting with quality selections."""
    vote_data = {
        "vote_type": "upvote",
        "quality_keys": [test_quality.key],
    }
    response = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vote_type"] == "upvote"


def test_get_vote_qualities(
    client: TestClient,
    other_user_idea: db_models.Idea,
    auth_headers: dict,
    test_quality: db_models.Quality,
):
    """Test getting quality selections for a vote."""
    # First vote with qualities
    vote_data = {
        "vote_type": "upvote",
        "quality_keys": [test_quality.key],
    }
    client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )

    # Get qualities
    response = client.get(
        f"/api/votes/{other_user_idea.id}/qualities", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_update_vote_qualities(
    client: TestClient,
    other_user_idea: db_models.Idea,
    auth_headers: dict,
    test_quality: db_models.Quality,
):
    """Test updating quality selections for an existing vote."""
    # First vote
    vote_data = {"vote_type": "upvote"}
    client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )

    # Update qualities
    quality_data = {
        "quality_keys": [test_quality.key],
    }
    response = client.put(
        f"/api/votes/{other_user_idea.id}/qualities",
        json=quality_data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_vote_duplicate_same_type(
    client: TestClient, other_user_idea: db_models.Idea, auth_headers: dict
):
    """Test voting twice with same vote type (should be idempotent)."""
    vote_data = {"vote_type": "upvote"}

    # First vote
    response1 = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response1.status_code == 200

    # Second identical vote (should update, not fail)
    response2 = client.post(
        f"/api/votes/{other_user_idea.id}", json=vote_data, headers=auth_headers
    )
    assert response2.status_code == 200
    data = response2.json()
    assert data["vote_type"] == "upvote"
