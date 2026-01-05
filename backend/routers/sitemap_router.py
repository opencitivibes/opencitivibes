"""Sitemap router for SEO optimization.

Provides lightweight endpoints for sitemap generation.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from repositories.database import get_db
from services.sitemap_service import SitemapService

router = APIRouter(prefix="/sitemap", tags=["sitemap"])


class SitemapIdea(BaseModel):
    """Lightweight idea representation for sitemap."""

    id: int
    updated_at: datetime
    score: int

    model_config = {"from_attributes": True}


@router.get("/ideas", response_model=list[SitemapIdea])
def get_sitemap_ideas(db: Session = Depends(get_db)) -> list[SitemapIdea]:
    """Get all approved ideas for sitemap generation.

    Returns minimal data needed for sitemap:
    - id: for URL generation
    - updated_at: for lastmod
    - score: for priority calculation
    """
    ideas = SitemapService.get_sitemap_ideas(db)
    return [
        SitemapIdea(
            id=idea.id,
            updated_at=idea.updated_at,
            score=idea.score,
        )
        for idea in ideas
    ]
