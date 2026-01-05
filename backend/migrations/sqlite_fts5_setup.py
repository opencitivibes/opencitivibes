#!/usr/bin/env python3
"""
SQLite FTS5 setup migration.

Creates the FTS5 virtual table and triggers for idea search.
Run this after init_db.py to enable full-text search.

Usage:
    cd backend
    python migrations/sqlite_fts5_setup.py
"""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from repositories.database import SessionLocal, engine

FTS_TABLE_NAME = "ideas_fts"


def check_fts5_support() -> bool:
    """Check if SQLite has FTS5 support."""
    with engine.connect() as conn:
        try:
            # Try to create a temporary FTS5 table
            conn.execute(text("CREATE VIRTUAL TABLE temp_fts5_test USING fts5(test)"))
            conn.execute(text("DROP TABLE temp_fts5_test"))
            conn.commit()
            return True
        except Exception as e:
            print(f"FTS5 not supported: {e}")
            return False


def table_exists() -> bool:
    """Check if FTS table already exists."""
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{FTS_TABLE_NAME}'
        """)  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
        )
        return result.fetchone() is not None


def create_fts_table() -> bool:
    """Create FTS5 virtual table for idea search."""
    if table_exists():
        print(f"FTS table '{FTS_TABLE_NAME}' already exists. Skipping creation.")
        return False

    with engine.connect() as conn:
        # Create FTS5 virtual table
        # Using porter tokenizer for English stemming and unicode61 for proper unicode handling
        conn.execute(
            text(f"""
            CREATE VIRTUAL TABLE {FTS_TABLE_NAME} USING fts5(
                idea_id UNINDEXED,
                title,
                description,
                tags,
                tokenize='porter unicode61'
            )
        """)  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
        )
        conn.commit()
        print(f"Created FTS5 table '{FTS_TABLE_NAME}'")
        return True


def populate_fts_table() -> int:
    """Populate FTS table with existing ideas."""
    db = SessionLocal()
    try:
        # Get all ideas with their tags using raw SQL for efficiency
        result = db.execute(
            text("""
            SELECT
                i.id,
                i.title,
                i.description,
                COALESCE(GROUP_CONCAT(t.name, ' '), '') as tags
            FROM ideas i
            LEFT JOIN idea_tags it ON i.id = it.idea_id
            LEFT JOIN tags t ON it.tag_id = t.id
            GROUP BY i.id
        """)
        )

        ideas = result.fetchall()
        count = 0

        for idea in ideas:
            db.execute(
                text(f"""
                    INSERT INTO {FTS_TABLE_NAME}(idea_id, title, description, tags)
                    VALUES (:idea_id, :title, :description, :tags)
                """),  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
                {
                    "idea_id": idea[0],
                    "title": idea[1] or "",
                    "description": idea[2] or "",
                    "tags": idea[3] or "",
                },
            )
            count += 1

        db.commit()
        print(f"Indexed {count} ideas in FTS table")
        return count

    finally:
        db.close()


def create_triggers() -> None:
    """Create triggers to keep FTS in sync with ideas table."""
    with engine.connect() as conn:
        # Drop existing triggers if any (for idempotency)
        for trigger_name in [
            "ideas_fts_insert",
            "ideas_fts_update",
            "ideas_fts_delete",
            "idea_tags_insert_fts",
            "idea_tags_delete_fts",
        ]:
            try:
                conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))  # nosec B608
            except Exception as e:
                # Ignore if trigger doesn't exist - this is expected during idempotent setup
                import logging

                logging.debug(
                    f"Trigger {trigger_name} does not exist or could not be dropped: {e}"
                )

        # Insert trigger - when a new idea is created
        conn.execute(
            text(f"""
            CREATE TRIGGER ideas_fts_insert
            AFTER INSERT ON ideas
            BEGIN
                INSERT INTO {FTS_TABLE_NAME}(idea_id, title, description, tags)
                VALUES (
                    NEW.id,
                    NEW.title,
                    COALESCE(NEW.description, ''),
                    (SELECT COALESCE(GROUP_CONCAT(t.name, ' '), '')
                     FROM tags t
                     JOIN idea_tags it ON t.id = it.tag_id
                     WHERE it.idea_id = NEW.id)
                );
            END
        """)  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
        )

        # Update trigger - when an idea is updated
        conn.execute(
            text(f"""
            CREATE TRIGGER ideas_fts_update
            AFTER UPDATE ON ideas
            BEGIN
                UPDATE {FTS_TABLE_NAME} SET
                    title = NEW.title,
                    description = COALESCE(NEW.description, '')
                WHERE idea_id = NEW.id;
            END
        """)  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
        )

        # Delete trigger - when an idea is deleted
        conn.execute(
            text(f"""
            CREATE TRIGGER ideas_fts_delete
            AFTER DELETE ON ideas
            BEGIN
                DELETE FROM {FTS_TABLE_NAME} WHERE idea_id = OLD.id;
            END
        """)  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
        )

        # Tag insert trigger - when a tag is added to an idea
        conn.execute(
            text(f"""
            CREATE TRIGGER idea_tags_insert_fts
            AFTER INSERT ON idea_tags
            BEGIN
                UPDATE {FTS_TABLE_NAME} SET
                    tags = (SELECT COALESCE(GROUP_CONCAT(t.name, ' '), '')
                            FROM tags t
                            JOIN idea_tags it ON t.id = it.tag_id
                            WHERE it.idea_id = NEW.idea_id)
                WHERE idea_id = NEW.idea_id;
            END
        """)  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
        )

        # Tag delete trigger - when a tag is removed from an idea
        conn.execute(
            text(f"""
            CREATE TRIGGER idea_tags_delete_fts
            AFTER DELETE ON idea_tags
            BEGIN
                UPDATE {FTS_TABLE_NAME} SET
                    tags = (SELECT COALESCE(GROUP_CONCAT(t.name, ' '), '')
                            FROM tags t
                            JOIN idea_tags it ON t.id = it.tag_id
                            WHERE it.idea_id = OLD.idea_id)
                WHERE idea_id = OLD.idea_id;
            END
        """)  # nosec B608 - FTS_TABLE_NAME is a module constant, not user input
        )

        conn.commit()
        print("Created FTS sync triggers")


def drop_fts_setup() -> None:
    """Remove FTS table and triggers (for rollback)."""
    import logging

    with engine.connect() as conn:
        # Drop triggers
        for trigger_name in [
            "ideas_fts_insert",
            "ideas_fts_update",
            "ideas_fts_delete",
            "idea_tags_insert_fts",
            "idea_tags_delete_fts",
        ]:
            try:
                conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))  # nosec B608 - trigger_name is from a hardcoded list
            except Exception as e:
                # Ignore if trigger doesn't exist
                logging.debug(
                    f"Trigger {trigger_name} does not exist or could not be dropped: {e}"
                )

        # Drop FTS table
        try:
            conn.execute(text(f"DROP TABLE IF EXISTS {FTS_TABLE_NAME}"))  # nosec B608 - FTS_TABLE_NAME is a module constant
        except Exception as e:
            # Log error if table cannot be dropped
            logging.warning(f"Could not drop FTS table {FTS_TABLE_NAME}: {e}")

        conn.commit()
        print("Dropped FTS table and triggers")


def main() -> None:
    """Run the FTS5 setup migration."""
    print("Setting up SQLite FTS5 for idea search...")
    print("=" * 50)

    # Check FTS5 support
    if not check_fts5_support():
        print("ERROR: SQLite FTS5 is not available.")
        print("Please ensure your SQLite installation supports FTS5.")
        sys.exit(1)

    # Create table
    created = create_fts_table()

    if created:
        # Populate with existing data
        populate_fts_table()

        # Create sync triggers
        create_triggers()

    print("=" * 50)
    print("FTS5 setup complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SQLite FTS5 setup for idea search")
    parser.add_argument(
        "--rollback", action="store_true", help="Remove FTS table and triggers"
    )
    args = parser.parse_args()

    if args.rollback:
        drop_fts_setup()
    else:
        main()
