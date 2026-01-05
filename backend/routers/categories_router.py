from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models.schemas as schemas
from repositories.database import get_db
from services import CategoryService
from services.quality_service import QualityService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[schemas.Category])
def get_categories(
    db: Session = Depends(get_db),
):
    """
    Get all categories.

    Categories are few in number, so pagination is not needed.
    """
    return CategoryService.get_all_categories(db)


@router.get("/qualities/defaults", response_model=List[schemas.QualityPublic])
def get_default_qualities(db: Session = Depends(get_db)):
    """Get all default qualities (applies to all categories)."""
    return QualityService.get_all_default_qualities(db)


@router.get("/{category_id}", response_model=schemas.Category)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a specific category by ID."""
    return CategoryService.get_category_by_id(db, category_id)


@router.get("/{category_id}/qualities", response_model=List[schemas.QualityPublic])
def get_category_qualities(
    category_id: int,
    db: Session = Depends(get_db),
):
    """
    Get available qualities for a category.

    Returns qualities that can be attached to votes for ideas in this category.
    Includes default qualities and category-specific additions.
    """
    return QualityService.get_qualities_for_category(db, category_id)
