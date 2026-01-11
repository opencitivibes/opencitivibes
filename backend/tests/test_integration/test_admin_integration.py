"""
Integration tests for admin router.

Tests admin functionality:
1. List pending ideas (admin only)
2. Approve/reject idea
3. Admin access control
4. Get all users (admin)
5. Manage admin roles
"""

from fastapi.testclient import TestClient

import repositories.db_models as db_models


def test_get_pending_ideas_admin(
    client: TestClient, pending_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test getting pending ideas as admin."""
    response = client.get("/api/admin/ideas/pending", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_get_pending_ideas_non_admin(
    client: TestClient, pending_idea: db_models.Idea, auth_headers: dict
):
    """Test getting pending ideas as non-admin fails."""
    response = client.get("/api/admin/ideas/pending", headers=auth_headers)
    assert response.status_code == 403


def test_get_pending_ideas_unauthorized(
    client: TestClient, pending_idea: db_models.Idea
):
    """Test getting pending ideas without auth fails."""
    response = client.get("/api/admin/ideas/pending")
    assert response.status_code == 401


def test_moderate_idea_approve(
    client: TestClient, pending_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test approving an idea as admin."""
    moderation_data = {"status": "approved", "admin_comment": "Looks good!"}
    response = client.put(
        f"/api/admin/ideas/{pending_idea.id}/moderate",
        json=moderation_data,
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"


def test_moderate_idea_reject(
    client: TestClient, pending_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test rejecting an idea as admin."""
    moderation_data = {
        "status": "rejected",
        "admin_comment": "Does not meet guidelines",
    }
    response = client.put(
        f"/api/admin/ideas/{pending_idea.id}/moderate",
        json=moderation_data,
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"


def test_moderate_idea_non_admin(
    client: TestClient, pending_idea: db_models.Idea, auth_headers: dict
):
    """Test moderating idea as non-admin fails."""
    moderation_data = {"status": "approved", "admin_comment": "Should fail"}
    response = client.put(
        f"/api/admin/ideas/{pending_idea.id}/moderate",
        json=moderation_data,
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_get_all_users_admin(
    client: TestClient, test_user: db_models.User, admin_auth_headers: dict
):
    """Test getting all users as admin."""
    response = client.get(
        "/api/admin/users?page=1&page_size=20", headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert isinstance(data["users"], list)


def test_get_all_users_non_admin(client: TestClient, auth_headers: dict):
    """Test getting all users as non-admin fails."""
    response = client.get("/api/admin/users", headers=auth_headers)
    assert response.status_code == 403


def test_get_user_by_id_admin(
    client: TestClient, test_user: db_models.User, admin_auth_headers: dict
):
    """Test getting user details as admin."""
    response = client.get(
        f"/api/admin/users/{test_user.id}", headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id


def test_update_user_admin(
    client: TestClient, test_user: db_models.User, admin_auth_headers: dict
):
    """Test updating user as admin."""
    update_data = {
        "is_active": True,
    }
    response = client.put(
        f"/api/admin/users/{test_user.id}", json=update_data, headers=admin_auth_headers
    )
    assert response.status_code == 200


def test_get_approved_ideas_admin(
    client: TestClient, test_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test getting approved ideas as admin."""
    response = client.get("/api/admin/ideas/approved", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_all_comments_admin(
    client: TestClient, test_comment: db_models.Comment, admin_auth_headers: dict
):
    """Test getting all comments as admin."""
    response = client.get("/api/admin/comments/all", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_moderate_comment_admin(
    client: TestClient, test_comment: db_models.Comment, admin_auth_headers: dict
):
    """Test moderating a comment as admin."""
    moderation_data = {
        "is_moderated": True,
    }
    response = client.put(
        f"/api/admin/comments/{test_comment.id}/moderate",
        json=moderation_data,
        headers=admin_auth_headers,
    )
    assert response.status_code == 200


def test_get_admin_roles(client: TestClient, admin_auth_headers: dict):
    """Test getting all admin roles."""
    response = client.get("/api/admin/roles", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_admin_role(
    client: TestClient,
    test_user: db_models.User,
    test_category: db_models.Category,
    admin_auth_headers: dict,
):
    """Test creating admin role."""
    role_data = {
        "user_id": test_user.id,
        "category_id": test_category.id,
    }
    response = client.post(
        "/api/admin/roles", json=role_data, headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user.id


def test_get_categories_admin(
    client: TestClient, test_category: db_models.Category, admin_auth_headers: dict
):
    """Test getting categories with statistics as admin."""
    response = client.get("/api/admin/categories", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_category_admin(client: TestClient, admin_auth_headers: dict):
    """Test creating category as admin."""
    category_data = {
        "name_en": "New Category",
        "name_fr": "Nouvelle Catégorie",
        "description_en": "A new test category",
        "description_fr": "Une nouvelle catégorie de test",
    }
    response = client.post(
        "/api/admin/categories", json=category_data, headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name_en"] == category_data["name_en"]


def test_admin_delete_idea(
    client: TestClient, test_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test admin deleting an idea."""
    delete_data = {"reason": "Admin deletion for testing"}
    response = client.request(
        "DELETE",
        f"/api/admin/ideas/{test_idea.id}",
        json=delete_data,
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Idea deleted by admin"


def test_get_deleted_ideas(
    client: TestClient, deleted_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test getting deleted ideas list."""
    response = client.get("/api/admin/ideas/deleted", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_restore_idea(
    client: TestClient, deleted_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test restoring a deleted idea."""
    response = client.post(
        f"/api/admin/ideas/{deleted_idea.id}/restore", headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Idea restored successfully"


def test_get_rejected_ideas(
    client: TestClient, rejected_idea: db_models.Idea, admin_auth_headers: dict
):
    """Test getting rejected ideas list."""
    response = client.get("/api/admin/ideas/rejected", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_admin_endpoints_require_admin_role(client: TestClient, auth_headers: dict):
    """Test that various admin endpoints require admin role."""
    # List of admin-only endpoints
    endpoints = [
        "/api/admin/ideas/pending",
        "/api/admin/users",
        "/api/admin/roles",
        "/api/admin/categories",
        "/api/admin/comments/all",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint, headers=auth_headers)
        assert response.status_code == 403, f"Endpoint {endpoint} should require admin"
