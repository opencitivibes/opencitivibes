"""
Integration tests for flags API endpoints.
"""

from repositories.db_models import Comment


class TestFlagsAPI:
    """Integration tests for /api/flags endpoints."""

    def test_create_flag_success(
        self, client, auth_headers, test_user, other_user, test_idea, db_session
    ):
        """Test POST /api/flags creates a flag."""
        # Create a comment by other_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=other_user.id,
            content="Comment by other user",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        response = client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
                "details": "This is spam content",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "comment"
        assert data["content_id"] == comment.id
        assert data["reason"] == "spam"
        assert data["status"] == "pending"

    def test_create_flag_unauthenticated(
        self, client, test_idea, db_session, test_user
    ):
        """Test POST /api/flags requires authentication."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        response = client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
            },
        )

        assert response.status_code == 401

    def test_create_flag_duplicate_fails(
        self, client, auth_headers, test_user, other_user, test_idea, db_session
    ):
        """Test duplicate flag returns 409."""
        # Create a comment by other_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=other_user.id,
            content="Comment to flag twice",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # First flag
        response1 = client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
            },
            headers=auth_headers,
        )
        assert response1.status_code == 200

        # Duplicate flag
        response2 = client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "harassment",
            },
            headers=auth_headers,
        )

        assert response2.status_code == 409

    def test_create_flag_own_content_fails(
        self, client, auth_headers, test_user, test_idea, db_session
    ):
        """Test flagging own content returns 400."""
        # Create a comment by test_user (who is making the request)
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="My own comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        response = client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_get_my_flags(
        self, client, auth_headers, test_user, other_user, test_idea, db_session
    ):
        """Test GET /api/flags/my-flags returns user's flags."""
        # Create a comment by other_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=other_user.id,
            content="Comment to flag",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create a flag
        client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
            },
            headers=auth_headers,
        )

        response = client.get(
            "/api/flags/my-flags",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["content_type"] == "comment"

    def test_retract_flag_success(
        self, client, auth_headers, test_user, other_user, test_idea, db_session
    ):
        """Test DELETE /api/flags/{flag_id} retracts a flag."""
        # Create a comment by other_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=other_user.id,
            content="Comment to flag and retract",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create flag
        create_response = client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
            },
            headers=auth_headers,
        )
        flag_id = create_response.json()["id"]

        # Retract flag
        response = client.delete(
            f"/api/flags/{flag_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "retracted" in response.json()["message"].lower()

    def test_retract_others_flag_fails(
        self,
        client,
        auth_headers,
        admin_auth_headers,
        test_user,
        other_user,
        test_idea,
        db_session,
    ):
        """Test DELETE /api/flags/{flag_id} fails for other's flag."""
        # Create a comment by test_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Comment flagged by other",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create a user to flag the comment (use admin since they're different)
        # Actually let's use another approach - create a flag directly
        from authentication.auth import create_access_token, get_password_hash
        from repositories.db_models import User

        flagger = User(
            email="flagger@example.com",
            username="flagger",
            display_name="Flagger User",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_global_admin=False,
        )
        db_session.add(flagger)
        db_session.commit()
        db_session.refresh(flagger)

        flagger_token = create_access_token(data={"sub": flagger.email})
        flagger_headers = {"Authorization": f"Bearer {flagger_token}"}

        # Flagger creates a flag
        create_response = client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
            },
            headers=flagger_headers,
        )
        flag_id = create_response.json()["id"]

        # test_user tries to retract flagger's flag
        response = client.delete(
            f"/api/flags/{flag_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_check_flag_status_not_flagged(
        self, client, auth_headers, test_user, other_user, test_idea, db_session
    ):
        """Test GET /api/flags/check/{type}/{id} returns flagged: false."""
        # Create a comment by other_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=other_user.id,
            content="Unflagged comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Check before flagging
        response = client.get(
            f"/api/flags/check/comment/{comment.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["flagged"] is False

    def test_check_flag_status_flagged(
        self, client, auth_headers, test_user, other_user, test_idea, db_session
    ):
        """Test GET /api/flags/check/{type}/{id} returns flagged: true."""
        # Create a comment by other_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=other_user.id,
            content="Comment to be flagged",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create flag
        client.post(
            "/api/flags",
            json={
                "content_type": "comment",
                "content_id": comment.id,
                "reason": "spam",
            },
            headers=auth_headers,
        )

        # Check after flagging
        response = client.get(
            f"/api/flags/check/comment/{comment.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["flagged"] is True

    def test_flag_on_idea(
        self, client, auth_headers, test_user, other_user, test_category, db_session
    ):
        """Test flagging an idea works correctly."""
        from repositories.db_models import Idea, IdeaStatus

        # Create an idea by other_user
        idea = Idea(
            title="Idea to Flag",
            description="Test idea description",
            category_id=test_category.id,
            user_id=other_user.id,
            status=IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.refresh(idea)

        response = client.post(
            "/api/flags",
            json={
                "content_type": "idea",
                "content_id": idea.id,
                "reason": "misinformation",
                "details": "Contains false information",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "idea"
        assert data["content_id"] == idea.id
        assert data["reason"] == "misinformation"
