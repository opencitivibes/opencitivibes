"""Public configuration endpoint for frontend."""

from fastapi import APIRouter

from services.config_service import get_config

router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/public", response_model=dict)
def get_public_config() -> dict:
    """Get public platform configuration.

    Returns non-sensitive configuration for frontend use.
    Excludes admin emails, internal settings, etc.
    """
    config = get_config()

    return {
        "platform": config.platform,
        "instance": {
            "name": config.instance.name,
            "entity": {
                "type": config.instance.entity.type,
                "name": config.instance.entity.name,
            },
            "location": config.instance.location,
        },
        "branding": config.branding.model_dump() if config.branding else None,
        "localization": config.localization.model_dump(),
        "features": config.features,
        "contact": {
            "email": config.contact.email,
        },
        "legal": (
            {
                "jurisdiction": config.legal.jurisdiction,
            }
            if config.legal
            else None
        ),
    }
