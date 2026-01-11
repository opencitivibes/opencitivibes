"""
Integration tests for comments router.

Tests the complete comment flow:
1. Add comment to idea
2. List comments for idea
3. Delete comment (owner only)
4. Like/unlike comments
5. Comment sorting
"""

from fastapi.testclient import TestClient

import repositories.db_models as db_models


def test_create_comment(
    client: TestClient, test_idea: db_models.Idea, auth_headers: dict
):
    """Test creating a comment on an idea."""
    comment_data = {
        "content": "This is a test comment on the idea.",
        "language": "en",
    }
    response = client.post(
        f"/api/comments/{test_idea.id}", json=comment_data, headers=auth_headers
    )
    # Could be 200 or 202 depending on approval requirements
    assert response.status_code in [200, 202]
    if response.status_code == 200:
        data = response.json()
        assert data["content"] == comment_data["content"]
        assert data["idea_id"] == test_idea.id


def test_create_comment_unauthorized(client: TestClient, test_idea: db_models.Idea):
    """Test creating comment without authentication fails."""
    comment_data = {
        "content": "This should fail due to no authentication.",
        "language": "en",
    }
    response = client.post(f"/api/comments/{test_idea.id}", json=comment_data)
    assert response.status_code == 401


def test_create_comment_nonexistent_idea(client: TestClient, auth_headers: dict):
    """Test creating comment on non-existent idea fails."""
    comment_data = {
        "content": "Comment on non-existent idea.",
        "language": "en",
    }
    response = client.post(
        "/api/comments/99999", json=comment_data, headers=auth_headers
    )
    assert response.status_code == 404


def test_get_comments_for_idea(
    client: TestClient, test_idea: db_models.Idea, test_comment: db_models.Comment
):
    """Test getting comments for an idea."""
    response = client.get(f"/api/comments/{test_idea.id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should contain the test comment
    comment_ids = [comment["id"] for comment in data]
    assert test_comment.id in comment_ids


def test_get_comments_with_pagination(client: TestClient, test_idea: db_models.Idea):
    """Test getting comments with pagination."""
    response = client.get(f"/api/comments/{test_idea.id}?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_get_comments_with_sorting(client: TestClient, test_idea: db_models.Idea):
    """Test getting comments with different sort orders."""
    # Test relevance sort
    response = client.get(f"/api/comments/{test_idea.id}?sort_by=relevance")
    assert response.status_code == 200

    # Test newest sort
    response = client.get(f"/api/comments/{test_idea.id}?sort_by=newest")
    assert response.status_code == 200

    # Test oldest sort
    response = client.get(f"/api/comments/{test_idea.id}?sort_by=oldest")
    assert response.status_code == 200


def test_delete_comment_owner(
    client: TestClient, test_comment: db_models.Comment, auth_headers: dict
):
    """Test deleting own comment."""
    response = client.delete(f"/api/comments/{test_comment.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Comment deleted successfully"


def test_delete_comment_not_owner(
    client: TestClient, test_comment: db_models.Comment, other_user: db_models.User
):
    """Test deleting comment by non-owner fails."""
    from authentication.auth import create_access_token

    other_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': other_user.email})}"
    }
    response = client.delete(f"/api/comments/{test_comment.id}", headers=other_headers)
    assert response.status_code == 403


def test_delete_comment_unauthorized(
    client: TestClient, test_comment: db_models.Comment
):
    """Test deleting comment without authentication fails."""
    response = client.delete(f"/api/comments/{test_comment.id}")
    assert response.status_code == 401


def test_toggle_comment_like(
    client: TestClient, test_comment: db_models.Comment, other_user: db_models.User
):
    """Test liking a comment."""
    from authentication.auth import create_access_token

    # Use other_user to like the test_comment (which was created by test_user)
    other_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': other_user.email})}"
    }
    response = client.post(
        f"/api/comments/{test_comment.id}/like", headers=other_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "liked" in data
    assert "like_count" in data


def test_toggle_comment_like_twice(
    client: TestClient, test_comment: db_models.Comment, other_user: db_models.User
):
    """Test liking and then unliking a comment."""
    from authentication.auth import create_access_token

    # Use other_user to like the test_comment (which was created by test_user)
    other_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': other_user.email})}"
    }
    # First like
    response1 = client.post(
        f"/api/comments/{test_comment.id}/like", headers=other_headers
    )
    assert response1.status_code == 200
    data1 = response1.json()
    liked_first = data1["liked"]

    # Second like (toggle)
    response2 = client.post(
        f"/api/comments/{test_comment.id}/like", headers=other_headers
    )
    assert response2.status_code == 200
    data2 = response2.json()
    # Should toggle
    assert data2["liked"] != liked_first


def test_comment_like_unauthorized(client: TestClient, test_comment: db_models.Comment):
    """Test liking comment without authentication fails."""
    response = client.post(f"/api/comments/{test_comment.id}/like")
    assert response.status_code == 401


def test_comment_like_nonexistent(client: TestClient, auth_headers: dict):
    """Test liking non-existent comment fails."""
    response = client.post("/api/comments/99999/like", headers=auth_headers)
    assert response.status_code == 404


def test_create_multiple_comments(
    client: TestClient,
    test_idea: db_models.Idea,
    auth_headers: dict,
    test_comment: db_models.Comment,
):
    """Test creating multiple comments on the same idea."""
    created_count = 0
    for i in range(3):
        comment_data = {
            "content": f"This is test comment number {i + 1}.",
            "language": "en",
        }
        response = client.post(
            f"/api/comments/{test_idea.id}", json=comment_data, headers=auth_headers
        )
        assert response.status_code in [200, 202]
        # Track only comments that were approved (status 200)
        if response.status_code == 200:
            created_count += 1

    # Verify comments are retrievable
    response = client.get(f"/api/comments/{test_idea.id}")
    assert response.status_code == 200
    data = response.json()
    # Should have test_comment (if not moderated) plus any approved new ones
    # Comments with 202 status require approval and won't show up
    assert len(data) >= 1  # At least test_comment should be visible


def test_get_comments_with_user_context(
    client: TestClient,
    test_idea: db_models.Idea,
    test_comment: db_models.Comment,
    auth_headers: dict,
):
    """Test getting comments with authenticated user context."""
    response = client.get(f"/api/comments/{test_idea.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # When authenticated, should include user_has_liked field
    if len(data) > 0:
        assert "user_has_liked" in data[0]
