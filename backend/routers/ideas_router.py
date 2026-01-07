from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

import authentication.auth as auth
from helpers.language import parse_accept_language
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.pagination import PaginationLimit, PaginationLimitSmall, PaginationSkip
from repositories.database import get_db
from services import IdeaService

router = APIRouter(prefix="/ideas", tags=["ideas"])


@router.get("/leaderboard", response_model=List[schemas.IdeaWithScore])
def get_leaderboard(
    category_id: Optional[int] = None,
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 20,
    accept_language: Annotated[str, Header(alias="Accept-Language")] = "fr",
    db: Session = Depends(get_db),
    current_user: Optional[db_models.User] = Depends(auth.get_current_user_optional),
):
    """
    Get leaderboard with language prioritization.

    Ideas in the user's preferred language (from Accept-Language header)
    appear first, followed by other languages. All ideas are shown.
    """
    user_id = current_user.id if current_user else None
    preferred_lang = parse_accept_language(accept_language)
    return IdeaService.get_leaderboard(
        db, category_id, user_id, skip, limit, preferred_lang
    )


@router.post("/", response_model=schemas.Idea)
def create_idea(
    idea: schemas.IdeaCreate,
    language: str = Query("en", pattern="^(en|fr)$"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """
    Create a new idea.

    Domain exceptions are caught by centralized exception handlers.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    return IdeaService.validate_and_create_idea(db, idea, user_id, language)


@router.get("/my-ideas", response_model=List[schemas.IdeaWithScore])
def get_my_ideas(
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 20,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    # Get all ideas (pending, approved, rejected) for current user
    user_id: int = current_user.id  # type: ignore[assignment]
    return IdeaService.get_my_ideas(db, user_id, skip, limit)


@router.get("/{idea_id}", response_model=schemas.IdeaWithScore)
def get_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[db_models.User] = Depends(auth.get_current_user_optional),
):
    """
    Get a single idea with scores.

    Domain exceptions are caught by centralized exception handlers.
    """
    current_user_id: int | None = int(current_user.id) if current_user else None  # type: ignore[arg-type]
    return IdeaService.get_idea_with_score(
        db=db,
        idea_id=idea_id,
        current_user_id=current_user_id,
    )


@router.put("/{idea_id}", response_model=schemas.Idea)
def update_idea(
    idea_id: int,
    idea_update: schemas.IdeaUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    # Use IdeaService to update idea
    user_id: int = current_user.id  # type: ignore[assignment]
    return IdeaService.update_idea(db, idea_id, idea_update, user_id)


@router.delete(
    "/{idea_id}",
    response_model=schemas.IdeaDeleteResponse,
    summary="Delete an idea",
    description="Soft delete an idea. Users can only delete their own ideas.",
)
def delete_idea(
    idea_id: int,
    request: Optional[schemas.IdeaDeleteRequest] = None,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.IdeaDeleteResponse:
    """
    Delete an idea (soft delete).

    - Users can only delete their own ideas
    - Reason is optional
    - Idea can be restored by admin
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    reason = request.reason if request else None

    IdeaService.soft_delete_idea(
        db=db,
        idea_id=idea_id,
        user_id=user_id,
        reason=reason,
        is_admin=False,
    )

    return schemas.IdeaDeleteResponse(
        message="Idea deleted successfully",
        idea_id=idea_id,
    )


@router.post("/check-similar", response_model=List[schemas.SimilarIdea])
def check_similar_ideas(
    similar_request: schemas.SimilarIdeaRequest,
    language: str = Query("en", pattern="^(en|fr)$"),
    threshold: float = Query(0.3, ge=0.0, le=1.0),
    limit: PaginationLimitSmall = 5,
    db: Session = Depends(get_db),
):
    """
    Check for similar ideas before submission (public endpoint).
    Helps prevent duplicate submissions by showing similar approved ideas.
    """
    return IdeaService.get_similar_ideas(
        db,
        similar_request.title,
        similar_request.description,
        similar_request.category_id,
        threshold,
        limit,
        language,
    )


@router.get("/{idea_id}/quality-counts", response_model=schemas.QualityCounts)
def get_idea_quality_counts(
    idea_id: int,
    db: Session = Depends(get_db),
):
    """Get quality voting breakdown for an idea."""
    from models.exceptions import IdeaNotFoundException
    from services.quality_service import QualityService

    # Verify idea exists
    idea = IdeaService.get_idea_by_id(db, idea_id)
    if not idea:
        raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

    return QualityService.get_quality_counts_for_idea(db, idea_id)


@router.get(
    "/{idea_id}/quality-signals",
    response_model=schemas.QualitySignalsResponse,
    summary="Get quality signals for an idea",
    description="Returns trust distribution and quality counts for an idea. Public endpoint for approved ideas.",
)
def get_idea_quality_signals(
    idea_id: int,
    db: Session = Depends(get_db),
):
    """
    Get aggregated quality signals for an idea.

    Returns:
    - Trust distribution of upvoters (excellent/good/average/below_average/low)
    - Quality voting breakdown
    - Total upvotes and votes with qualities
    """
    from models.exceptions import IdeaNotFoundException
    from services.quality_signals_service import QualitySignalsService

    # Verify idea exists
    idea = IdeaService.get_idea_by_id(db, idea_id)
    if not idea:
        raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

    return QualitySignalsService.get_signals_for_idea(db, idea_id)
