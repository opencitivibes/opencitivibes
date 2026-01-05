#!/usr/bin/env python3
# ruff: noqa: E402
# E402 disabled: sys.path modification must occur before imports
"""
One-time migration script to sanitize existing idea content.

This script audits and cleans all existing ideas in the database,
removing any potentially malicious HTML/JavaScript that may have
been stored before sanitization was implemented.

Usage:
    cd backend && uv run python -m scripts.sanitize_existing_ideas

The script will:
1. Load all existing ideas from the database
2. Apply sanitization to title and description
3. Log any changes made
4. Commit the sanitized data
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.sanitization import sanitize_html, sanitize_plain_text
from repositories.database import SessionLocal
from repositories.db_models import Idea


def sanitize_existing_ideas() -> None:
    """Sanitize all existing ideas in the database."""
    db = SessionLocal()
    try:
        ideas = db.query(Idea).all()
        total = len(ideas)
        sanitized_count = 0
        changes: list[dict] = []

        print(f"Auditing {total} ideas for XSS content...")

        for idea in ideas:
            original_title = idea.title
            original_desc = idea.description

            new_title = sanitize_plain_text(
                str(original_title) if original_title else None
            )
            new_desc = sanitize_html(str(original_desc) if original_desc else None)

            title_changed = new_title != original_title
            desc_changed = new_desc != original_desc

            if title_changed or desc_changed:
                sanitized_count += 1
                idea.title = new_title  # type: ignore[assignment]
                idea.description = new_desc  # type: ignore[assignment]

                change_record: dict = {
                    "id": idea.id,
                    "title_changed": title_changed,
                    "desc_changed": desc_changed,
                }

                if title_changed:
                    change_record["original_title"] = (
                        str(original_title)[:100] if original_title else ""
                    )
                    change_record["sanitized_title"] = (
                        str(new_title)[:100] if new_title else ""
                    )
                if desc_changed:
                    change_record["original_desc"] = (
                        str(original_desc)[:200] if original_desc else ""
                    )
                    change_record["sanitized_desc"] = (
                        str(new_desc)[:200] if new_desc else ""
                    )

                changes.append(change_record)
                title_preview = (
                    str(original_title)[:50] if original_title else "No title"
                )
                print(f"  Sanitized idea {idea.id}: {title_preview}")

        if sanitized_count > 0:
            db.commit()
            print(f"\nCommitted {sanitized_count} sanitized ideas.")

            # Write audit log
            audit_file = (
                Path(__file__).parent
                / f"sanitization_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(audit_file, "w") as f:
                json.dump(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "total_ideas": total,
                        "sanitized_count": sanitized_count,
                        "changes": changes,
                    },
                    f,
                    indent=2,
                )
            print(f"Audit log written to: {audit_file}")
        else:
            print("\nNo ideas required sanitization.")

        print(f"\nSummary: {sanitized_count}/{total} ideas sanitized")

    finally:
        db.close()


if __name__ == "__main__":
    sanitize_existing_ideas()
