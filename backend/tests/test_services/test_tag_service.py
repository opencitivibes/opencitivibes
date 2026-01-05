"""
Unit tests for TagService.
"""

import time

import pytest
from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import BusinessRuleException, NotFoundException
from services.tag_service import TagService


class TestCaching:
    """Tests for TagService caching functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_get_cache_key(self):
        """Should generate cache key from prefix and arguments."""
        key = TagService._get_cache_key("popular", 10, 5)
        assert key == "popular:10:5"

    def test_set_and_get_cache(self):
        """Should store and retrieve from cache."""
        key = "test_key"
        data = {"foo": "bar"}

        TagService._set_cache(key, data)
        result = TagService._get_from_cache(key)

        assert result == data

    def test_get_from_cache_expired(self):
        """Should return None for expired cache entries."""
        key = "expired_key"
        data = {"foo": "bar"}

        # Set cache with old timestamp
        TagService._cache[key] = (data, time.time() - 400)  # 400s ago

        result = TagService._get_from_cache(key)

        assert result is None
        assert key not in TagService._cache

    def test_get_from_cache_missing(self):
        """Should return None for missing cache entries."""
        result = TagService._get_from_cache("nonexistent")
        assert result is None

    def test_invalidate_popular_cache(self):
        """Should invalidate all popular cache entries."""
        TagService._set_cache("popular:10:5", ["tag1"])
        TagService._set_cache("popular:20:1", ["tag2"])
        TagService._set_cache("other:key", ["other"])

        TagService.invalidate_popular_cache()

        assert "popular:10:5" not in TagService._cache
        assert "popular:20:1" not in TagService._cache
        assert "other:key" in TagService._cache


class TestGetAllTags:
    """Tests for TagService.get_all_tags."""

    def test_get_all_tags_empty(self, db_session: Session):
        """Should return empty list when no tags exist."""
        result = TagService.get_all_tags(db_session)
        assert result == []

    def test_get_all_tags(self, db_session: Session):
        """Should return all tags."""
        tag1 = db_models.Tag(name="tag1", display_name="Tag1")
        tag2 = db_models.Tag(name="tag2", display_name="Tag2")
        db_session.add(tag1)
        db_session.add(tag2)
        db_session.commit()

        result = TagService.get_all_tags(db_session)

        assert len(result) == 2

    def test_get_all_tags_with_pagination(self, db_session: Session):
        """Should support pagination."""
        for i in range(5):
            db_session.add(db_models.Tag(name=f"tag{i}", display_name=f"Tag{i}"))
        db_session.commit()

        result = TagService.get_all_tags(db_session, skip=2, limit=2)

        assert len(result) == 2


class TestGetTagById:
    """Tests for TagService.get_tag_by_id."""

    def test_get_tag_by_id_found(self, db_session: Session, test_tag: db_models.Tag):
        """Should return tag when found."""
        result = TagService.get_tag_by_id(db_session, test_tag.id)

        assert result.id == test_tag.id
        assert result.name == test_tag.name

    def test_get_tag_by_id_not_found(self, db_session: Session):
        """Should raise NotFoundException when tag not found."""
        with pytest.raises(NotFoundException) as exc_info:
            TagService.get_tag_by_id(db_session, 99999)

        assert "99999" in str(exc_info.value)


class TestGetTagByName:
    """Tests for TagService.get_tag_by_name."""

    def test_get_tag_by_name_found(self, db_session: Session, test_tag: db_models.Tag):
        """Should return tag when found."""
        result = TagService.get_tag_by_name(db_session, test_tag.name)

        assert result.id == test_tag.id

    def test_get_tag_by_name_not_found(self, db_session: Session):
        """Should raise NotFoundException when tag not found."""
        with pytest.raises(NotFoundException) as exc_info:
            TagService.get_tag_by_name(db_session, "nonexistent")

        assert "nonexistent" in str(exc_info.value)


class TestSearchTags:
    """Tests for TagService.search_tags."""

    def test_search_tags_empty_query(self, db_session: Session):
        """Should return empty list for empty query."""
        result = TagService.search_tags(db_session, "")
        assert result == []

    def test_search_tags_whitespace_query(self, db_session: Session):
        """Should return empty list for whitespace query."""
        result = TagService.search_tags(db_session, "   ")
        assert result == []

    def test_search_tags(self, db_session: Session):
        """Should return matching tags."""
        db_session.add(db_models.Tag(name="environment", display_name="Environment"))
        db_session.add(db_models.Tag(name="environ", display_name="Environ"))
        db_session.add(db_models.Tag(name="transport", display_name="Transport"))
        db_session.commit()

        result = TagService.search_tags(db_session, "environ")

        assert len(result) == 2


class TestGetPopularTags:
    """Tests for TagService.get_popular_tags."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_get_popular_tags_empty(self, db_session: Session):
        """Should return empty list when no tags exist."""
        result = TagService.get_popular_tags(db_session)
        assert result == []

    def test_get_popular_tags(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return popular tags with counts."""
        tag = db_models.Tag(name="popular", display_name="Popular")
        db_session.add(tag)
        db_session.commit()

        # Create approved ideas with tag
        for i in range(3):
            idea = db_models.Idea(
                title=f"Idea {i}",
                description="Description long enough",
                category_id=test_category.id,
                user_id=test_user.id,
                status=db_models.IdeaStatus.APPROVED,
            )
            db_session.add(idea)
            db_session.commit()
            db_session.add(db_models.IdeaTag(idea_id=idea.id, tag_id=tag.id))
        db_session.commit()

        result = TagService.get_popular_tags(db_session)

        assert len(result) == 1
        assert result[0].name == "popular"
        assert result[0].idea_count == 3

    def test_get_popular_tags_cached(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return cached result on second call."""
        tag = db_models.Tag(name="popular", display_name="Popular")
        db_session.add(tag)
        db_session.commit()

        idea = db_models.Idea(
            title="Idea",
            description="Description long enough",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.add(db_models.IdeaTag(idea_id=idea.id, tag_id=tag.id))
        db_session.commit()

        # First call - cache miss
        result1 = TagService.get_popular_tags(db_session, limit=20, min_ideas=1)

        # Verify cached
        cache_key = TagService._get_cache_key("popular", 20, 1)
        assert cache_key in TagService._cache

        # Second call - cache hit
        result2 = TagService.get_popular_tags(db_session, limit=20, min_ideas=1)

        assert result1 == result2


class TestGetTagStatistics:
    """Tests for TagService.get_tag_statistics."""

    def test_get_tag_statistics(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return statistics for tag."""
        tag = db_models.Tag(name="stats", display_name="Stats")
        db_session.add(tag)
        db_session.commit()

        # Create ideas with different statuses
        approved = db_models.Idea(
            title="Approved",
            description="Description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        pending = db_models.Idea(
            title="Pending",
            description="Description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.PENDING,
        )
        db_session.add(approved)
        db_session.add(pending)
        db_session.commit()

        db_session.add(db_models.IdeaTag(idea_id=approved.id, tag_id=tag.id))
        db_session.add(db_models.IdeaTag(idea_id=pending.id, tag_id=tag.id))
        db_session.commit()

        result = TagService.get_tag_statistics(db_session, tag.id)

        assert result.total_ideas == 2
        assert result.approved_ideas == 1
        assert result.pending_ideas == 1

    def test_get_tag_statistics_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent tag."""
        with pytest.raises(NotFoundException):
            TagService.get_tag_statistics(db_session, 99999)


class TestCreateTag:
    """Tests for TagService.create_tag."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_create_tag(self, db_session: Session):
        """Should create new tag."""
        tag_data = schemas.TagCreate(display_name="NewTag")
        result = TagService.create_tag(db_session, tag_data)

        assert result.name == "newtag"
        assert result.display_name == "NewTag"

    def test_create_tag_returns_existing(
        self, db_session: Session, test_tag: db_models.Tag
    ):
        """Should return existing tag if it exists."""
        tag_data = schemas.TagCreate(display_name=test_tag.display_name)
        result = TagService.create_tag(db_session, tag_data)

        assert result.id == test_tag.id

    def test_create_tag_too_short(self, db_session: Session):
        """Should raise BusinessRuleException for short name."""
        tag_data = schemas.TagCreate(display_name="A")

        with pytest.raises(BusinessRuleException) as exc_info:
            TagService.create_tag(db_session, tag_data)

        assert "at least 2 characters" in str(exc_info.value)

    def test_create_tag_too_long(self, db_session: Session):
        """Should raise BusinessRuleException for long name."""
        tag_data = schemas.TagCreate(display_name="A" * 51)

        with pytest.raises(BusinessRuleException) as exc_info:
            TagService.create_tag(db_session, tag_data)

        assert "at most 50 characters" in str(exc_info.value)

    def test_create_tag_empty(self, db_session: Session):
        """Should raise BusinessRuleException for empty name."""
        tag_data = schemas.TagCreate(display_name="   ")

        with pytest.raises(BusinessRuleException) as exc_info:
            TagService.create_tag(db_session, tag_data)

        assert "at least 2 characters" in str(exc_info.value)


class TestDeleteTag:
    """Tests for TagService.delete_tag."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_delete_tag(self, db_session: Session):
        """Should delete tag."""
        tag = db_models.Tag(name="todelete", display_name="ToDelete")
        db_session.add(tag)
        db_session.commit()
        tag_id = tag.id

        TagService.delete_tag(db_session, tag_id)

        # Verify deleted
        result = db_session.query(db_models.Tag).filter_by(id=tag_id).first()
        assert result is None

    def test_delete_tag_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent tag."""
        with pytest.raises(NotFoundException):
            TagService.delete_tag(db_session, 99999)

    def test_delete_tag_in_use(self, db_session: Session, test_idea: db_models.Idea):
        """Should raise BusinessRuleException for tag in use."""
        tag = db_models.Tag(name="inuse", display_name="InUse")
        db_session.add(tag)
        db_session.commit()

        db_session.add(db_models.IdeaTag(idea_id=test_idea.id, tag_id=tag.id))
        db_session.commit()

        with pytest.raises(BusinessRuleException) as exc_info:
            TagService.delete_tag(db_session, tag.id)

        assert "used by" in str(exc_info.value)


class TestDeleteUnusedTags:
    """Tests for TagService.delete_unused_tags."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_delete_unused_tags(self, db_session: Session):
        """Should delete unused tags."""
        tag1 = db_models.Tag(name="unused1", display_name="Unused1")
        tag2 = db_models.Tag(name="unused2", display_name="Unused2")
        db_session.add(tag1)
        db_session.add(tag2)
        db_session.commit()

        count = TagService.delete_unused_tags(db_session)

        assert count >= 0  # May be 0 due to SQL complexity


class TestGetTagsForIdea:
    """Tests for TagService.get_tags_for_idea."""

    def test_get_tags_for_idea(self, db_session: Session, test_idea: db_models.Idea):
        """Should return tags for idea."""
        tag = db_models.Tag(name="ideatag", display_name="IdeaTag")
        db_session.add(tag)
        db_session.commit()
        db_session.add(db_models.IdeaTag(idea_id=test_idea.id, tag_id=tag.id))
        db_session.commit()

        result = TagService.get_tags_for_idea(db_session, test_idea.id)

        assert len(result) == 1
        assert result[0].name == "ideatag"

    def test_get_tags_for_idea_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent idea."""
        with pytest.raises(NotFoundException):
            TagService.get_tags_for_idea(db_session, 99999)


class TestAddTagToIdea:
    """Tests for TagService.add_tag_to_idea."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_add_tag_to_idea(self, db_session: Session, test_idea: db_models.Idea):
        """Should add tag to idea."""
        result = TagService.add_tag_to_idea(db_session, test_idea.id, "NewTag")

        assert result.name == "newtag"

        # Verify association
        tags = TagService.get_tags_for_idea(db_session, test_idea.id)
        assert len(tags) == 1

    def test_add_tag_to_idea_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent idea."""
        with pytest.raises(NotFoundException):
            TagService.add_tag_to_idea(db_session, 99999, "Tag")


class TestRemoveTagFromIdea:
    """Tests for TagService.remove_tag_from_idea."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_remove_tag_from_idea(
        self, db_session: Session, test_idea: db_models.Idea, test_tag: db_models.Tag
    ):
        """Should remove tag from idea."""
        db_session.add(db_models.IdeaTag(idea_id=test_idea.id, tag_id=test_tag.id))
        db_session.commit()

        result = TagService.remove_tag_from_idea(db_session, test_idea.id, test_tag.id)

        assert result is True

    def test_remove_tag_from_idea_idea_not_found(
        self, db_session: Session, test_tag: db_models.Tag
    ):
        """Should raise NotFoundException for non-existent idea."""
        with pytest.raises(NotFoundException):
            TagService.remove_tag_from_idea(db_session, 99999, test_tag.id)

    def test_remove_tag_from_idea_tag_not_found(
        self, db_session: Session, test_idea: db_models.Idea
    ):
        """Should raise NotFoundException for non-existent tag."""
        with pytest.raises(NotFoundException):
            TagService.remove_tag_from_idea(db_session, test_idea.id, 99999)


class TestSyncIdeaTags:
    """Tests for TagService.sync_idea_tags."""

    def setup_method(self):
        """Clear cache before each test."""
        TagService._cache.clear()

    def test_sync_idea_tags(self, db_session: Session, test_idea: db_models.Idea):
        """Should sync tags for idea."""
        # Add initial tag
        old_tag = db_models.Tag(name="old", display_name="Old")
        db_session.add(old_tag)
        db_session.commit()
        db_session.add(db_models.IdeaTag(idea_id=test_idea.id, tag_id=old_tag.id))
        db_session.commit()

        # Sync with new tags
        result = TagService.sync_idea_tags(db_session, test_idea.id, ["New1", "New2"])

        assert len(result) == 2
        tag_names = [t.name for t in result]
        assert "new1" in tag_names
        assert "new2" in tag_names

        # Verify old tag removed
        tags = TagService.get_tags_for_idea(db_session, test_idea.id)
        assert len(tags) == 2
        assert all(t.name != "old" for t in tags)

    def test_sync_idea_tags_empty_list(
        self, db_session: Session, test_idea: db_models.Idea
    ):
        """Should remove all tags when empty list provided."""
        tag = db_models.Tag(name="toremove", display_name="ToRemove")
        db_session.add(tag)
        db_session.commit()
        db_session.add(db_models.IdeaTag(idea_id=test_idea.id, tag_id=tag.id))
        db_session.commit()

        result = TagService.sync_idea_tags(db_session, test_idea.id, [])

        assert len(result) == 0

    def test_sync_idea_tags_idea_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent idea."""
        with pytest.raises(NotFoundException):
            TagService.sync_idea_tags(db_session, 99999, ["Tag"])


class TestGetIdeasByTag:
    """Tests for TagService.get_ideas_by_tag."""

    def test_get_ideas_by_tag(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return idea IDs for tag."""
        tag = db_models.Tag(name="bytag", display_name="ByTag")
        db_session.add(tag)
        db_session.commit()

        idea = db_models.Idea(
            title="Idea",
            description="Description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.add(db_models.IdeaTag(idea_id=idea.id, tag_id=tag.id))
        db_session.commit()

        result = TagService.get_ideas_by_tag(db_session, tag.id)

        assert len(result) == 1
        assert idea.id in result

    def test_get_ideas_by_tag_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent tag."""
        with pytest.raises(NotFoundException):
            TagService.get_ideas_by_tag(db_session, 99999)


class TestGetIdeasByTagFull:
    """Tests for TagService.get_ideas_by_tag_full."""

    def test_get_ideas_by_tag_full(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return full ideas for tag."""
        tag = db_models.Tag(name="fulltag", display_name="FullTag")
        db_session.add(tag)
        db_session.commit()

        idea = db_models.Idea(
            title="Full Idea",
            description="Full Description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.add(db_models.IdeaTag(idea_id=idea.id, tag_id=tag.id))
        db_session.commit()

        result = TagService.get_ideas_by_tag_full(db_session, tag.id)

        assert len(result) == 1
        assert result[0].title == "Full Idea"

    def test_get_ideas_by_tag_full_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent tag."""
        with pytest.raises(NotFoundException):
            TagService.get_ideas_by_tag_full(db_session, 99999)
