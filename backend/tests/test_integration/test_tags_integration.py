"""
Integration tests for tags router.

Tests the complete tag flow:
1. List all tags
2. Search tags
3. Get tag by ID
4. Get tag by name
5. Create tag (authenticated)
6. Get popular tags
"""

from fastapi.testclient import TestClient

import repositories.db_models as db_models


def test_get_all_tags(client: TestClient, test_tag: db_models.Tag):
    """Test getting all tags with pagination."""
    response = client.get("/api/tags/?skip=0&limit=100")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_search_tags(client: TestClient, test_tag: db_models.Tag):
    """Test searching tags by name."""
    response = client.get(f"/api/tags/search?q={test_tag.name[:4]}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_search_tags_no_query(client: TestClient):
    """Test search requires query parameter."""
    response = client.get("/api/tags/search")
    # Should fail validation
    assert response.status_code == 422


def test_get_tag_by_id(client: TestClient, test_tag: db_models.Tag):
    """Test getting a tag by ID."""
    response = client.get(f"/api/tags/{test_tag.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_tag.id
    assert data["name"] == test_tag.name
    assert data["display_name"] == test_tag.display_name


def test_get_tag_by_id_nonexistent(client: TestClient):
    """Test getting non-existent tag by ID fails."""
    response = client.get("/api/tags/99999")
    assert response.status_code == 404


def test_get_tag_by_name(client: TestClient, test_tag: db_models.Tag):
    """Test getting a tag by name."""
    response = client.get(f"/api/tags/by-name/{test_tag.name}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_tag.name
    assert data["display_name"] == test_tag.display_name


def test_get_tag_by_name_nonexistent(client: TestClient):
    """Test getting non-existent tag by name fails."""
    response = client.get("/api/tags/by-name/nonexistenttag")
    assert response.status_code == 404


def test_get_popular_tags(client: TestClient):
    """Test getting popular tags."""
    response = client.get("/api/tags/popular?limit=20")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_popular_tags_with_filters(client: TestClient):
    """Test getting popular tags with min_ideas filter."""
    response = client.get("/api/tags/popular?limit=10&min_ideas=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_tag(client: TestClient, auth_headers: dict):
    """Test creating a new tag (authenticated)."""
    tag_data = {
        "name": "newtesttag",
        "display_name": "New Test Tag",
    }
    response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Name is normalized to lowercase "new test tag" (from display_name)
    assert data["name"] == "new test tag"
    assert data["display_name"] == tag_data["display_name"]


def test_create_tag_unauthorized(client: TestClient):
    """Test creating tag without authentication fails."""
    tag_data = {
        "name": "unauthorizedtag",
        "display_name": "Unauthorized Tag",
    }
    response = client.post("/api/tags/", json=tag_data)
    assert response.status_code == 401


def test_create_duplicate_tag(
    client: TestClient, test_tag: db_models.Tag, auth_headers: dict
):
    """Test creating duplicate tag returns existing tag."""
    tag_data = {
        "name": test_tag.display_name,  # Use display_name to match the tag
        "display_name": test_tag.display_name,
    }
    response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
    # Should return the existing tag
    assert response.status_code == 200
    data = response.json()
    # Name is normalized to lowercase
    assert data["name"] == test_tag.name
    assert data["id"] == test_tag.id


def test_get_tag_statistics(client: TestClient, test_tag: db_models.Tag):
    """Test getting statistics for a tag."""
    response = client.get(f"/api/tags/{test_tag.id}/statistics")
    assert response.status_code == 200
    data = response.json()
    assert "total_ideas" in data
    assert "approved_ideas" in data


def test_get_ideas_by_tag(client: TestClient, test_tag: db_models.Tag):
    """Test getting idea IDs for a tag."""
    response = client.get(f"/api/tags/{test_tag.id}/ideas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_ideas_by_tag_full(client: TestClient, test_tag: db_models.Tag):
    """Test getting full ideas with scores for a tag."""
    response = client.get(f"/api/tags/{test_tag.id}/ideas/full")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_ideas_by_tag_pagination(client: TestClient, test_tag: db_models.Tag):
    """Test pagination for ideas by tag."""
    response = client.get(f"/api/tags/{test_tag.id}/ideas?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_tags_no_auth_required_for_read(client: TestClient):
    """Test tags can be read without authentication."""
    response = client.get("/api/tags/")
    assert response.status_code == 200

    response = client.get("/api/tags/popular")
    assert response.status_code == 200


def test_delete_tag_admin_only(
    client: TestClient, test_tag: db_models.Tag, admin_auth_headers: dict
):
    """Test deleting a tag (admin only)."""
    # First create a new tag to delete
    tag_data = {"name": "deletetest", "display_name": "Delete Test"}
    create_response = client.post(
        "/api/tags/", json=tag_data, headers=admin_auth_headers
    )
    assert create_response.status_code == 200
    tag_id = create_response.json()["id"]

    # Try to delete it
    response = client.delete(f"/api/tags/{tag_id}", headers=admin_auth_headers)
    assert response.status_code == 200


def test_delete_tag_unauthorized(
    client: TestClient, test_tag: db_models.Tag, auth_headers: dict
):
    """Test deleting tag as non-admin fails."""
    response = client.delete(f"/api/tags/{test_tag.id}", headers=auth_headers)
    assert response.status_code == 403
