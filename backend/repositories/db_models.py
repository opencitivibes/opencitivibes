"""
Database models using SQLAlchemy 2.0 style with Mapped type hints.

This module defines all database models with proper type annotations
for improved IDE support and type checking.
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repositories.database import Base


class TSVectorType(TypeDecorator):
    """
    PostgreSQL TSVECTOR type that falls back to Text for other databases.

    This custom type allows the same model to work with both PostgreSQL
    (using native tsvector) and SQLite (using nullable Text columns).
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import TSVECTOR

            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


class IdeaStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VoteType(str, enum.Enum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"


class StakeholderType(str, enum.Enum):
    """Type of stakeholder relationship to an idea's location/topic."""

    RESIDENT_NEARBY = "resident_nearby"  # Lives near the proposed location
    BUSINESS_OWNER = "business_owner"  # Owns/operates a business in the area
    COMMUTER = "commuter"  # Regularly passes through the area
    PARENT = "parent"  # Parent with children (family-oriented ideas)
    WORKER = "worker"  # Works in the area
    OTHER = "other"  # Other relationship


# Content Moderation Enums


class FlagReason(str, enum.Enum):
    """Reasons for flagging content."""

    SPAM = "spam"
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment"
    OFF_TOPIC = "off_topic"
    MISINFORMATION = "misinformation"
    OTHER = "other"


class FlagStatus(str, enum.Enum):
    """Status of a content flag."""

    PENDING = "pending"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


class ContentType(str, enum.Enum):
    """Type of content being flagged."""

    COMMENT = "comment"
    IDEA = "idea"


class PenaltyType(str, enum.Enum):
    """Types of user penalties."""

    WARNING = "warning"
    TEMP_BAN_24H = "temp_ban_24h"
    TEMP_BAN_7D = "temp_ban_7d"
    TEMP_BAN_30D = "temp_ban_30d"
    PERMANENT_BAN = "permanent_ban"


class PenaltyStatus(str, enum.Enum):
    """Status of a user penalty."""

    ACTIVE = "active"
    EXPIRED = "expired"
    APPEALED = "appealed"
    REVOKED = "revoked"


class AppealStatus(str, enum.Enum):
    """Status of a penalty appeal."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def _utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_global_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Trust score system (content moderation)
    trust_score: Mapped[int] = mapped_column(Integer, default=50)
    approved_comments_count: Mapped[int] = mapped_column(Integer, default=0)
    total_flags_received: Mapped[int] = mapped_column(Integer, default=0)
    valid_flags_received: Mapped[int] = mapped_column(Integer, default=0)
    flags_submitted_validated: Mapped[int] = mapped_column(Integer, default=0)
    requires_comment_approval: Mapped[bool] = mapped_column(Boolean, default=True)

    # Official role fields (granted by admin)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    official_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    official_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Official request fields (from signup - pending admin approval)
    requests_official_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    official_title_request: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    official_request_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Two-Factor Authentication (2FA) fields
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Consent Management Fields (Law 25 Compliance)
    consent_terms_accepted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="User accepted Terms of Service"
    )
    consent_privacy_accepted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="User accepted Privacy Policy"
    )
    consent_terms_version: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Version of Terms accepted (e.g., '1.0')"
    )
    consent_privacy_version: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Version of Privacy Policy accepted (e.g., '1.0')",
    )
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="When consent was given"
    )
    marketing_consent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="User opted into marketing communications",
    )
    marketing_consent_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="When marketing consent was given/withdrawn"
    )

    # Data Retention Tracking (Law 25 Compliance - Phase 3)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="Last successful login timestamp"
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last activity timestamp (any authenticated action)",
    )
    inactivity_warning_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="When inactivity warning email was sent"
    )
    scheduled_anonymization_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="When account is scheduled for anonymization"
    )

    # Privacy Settings (Law 25 Compliance - Phase 4: Article 9.1, 10)
    profile_visibility: Mapped[str] = mapped_column(
        String(20),
        default="public",
        nullable=False,
        comment="Profile visibility: public, registered, private",
    )
    show_display_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Show display name on public profile",
    )
    show_avatar: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Show avatar on public profile",
    )
    show_activity: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Show activity (ideas, comments) on public profile",
    )
    show_join_date: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Show account creation date on public profile",
    )

    # Relationships
    ideas: Mapped[List["Idea"]] = relationship(
        "Idea",
        back_populates="author",
        foreign_keys=lambda: [Idea.user_id],
    )
    votes: Mapped[List["Vote"]] = relationship("Vote", back_populates="user")
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="user", foreign_keys="[Comment.user_id]"
    )
    admin_roles: Mapped[List["AdminRole"]] = relationship(
        "AdminRole", back_populates="user"
    )
    comment_likes: Mapped[List["CommentLike"]] = relationship(
        "CommentLike", back_populates="user", cascade="all, delete-orphan"
    )
    # 2FA relationships
    totp_secret: Mapped[Optional["UserTOTPSecret"]] = relationship(
        "UserTOTPSecret",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    backup_codes: Mapped[List["UserBackupCode"]] = relationship(
        "UserBackupCode", back_populates="user", cascade="all, delete-orphan"
    )
    consent_logs: Mapped[List["ConsentLog"]] = relationship(
        "ConsentLog", back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_en: Mapped[str] = mapped_column(String, nullable=False)
    name_fr: Mapped[str] = mapped_column(String, nullable=False)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_fr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    ideas: Mapped[List["Idea"]] = relationship("Idea", back_populates="category")
    admin_roles: Mapped[List["AdminRole"]] = relationship(
        "AdminRole", back_populates="category"
    )
    quality_overrides: Mapped[List["CategoryQuality"]] = relationship(
        "CategoryQuality", back_populates="category", cascade="all, delete-orphan"
    )


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[IdeaStatus] = mapped_column(
        Enum(IdeaStatus), default=IdeaStatus.PENDING, nullable=False
    )
    admin_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # PostgreSQL full-text search vectors (nullable for SQLite compatibility)
    search_vector_en: Mapped[Optional[str]] = mapped_column(TSVectorType, nullable=True)
    search_vector_fr: Mapped[Optional[str]] = mapped_column(TSVectorType, nullable=True)

    # Soft delete fields
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    deleted_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flag-related fields (content moderation)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    flag_count: Mapped[int] = mapped_column(Integer, default=0)

    # Language tracking for multilingual content
    language: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="fr",
        index=True,
        doc="Language code (fr/en) of the content",
    )

    # Relationships
    author: Mapped["User"] = relationship(
        "User", back_populates="ideas", foreign_keys=[user_id]
    )
    category: Mapped["Category"] = relationship("Category", back_populates="ideas")
    votes: Mapped[List["Vote"]] = relationship(
        "Vote", back_populates="idea", cascade="all, delete-orphan"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="idea", cascade="all, delete-orphan"
    )
    idea_tags: Mapped[List["IdeaTag"]] = relationship(
        "IdeaTag", back_populates="idea", cascade="all, delete-orphan"
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag", secondary="idea_tags", viewonly=True
    )
    deleted_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[deleted_by], backref="deleted_ideas"
    )

    __table_args__ = (
        Index("ix_ideas_status", "status"),
        Index("ix_ideas_user_status", "user_id", "status"),
        Index("ix_ideas_category", "category_id"),
        Index("ix_ideas_hidden", "is_hidden"),
        # Note: deleted_at index is created by index=True on the column
    )


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("idea_id", "user_id", name="uq_vote_idea_user"),
        Index("ix_votes_idea", "idea_id"),
        Index("ix_votes_user_idea", "user_id", "idea_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idea_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ideas.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    vote_type: Mapped[VoteType] = mapped_column(Enum(VoteType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Future-proofing fields (nullable, not used initially)
    voter_neighborhood: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    stakeholder_type: Mapped[Optional[StakeholderType]] = mapped_column(
        Enum(StakeholderType), nullable=True
    )

    # Relationships
    idea: Mapped["Idea"] = relationship("Idea", back_populates="votes")
    user: Mapped["User"] = relationship("User", back_populates="votes")
    qualities: Mapped[List["VoteQuality"]] = relationship(
        "VoteQuality", back_populates="vote", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_idea_moderated", "idea_id", "is_moderated"),
        Index("ix_comments_hidden", "is_hidden"),
        Index("ix_comments_requires_approval", "requires_approval"),
        Index("ix_comments_deleted", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idea_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ideas.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_moderated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Soft delete fields (content moderation)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flag-related fields (content moderation)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    flag_count: Mapped[int] = mapped_column(Integer, default=0)

    # Pending approval for new users (content moderation)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Like count (denormalized for performance)
    like_count: Mapped[int] = mapped_column(Integer, default=0)

    # Language tracking for multilingual content
    language: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="fr",
        doc="Language code (fr/en) of the comment",
    )

    # Relationships
    idea: Mapped["Idea"] = relationship("Idea", back_populates="comments")
    user: Mapped["User"] = relationship(
        "User", back_populates="comments", foreign_keys=[user_id]
    )
    deleted_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[deleted_by]
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approved_by]
    )
    likes: Mapped[List["CommentLike"]] = relationship(
        "CommentLike", back_populates="comment", cascade="all, delete-orphan"
    )


class CommentLike(Base):
    """Tracks user likes on comments."""

    __tablename__ = "comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_like_comment_user"),
        Index("ix_comment_likes_comment", "comment_id"),
        Index("ix_comment_likes_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    comment: Mapped["Comment"] = relationship("Comment", back_populates="likes")
    user: Mapped["User"] = relationship("User", back_populates="comment_likes")


class AdminRole(Base):
    __tablename__ = "admin_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_admin_role_user_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="admin_roles")
    category: Mapped["Category"] = relationship(
        "Category", back_populates="admin_roles"
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    idea_tags: Mapped[List["IdeaTag"]] = relationship("IdeaTag", back_populates="tag")
    ideas: Mapped[List["Idea"]] = relationship(
        "Idea", secondary="idea_tags", viewonly=True
    )


class IdeaTag(Base):
    __tablename__ = "idea_tags"
    __table_args__ = (UniqueConstraint("idea_id", "tag_id", name="uq_idea_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idea_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ideas.id"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    idea: Mapped["Idea"] = relationship("Idea", back_populates="idea_tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="idea_tags")


# ============================================================================
# Vote Qualities Models
# ============================================================================


class Quality(Base):
    """Defines available qualities that can be attached to votes."""

    __tablename__ = "qualities"
    __table_args__ = (Index("ix_qualities_is_default", "is_default"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_fr: Mapped[str] = mapped_column(String(100), nullable=False)
    description_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description_fr: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # lucide icon name
    color: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # tailwind color
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    category_overrides: Mapped[List["CategoryQuality"]] = relationship(
        "CategoryQuality", back_populates="quality", cascade="all, delete-orphan"
    )
    vote_qualities: Mapped[List["VoteQuality"]] = relationship(
        "VoteQuality", back_populates="quality", cascade="all, delete-orphan"
    )


class CategoryQuality(Base):
    """Overrides for quality availability per category."""

    __tablename__ = "category_qualities"
    __table_args__ = (
        UniqueConstraint("category_id", "quality_id", name="uq_category_quality"),
        Index("ix_category_qualities_category", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    quality_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("qualities.id", ondelete="CASCADE"), nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category", back_populates="quality_overrides"
    )
    quality: Mapped["Quality"] = relationship(
        "Quality", back_populates="category_overrides"
    )


class VoteQuality(Base):
    """User's quality selections for a vote."""

    __tablename__ = "vote_qualities"
    __table_args__ = (
        UniqueConstraint("vote_id", "quality_id", name="uq_vote_quality"),
        Index("ix_vote_qualities_vote", "vote_id"),
        Index("ix_vote_qualities_quality", "quality_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("votes.id", ondelete="CASCADE"), nullable=False
    )
    quality_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("qualities.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    vote: Mapped["Vote"] = relationship("Vote", back_populates="qualities")
    quality: Mapped["Quality"] = relationship(
        "Quality", back_populates="vote_qualities"
    )


# ============================================================================
# Content Moderation Models
# ============================================================================


class ContentFlag(Base):
    """
    Tracks flags/reports on comments and ideas.

    Flags are unique per (content_type, content_id, reporter_id).
    When flag_count reaches threshold (3), content is auto-hidden.
    """

    __tablename__ = "content_flags"
    __table_args__ = (
        UniqueConstraint(
            "content_type",
            "content_id",
            "reporter_id",
            name="uq_flag_content_reporter",
        ),
        Index("ix_content_flags_content", "content_type", "content_id"),
        Index("ix_content_flags_status", "status"),
        Index("ix_content_flags_reporter", "reporter_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reporter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[FlagReason] = mapped_column(Enum(FlagReason), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Additional context from reporter
    status: Mapped[FlagStatus] = mapped_column(
        Enum(FlagStatus), default=FlagStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    reporter: Mapped["User"] = relationship(
        "User", foreign_keys=[reporter_id], backref="flags_submitted"
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by]
    )


class UserPenalty(Base):
    """
    Tracks warnings, temporary bans, and permanent bans for users.

    Penalty progression: WARNING -> 24H -> 7D -> 30D -> PERMANENT
    """

    __tablename__ = "user_penalties"
    __table_args__ = (
        Index("ix_user_penalties_user_status", "user_id", "status"),
        Index("ix_user_penalties_expires", "expires_at"),
        Index("ix_user_penalties_type", "penalty_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    penalty_type: Mapped[PenaltyType] = mapped_column(Enum(PenaltyType), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PenaltyStatus] = mapped_column(
        Enum(PenaltyStatus), default=PenaltyStatus.ACTIVE, nullable=False
    )
    issued_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )  # NULL = permanent
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    revoke_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_flag_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of flag IDs

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], backref="penalties"
    )
    issuer: Mapped["User"] = relationship("User", foreign_keys=[issued_by])
    revoker: Mapped[Optional["User"]] = relationship("User", foreign_keys=[revoked_by])


class Appeal(Base):
    """
    Allows users to appeal penalties.

    One appeal per penalty. Admins review and approve/reject.
    """

    __tablename__ = "appeals"
    __table_args__ = (
        UniqueConstraint("penalty_id", name="uq_appeal_penalty"),
        Index("ix_appeals_status", "status"),
        Index("ix_appeals_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    penalty_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_penalties.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AppealStatus] = mapped_column(
        Enum(AppealStatus), default=AppealStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    penalty: Mapped["UserPenalty"] = relationship("UserPenalty", backref="appeal")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by]
    )


class KeywordWatchlist(Base):
    """
    Auto-flag content containing certain keywords/phrases.

    Keywords can be plain text or regex patterns.
    """

    __tablename__ = "keyword_watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    keyword: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_flag_reason: Mapped[FlagReason] = mapped_column(
        Enum(FlagReason), default=FlagReason.SPAM, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, onupdate=_utc_now
    )
    match_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    creator: Mapped["User"] = relationship("User")


class AdminNote(Base):
    """Internal admin notes on user profiles for moderation context."""

    __tablename__ = "admin_notes"
    __table_args__ = (Index("ix_admin_notes_user", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, onupdate=_utc_now
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], backref="admin_notes"
    )
    author: Mapped["User"] = relationship("User", foreign_keys=[created_by])


# ============================================================================
# Email Login Models
# ============================================================================


class EmailLoginCode(Base):
    """One-time codes for passwordless email login."""

    __tablename__ = "email_login_codes"
    __table_args__ = (
        Index("ix_email_login_codes_user_created", "user_id", "created_at"),
        Index("ix_email_login_codes_expires", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hash
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True
    )  # IPv6 max length

    # Relationships
    user: Mapped["User"] = relationship("User", backref="email_login_codes")


# ============================================================================
# Two-Factor Authentication (2FA) Models
# ============================================================================


class UserTOTPSecret(Base):
    """TOTP secret for 2FA authentication."""

    __tablename__ = "user_totp_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    encrypted_secret: Mapped[str] = mapped_column(
        String(256), nullable=False
    )  # Fernet-encrypted
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="totp_secret")


class UserBackupCode(Base):
    """Backup recovery codes for 2FA."""

    __tablename__ = "user_backup_codes"
    __table_args__ = (Index("idx_backup_codes_user_unused", "user_id", "used_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hash
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="backup_codes")


# ============================================================================
# Consent Management Models (Law 25 Compliance)
# ============================================================================


class PolicyVersion(Base):
    """
    Track versions of legal documents (privacy policy, terms).

    Required by Law 25 for demonstrating consent to specific versions.
    """

    __tablename__ = "policy_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Type: 'privacy' or 'terms'"
    )
    version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Version number (e.g., '1.0', '1.1')"
    )
    effective_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="When this version becomes effective"
    )
    summary_en: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Summary of changes in English"
    )
    summary_fr: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Summary of changes in French"
    )
    requires_reconsent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether users need to re-consent to this version",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("policy_type", "version", name="uq_policy_version"),
    )


class ConsentLog(Base):
    """
    Audit log for all consent-related actions.

    Required by Quebec Law 25 for demonstrating compliance.
    Tracks all consent grants, withdrawals, and updates with IP/user agent.
    """

    __tablename__ = "consent_logs"
    __table_args__ = (
        Index("ix_consent_logs_user_id", "user_id"),
        Index("ix_consent_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    consent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Type: 'terms', 'privacy', 'marketing'"
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Action: 'granted', 'withdrawn', 'updated'"
    )
    policy_version: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Version of policy at time of action"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True, comment="IP address when action was taken"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Browser/client user agent"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="consent_logs")


# ============================================================================
# Security Audit & Breach Notification Models (Law 25 Compliance - Phase 5)
# ============================================================================


class SecurityAuditLog(Base):
    """
    Security audit log for tracking security-relevant events.

    Required by Law 25 for breach detection and investigation.
    """

    __tablename__ = "security_audit_logs"
    __table_args__ = (
        Index("ix_security_audit_user_created", "user_id", "created_at"),
        Index("ix_security_audit_type_created", "event_type", "created_at"),
        Index("ix_security_audit_ip_created", "ip_address", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Event type: login_failed, login_success, data_export, admin_access_pii",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Severity: info, warning, critical",
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who triggered the event (if applicable)",
    )
    target_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User affected by the event (e.g., for admin actions)",
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True, comment="Client IP address"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Client user agent"
    )
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Resource type: user, idea, comment"
    )
    resource_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Resource ID"
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Action taken: view, create, update, delete, export",
    )
    details: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON with additional event details"
    )
    success: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether the action succeeded"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False, index=True
    )


class PrivacyIncident(Base):
    """
    Privacy incident register for Law 25 compliance.

    Tracks all privacy incidents including breaches.
    Required by Article 3.6 of Law 25.
    """

    __tablename__ = "privacy_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="Unique incident number (e.g., INC-2026-001)",
    )
    incident_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: unauthorized_access, data_loss, data_breach, system_compromise",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Severity: low, medium, high, critical",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        default="open",
        comment="Status: open, investigating, contained, mitigated, closed",
    )

    # Timeline
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="When incident was discovered"
    )
    occurred_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="When incident occurred (if known)"
    )
    contained_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="When incident was contained"
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="When incident was fully resolved"
    )

    # Description
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Brief incident title"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Detailed description of the incident"
    )
    root_cause: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Root cause analysis"
    )

    # Impact
    affected_users_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Number of affected users"
    )
    affected_user_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON array of affected user IDs"
    )
    data_types_involved: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON array of data types involved"
    )
    risk_of_harm: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        nullable=False,
        comment="Risk level: none, low, medium, high, serious",
    )

    # Notifications (Law 25 Article 3.6)
    cai_notification_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether CAI notification needed",
    )
    cai_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cai_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cai_reference_number: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="CAI reference number if provided"
    )

    users_notification_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user notification is required",
    )
    users_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    users_notified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Remediation
    mitigation_measures: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Measures taken to mitigate harm"
    )
    preventive_measures: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Measures to prevent recurrence"
    )

    # Metadata
    reported_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, onupdate=_utc_now
    )
