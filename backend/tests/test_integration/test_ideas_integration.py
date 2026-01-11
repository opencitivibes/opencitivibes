"""
Integration tests for ideas router.

Tests the complete idea lifecycle:
1. Create idea (authenticated)
2. Get idea by ID
3. List ideas (leaderboard)
4. Update idea (owner only)
5. Delete idea (soft delete)
6. Get my ideas
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import repositories.db_models as db_models


def test_create_idea(
    client: TestClient, auth_headers: dict, test_category: db_models.Category
):
    """Test creating a new idea with valid data."""
    idea_data = {
        "title": "New Test Idea",
        "description": "This is a detailed description of my new test idea that meets minimum length requirements.",
        "category_id": test_category.id,
        "tags": ["test", "integration"],
    }
    response = client.post(
        "/api/ideas/", json=idea_data, headers=auth_headers, params={"language": "en"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == idea_data["title"]
    assert data["description"] == idea_data["description"]
    assert data["category_id"] == idea_data["category_id"]
    assert data["status"] == "pending"


def test_create_idea_unauthorized(
    client: TestClient, test_category: db_models.Category
):
    """Test creating idea without authentication fails."""
    idea_data = {
        "title": "Unauthorized Idea",
        "description": "This should fail because no authentication is provided.",
        "category_id": test_category.id,
    }
    response = client.post("/api/ideas/", json=idea_data)
    assert response.status_code == 401


def test_create_idea_invalid_category(client: TestClient, auth_headers: dict):
    """Test creating idea with invalid category fails."""
    idea_data = {
        "title": "Invalid Category Idea",
        "description": "This idea has an invalid category ID.",
        "category_id": 99999,
    }
    response = client.post("/api/ideas/", json=idea_data, headers=auth_headers)
    assert response.status_code == 404


def test_get_idea_by_id(client: TestClient, test_idea: db_models.Idea):
    """Test getting a single idea by ID."""
    response = client.get(f"/api/ideas/{test_idea.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_idea.id
    assert data["title"] == test_idea.title
    assert data["description"] == test_idea.description
    assert "upvotes" in data
    assert "downvotes" in data


def test_get_idea_not_found(client: TestClient):
    """Test getting non-existent idea returns 404."""
    response = client.get("/api/ideas/99999")
    assert response.status_code == 404


def test_get_leaderboard(client: TestClient, test_idea: db_models.Idea):
    """Test getting ideas leaderboard."""
    response = client.get("/api/ideas/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should contain approved ideas
    idea_ids = [idea["id"] for idea in data]
    assert test_idea.id in idea_ids


def test_get_leaderboard_by_category(
    client: TestClient, test_idea: db_models.Idea, test_category: db_models.Category
):
    """Test getting leaderboard filtered by category."""
    response = client.get(f"/api/ideas/leaderboard?category_id={test_category.id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # All ideas should be from the specified category
    for idea in data:
        assert idea["category_id"] == test_category.id


def test_get_leaderboard_pagination(client: TestClient, test_idea: db_models.Idea):
    """Test leaderboard pagination."""
    response = client.get("/api/ideas/leaderboard?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_update_idea_owner(
    client: TestClient,
    test_idea: db_models.Idea,
    auth_headers: dict,
    db_session: Session,
):
    """Test updating idea as the owner."""
    # First, make the idea pending or rejected so it can be edited
    test_idea.status = db_models.IdeaStatus.PENDING
    db_session.commit()

    update_data = {
        "title": "Updated Idea Title",
        "description": "This is an updated description for the idea with enough length.",
    }
    response = client.put(
        f"/api/ideas/{test_idea.id}", json=update_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]


def test_update_idea_not_owner(
    client: TestClient, test_idea: db_models.Idea, other_user: db_models.User
):
    """Test updating idea by non-owner fails."""
    from authentication.auth import create_access_token

    other_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': other_user.email})}"
    }
    update_data = {
        "title": "Unauthorized Update",
        "description": "This should fail because user is not the owner.",
    }
    response = client.put(
        f"/api/ideas/{test_idea.id}", json=update_data, headers=other_headers
    )
    assert response.status_code == 403


def test_get_my_ideas(
    client: TestClient,
    test_user: db_models.User,
    auth_headers: dict,
    test_idea: db_models.Idea,
):
    """Test getting current user's ideas."""
    response = client.get("/api/ideas/my-ideas", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should contain the test idea
    idea_ids = [idea["id"] for idea in data]
    assert test_idea.id in idea_ids


def test_get_my_ideas_unauthorized(client: TestClient):
    """Test getting my ideas without authentication fails."""
    response = client.get("/api/ideas/my-ideas")
    assert response.status_code == 401


def test_delete_idea_owner(
    client: TestClient, test_idea: db_models.Idea, auth_headers: dict
):
    """Test deleting idea as the owner (soft delete)."""
    delete_data = {"reason": "No longer relevant"}
    response = client.request(
        "DELETE",
        f"/api/ideas/{test_idea.id}",
        json=delete_data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Idea deleted successfully"
    assert data["idea_id"] == test_idea.id


def test_delete_idea_not_owner(
    client: TestClient, test_idea: db_models.Idea, other_user: db_models.User
):
    """Test deleting idea by non-owner fails."""
    from authentication.auth import create_access_token

    other_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': other_user.email})}"
    }
    response = client.delete(f"/api/ideas/{test_idea.id}", headers=other_headers)
    assert response.status_code == 403


def test_check_similar_ideas(
    client: TestClient, test_category: db_models.Category, test_idea: db_models.Idea
):
    """Test checking for similar ideas."""
    similar_data = {
        "title": "Test Idea Similar",
        "description": "This is a test idea description",
        "category_id": test_category.id,
    }
    response = client.post(
        "/api/ideas/check-similar", json=similar_data, params={"language": "en"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_idea_quality_counts(client: TestClient, test_idea: db_models.Idea):
    """Test getting quality counts for an idea."""
    response = client.get(f"/api/ideas/{test_idea.id}/quality-counts")
    assert response.status_code == 200
    data = response.json()
    assert "total_votes_with_qualities" in data


def test_get_idea_quality_signals(client: TestClient, test_idea: db_models.Idea):
    """Test getting quality signals for an idea."""
    response = client.get(f"/api/ideas/{test_idea.id}/quality-signals")
    assert response.status_code == 200
    data = response.json()
    assert "total_upvotes" in data
    assert "trust_distribution" in data
