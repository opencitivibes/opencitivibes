from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from repositories.database import get_db
from services.idea_service import IdeaService
from services.quality_service import QualityService
from services.vote_service import VoteService

router = APIRouter(prefix="/votes", tags=["votes"])


@router.post("/{idea_id}", response_model=schemas.Vote)
def vote_on_idea(
    idea_id: int,
    vote: schemas.VoteCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """
    Vote on an idea with optional qualities.

    - vote_type: "upvote" or "downvote"
    - quality_keys: Optional list of quality keys (only for upvotes)
    """
    # Convert quality keys to IDs if provided
    quality_ids = None
    if vote.quality_keys:
        idea = IdeaService.get_idea_by_id(db, idea_id)
        if idea:
            quality_ids = QualityService.keys_to_ids(
                db, vote.quality_keys, idea.category_id
            )

    return VoteService.vote_on_idea(
        db=db,
        idea_id=idea_id,
        user_id=current_user.id,
        vote_type=vote.vote_type,
        quality_ids=quality_ids,
    )


@router.get("/{idea_id}/qualities", response_model=List[str])
def get_vote_qualities(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """Get user's quality selections for an idea (returns quality keys)."""
    quality_ids = VoteService.get_vote_qualities(db, idea_id, current_user.id)
    return QualityService.ids_to_keys(db, quality_ids)


@router.put("/{idea_id}/qualities", response_model=List[str])
def update_vote_qualities(
    idea_id: int,
    quality_data: schemas.VoteQualityCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """Update qualities for an existing upvote (accepts quality keys)."""
    # Get idea to validate category
    idea = IdeaService.get_idea_by_id(db, idea_id)
    if not idea:
        # Let VoteService handle the error
        return VoteService.update_vote_qualities(db, idea_id, current_user.id, [])

    # Convert keys to IDs
    quality_ids = QualityService.keys_to_ids(
        db, quality_data.quality_keys, idea.category_id
    )

    # Update qualities and return keys
    updated_ids = VoteService.update_vote_qualities(
        db, idea_id, current_user.id, quality_ids
    )
    return QualityService.ids_to_keys(db, updated_ids)


@router.get("/{idea_id}/my-vote", response_model=Optional[schemas.VoteWithQualities])
def get_my_vote(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """Get current user's vote with qualities (returns quality keys)."""
    vote = VoteService.get_user_vote(db, idea_id, current_user.id)
    if not vote:
        return None

    quality_ids = VoteService.get_vote_qualities(db, idea_id, current_user.id)
    quality_keys = QualityService.ids_to_keys(db, quality_ids)
    return schemas.VoteWithQualities(
        id=vote.id,
        idea_id=vote.idea_id,
        user_id=vote.user_id,
        vote_type=vote.vote_type,
        created_at=vote.created_at,
        qualities=quality_keys,
    )


@router.delete("/{idea_id}")
def remove_vote(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """
    Remove a user's vote on an idea.

    Domain exceptions are caught by centralized exception handlers.
    """
    VoteService.remove_vote(db=db, idea_id=idea_id, user_id=current_user.id)
    return {"message": "Vote removed successfully"}
