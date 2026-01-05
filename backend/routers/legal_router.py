"""Legal content endpoints.

Serves legal documents (Terms of Service, Privacy Policy) from Markdown files
with YAML frontmatter, supporting placeholder interpolation for instance-specific
content.
"""

import re
from pathlib import Path
from typing import Literal

import markdown
import yaml
from fastapi import APIRouter
from pydantic import BaseModel

from services.config_service import get_config, get_entity_name, get_instance_name

router = APIRouter(prefix="/legal", tags=["legal"])

# Directory containing legal markdown files
LEGAL_CONTENT_DIR = Path(__file__).parent.parent / "config" / "legal"


class LegalDocumentResponse(BaseModel):
    """Response model for legal document content."""

    version: str
    last_updated: str
    html_content: str


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Raw markdown content with optional YAML frontmatter.

    Returns:
        Tuple of (frontmatter dict, markdown body).
    """
    frontmatter: dict = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                frontmatter = {}
            body = parts[2].strip()

    return frontmatter, body


def _interpolate_placeholders(content: str, locale: str) -> str:
    """Replace placeholders with actual configuration values.

    Args:
        content: Content with {{placeholder}} markers.
        locale: Locale for localized values (e.g., 'en', 'fr').

    Returns:
        Content with placeholders replaced by actual values.
    """
    config = get_config()

    replacements = {
        "{{instanceName}}": get_instance_name(locale),
        "{{entityName}}": get_entity_name(locale),
        "{{contactEmail}}": config.contact.email,
        "{{jurisdiction}}": (
            config.legal.jurisdiction.get(locale, "") if config.legal else ""
        ),
        "{{courts}}": (config.legal.courts.get(locale, "") if config.legal else ""),
        "{{privacyAuthority}}": (
            config.legal.privacy_authority.get("name", {}).get(locale, "")
            if config.legal and config.legal.privacy_authority
            else ""
        ),
    }

    result = content
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    return result


def _load_legal_document(
    doc_type: Literal["terms", "privacy"],
    locale: str,
) -> LegalDocumentResponse | None:
    """Load and process a legal document.

    Args:
        doc_type: Type of document ('terms' or 'privacy').
        locale: Locale for the document ('en' or 'fr').

    Returns:
        Processed legal document or None if not found.
    """
    # Try requested locale, fall back to English
    file_path = LEGAL_CONTENT_DIR / f"{doc_type}.{locale}.md"
    if not file_path.exists():
        file_path = LEGAL_CONTENT_DIR / f"{doc_type}.en.md"

    if not file_path.exists():
        return None

    raw_content = file_path.read_text(encoding="utf-8")

    # Parse frontmatter and body
    frontmatter, body = _parse_frontmatter(raw_content)

    # Interpolate placeholders in the markdown body
    interpolated_body = _interpolate_placeholders(body, locale)

    # Convert markdown to HTML
    md = markdown.Markdown(extensions=["extra", "smarty"])
    html_content = md.convert(interpolated_body)

    # Clean up the HTML: remove the h1 title since frontend will display it separately
    # The h1 is the document title from the markdown
    html_content = re.sub(r"<h1>.*?</h1>\s*", "", html_content, count=1)

    return LegalDocumentResponse(
        version=frontmatter.get("version", "1.0"),
        last_updated=frontmatter.get("lastUpdated", ""),
        html_content=html_content,
    )


@router.get("/terms/{locale}", response_model=LegalDocumentResponse)
def get_terms_of_service(locale: str = "en") -> LegalDocumentResponse:
    """Get Terms of Service for specified locale.

    Args:
        locale: Language code ('en' or 'fr').

    Returns:
        Terms of Service content as HTML with metadata.
    """
    doc = _load_legal_document("terms", locale)
    if doc is None:
        # Return empty document if file not found
        return LegalDocumentResponse(
            version="1.0",
            last_updated="",
            html_content="<p>Terms of Service content not available.</p>",
        )
    return doc


@router.get("/privacy/{locale}", response_model=LegalDocumentResponse)
def get_privacy_policy(locale: str = "en") -> LegalDocumentResponse:
    """Get Privacy Policy for specified locale.

    Args:
        locale: Language code ('en' or 'fr').

    Returns:
        Privacy Policy content as HTML with metadata.
    """
    doc = _load_legal_document("privacy", locale)
    if doc is None:
        # Return empty document if file not found
        return LegalDocumentResponse(
            version="1.0",
            last_updated="",
            html_content="<p>Privacy Policy content not available.</p>",
        )
    return doc


@router.get("/moderation-transparency")
def get_moderation_transparency() -> dict:
    """Get content moderation transparency information.

    Returns information about automated systems used in content moderation
    as required by Law 25 Article 12.1.

    Returns:
        Dictionary containing moderation transparency details.
    """
    return {
        "trust_score": {
            "description": "Score reflecting positive contribution history",
            "range": "0-100",
            "starting_value": 50,
            "effects": {
                "below_30": "Comments require approval",
                "above_70": "Comments auto-approved",
            },
        },
        "automated_flagging": {
            "description": "Automatic detection of potentially problematic content",
            "action": "Flags for human review only",
            "human_decision": True,
        },
        "community_flagging": {
            "description": "User-reported content",
            "auto_hide_threshold": 3,
            "human_review": True,
        },
        "appeal_process": {
            "available": True,
            "response_time": "48 hours",
            "contact": "moderation@idees-montreal.ca",
        },
    }


@router.get("/cross-border-transfers")
def get_cross_border_info() -> dict:
    """Get information about cross-border data transfers.

    Returns documentation about cross-border transfers as required by
    Law 25 Article 17.

    Returns:
        Dictionary containing transfer details and safeguards.
    """
    return {
        "transfers": [
            {
                "recipient": "Sentry",
                "location": "United States",
                "purpose": "Error monitoring",
                "data_types": ["Error logs", "Correlation IDs"],
                "pii_transferred": False,
                "safeguards": ["DPA", "SCCs", "SOC 2 Type II"],
            },
            {
                "recipient": "Email Provider",
                "purpose": "Transactional emails",
                "data_types": ["Email addresses"],
                "safeguards": ["TLS", "DPA"],
            },
        ],
        "privacy_contact": "privacy@idees-montreal.ca",
    }
