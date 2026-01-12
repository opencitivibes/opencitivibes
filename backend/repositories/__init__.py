"""
Repository pattern implementation for data access layer.
"""

from .admin_role_repository import AdminRoleRepository
from .base import BaseRepository
from .category_repository import CategoryRepository
from .comment_repository import CommentRepository
from .idea_repository import IdeaRepository
from .parental_consent_repository import ParentalConsentRepository
from .user_repository import UserRepository
from .vote_repository import VoteRepository

__all__ = [
    "AdminRoleRepository",
    "BaseRepository",
    "CategoryRepository",
    "CommentRepository",
    "IdeaRepository",
    "ParentalConsentRepository",
    "UserRepository",
    "VoteRepository",
]
