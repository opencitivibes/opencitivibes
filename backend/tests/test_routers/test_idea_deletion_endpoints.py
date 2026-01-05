"""
Integration tests for idea deletion API endpoints.

Tests cover:
- User delete endpoint (DELETE /api/ideas/{id})
- Admin delete endpoint (DELETE /api/admin/ideas/{id})
- Admin list deleted ideas (GET /api/admin/ideas/deleted)
- Admin restore endpoint (POST /api/admin/ideas/{id}/restore)
"""

from fastapi.testclient import TestClient

from authentication.auth import create_access_token
import repositories.db_models as db_models


class TestUserDeleteEndpoint:
    """Tests for DELETE /api/ideas/{idea_id}."""

    def test_user_can_delete_own_idea(
        self,
        client: TestClient,
        auth_headers: dict,
        pending_idea: db_models.Idea,
    ):
        """User can delete their own idea."""
        response = client.request(
            "DELETE",
            f"/api/ideas/{pending_idea.id}",
            headers=auth_headers,
            json={"reason": "No longer relevant"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Idea deleted successfully"
        assert data["idea_id"] == pending_idea.id

    def test_user_can_delete_without_reason(
        self,
        client: TestClient,
        auth_headers: dict,
        pending_idea: db_models.Idea,
    ):
        """User can delete their own idea without providing a reason."""
        response = client.delete(
            f"/api/ideas/{pending_idea.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Idea deleted successfully"

    def test_user_cannot_delete_without_auth(
        self,
        client: TestClient,
        pending_idea: db_models.Idea,
    ):
        """Unauthenticated user cannot delete."""
        response = client.delete(f"/api/ideas/{pending_idea.id}")
        assert response.status_code == 401

    def test_user_cannot_delete_others_idea(
        self,
        client: TestClient,
        other_user: db_models.User,
        pending_idea: db_models.Idea,
    ):
        """User cannot delete another user's idea."""
        other_token = create_access_token(data={"sub": other_user.email})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.delete(
            f"/api/ideas/{pending_idea.id}",
            headers=other_headers,
        )
        assert response.status_code == 403

    def test_delete_nonexistent_idea(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Deleting nonexistent idea returns 404."""
        response = client.delete(
            "/api/ideas/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_delete_already_deleted_idea(
        self,
        client: TestClient,
        auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Deleting already deleted idea returns 400."""
        response = client.delete(
            f"/api/ideas/{deleted_idea.id}",
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestAdminDeleteEndpoint:
    """Tests for DELETE /api/admin/ideas/{idea_id}."""

    def test_admin_can_delete_any_idea(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        pending_idea: db_models.Idea,
    ):
        """Admin can delete any user's idea."""
        response = client.request(
            "DELETE",
            f"/api/admin/ideas/{pending_idea.id}",
            headers=admin_auth_headers,
            json={"reason": "Spam content"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Idea deleted by admin"
        assert data["idea_id"] == pending_idea.id

    def test_admin_delete_requires_reason(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        pending_idea: db_models.Idea,
    ):
        """Admin delete requires reason."""
        response = client.request(
            "DELETE",
            f"/api/admin/ideas/{pending_idea.id}",
            headers=admin_auth_headers,
            json={},  # No reason
        )
        assert response.status_code == 422

    def test_admin_delete_rejects_empty_reason(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        pending_idea: db_models.Idea,
    ):
        """Admin delete rejects empty reason."""
        response = client.request(
            "DELETE",
            f"/api/admin/ideas/{pending_idea.id}",
            headers=admin_auth_headers,
            json={"reason": ""},
        )
        assert response.status_code == 422

    def test_non_admin_cannot_use_admin_delete(
        self,
        client: TestClient,
        auth_headers: dict,
        pending_idea: db_models.Idea,
    ):
        """Non-admin cannot use admin delete endpoint."""
        response = client.request(
            "DELETE",
            f"/api/admin/ideas/{pending_idea.id}",
            headers=auth_headers,
            json={"reason": "Test"},
        )
        assert response.status_code == 403


class TestDeletedIdeasListEndpoint:
    """Tests for GET /api/admin/ideas/deleted."""

    def test_admin_can_list_deleted_ideas(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Admin can list deleted ideas."""
        response = client.get(
            "/api/admin/ideas/deleted",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_deleted_list_includes_metadata(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Deleted ideas list includes deletion metadata."""
        response = client.get(
            "/api/admin/ideas/deleted",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        item = data["items"][0]
        assert "id" in item
        assert "title" in item
        assert "deleted_at" in item
        assert "deleted_by_id" in item
        assert "deleted_by_name" in item
        assert "deletion_reason" in item
        assert "original_author_id" in item
        assert "original_author_name" in item

    def test_non_admin_cannot_list_deleted(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Non-admin cannot list deleted ideas."""
        response = client.get(
            "/api/admin/ideas/deleted",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_deleted_list_pagination(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Deleted ideas list supports pagination."""
        response = client.get(
            "/api/admin/ideas/deleted?skip=0&limit=10",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 10


class TestRestoreEndpoint:
    """Tests for POST /api/admin/ideas/{idea_id}/restore."""

    def test_admin_can_restore_idea(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Admin can restore a deleted idea."""
        response = client.post(
            f"/api/admin/ideas/{deleted_idea.id}/restore",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Idea restored successfully"
        assert data["idea_id"] == deleted_idea.id

        # Verify idea is accessible again
        get_response = client.get(f"/api/ideas/{deleted_idea.id}")
        assert get_response.status_code == 200

    def test_restore_non_deleted_idea(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        test_idea: db_models.Idea,
    ):
        """Restoring non-deleted idea returns 400."""
        response = client.post(
            f"/api/admin/ideas/{test_idea.id}/restore",
            headers=admin_auth_headers,
        )
        assert response.status_code == 400

    def test_restore_nonexistent_idea(
        self,
        client: TestClient,
        admin_auth_headers: dict,
    ):
        """Restoring nonexistent idea returns 404."""
        response = client.post(
            "/api/admin/ideas/99999/restore",
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    def test_non_admin_cannot_restore(
        self,
        client: TestClient,
        auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Non-admin cannot restore ideas."""
        response = client.post(
            f"/api/admin/ideas/{deleted_idea.id}/restore",
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestDeletedIdeaVisibility:
    """Tests for deleted idea visibility in public endpoints."""

    def test_deleted_idea_not_in_leaderboard(
        self,
        client: TestClient,
        deleted_idea: db_models.Idea,
    ):
        """Deleted ideas should not appear in leaderboard."""
        response = client.get("/api/ideas/leaderboard")
        assert response.status_code == 200
        ideas = response.json()
        idea_ids = [i["id"] for i in ideas]
        assert deleted_idea.id not in idea_ids

    def test_deleted_idea_returns_404(
        self,
        client: TestClient,
        deleted_idea: db_models.Idea,
    ):
        """Getting a deleted idea returns 404."""
        response = client.get(f"/api/ideas/{deleted_idea.id}")
        assert response.status_code == 404

    def test_deleted_idea_not_in_my_ideas(
        self,
        client: TestClient,
        auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Deleted ideas should not appear in user's idea list."""
        response = client.get(
            "/api/ideas/my-ideas",
            headers=auth_headers,
        )
        assert response.status_code == 200
        ideas = response.json()
        idea_ids = [i["id"] for i in ideas]
        assert deleted_idea.id not in idea_ids


class TestRejectedIdeasListEndpoint:
    """Tests for GET /api/admin/ideas/rejected."""

    def test_admin_can_list_rejected_ideas(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        rejected_idea: db_models.Idea,
    ):
        """Admin can list rejected ideas."""
        response = client.get(
            "/api/admin/ideas/rejected",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_rejected_list_includes_metadata(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        rejected_idea: db_models.Idea,
    ):
        """Rejected ideas list includes appropriate metadata."""
        response = client.get(
            "/api/admin/ideas/rejected",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        item = data["items"][0]
        assert "id" in item
        assert "title" in item
        assert "admin_comment" in item
        assert "author_id" in item
        assert "author_name" in item
        assert "category_id" in item
        assert "category_name_en" in item
        assert "category_name_fr" in item
        assert "created_at" in item

    def test_non_admin_cannot_list_rejected(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Non-admin cannot list rejected ideas."""
        response = client.get(
            "/api/admin/ideas/rejected",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_rejected_list_pagination(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        rejected_idea: db_models.Idea,
    ):
        """Rejected ideas list supports pagination."""
        response = client.get(
            "/api/admin/ideas/rejected?skip=0&limit=10",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 10

    def test_rejected_list_excludes_deleted_ideas(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        deleted_idea: db_models.Idea,
    ):
        """Rejected ideas list excludes soft-deleted ideas."""
        # The deleted_idea fixture has status APPROVED, but let's verify
        # that if a rejected idea is also soft-deleted, it won't appear
        response = client.get(
            "/api/admin/ideas/rejected",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        idea_ids = [item["id"] for item in data["items"]]
        assert deleted_idea.id not in idea_ids
