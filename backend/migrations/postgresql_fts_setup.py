#!/usr/bin/env python3
"""
PostgreSQL Full-Text Search setup migration.

This script sets up PostgreSQL-specific FTS features:
1. Adds tsvector columns for English and French search
2. Creates GIN indexes for fast searching
3. Creates trigger function to auto-update search vectors
4. Attaches triggers to the ideas table
5. Populates existing ideas with search vectors

Usage:
    python migrations/postgresql_fts_setup.py           # Apply migration
    python migrations/postgresql_fts_setup.py --check   # Check if already applied
    python migrations/postgresql_fts_setup.py --rollback # Remove FTS setup

This script is idempotent - safe to run multiple times.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session

from repositories.database import SessionLocal, engine


def is_postgresql() -> bool:
    """Check if the database is PostgreSQL."""
    return str(engine.url).startswith("postgresql")


def check_fts_setup(db: Session) -> dict:
    """Check the current state of FTS setup."""
    status = {
        "columns_exist": False,
        "indexes_exist": False,
        "trigger_function_exists": False,
        "triggers_exist": False,
        "ideas_indexed": 0,
    }

    if not is_postgresql():
        return status

    # Check columns
    result = db.execute(
        text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'ideas'
        AND column_name IN ('search_vector_en', 'search_vector_fr')
    """)
    )
    columns = [row[0] for row in result.fetchall()]
    status["columns_exist"] = len(columns) == 2

    # Check indexes
    result = db.execute(
        text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'ideas'
        AND indexname IN ('idx_ideas_search_en', 'idx_ideas_search_fr')
    """)
    )
    indexes = [row[0] for row in result.fetchall()]
    status["indexes_exist"] = len(indexes) == 2

    # Check trigger function
    result = db.execute(
        text("""
        SELECT proname
        FROM pg_proc
        WHERE proname = 'ideas_search_vector_update'
    """)
    )
    status["trigger_function_exists"] = result.fetchone() is not None

    # Check triggers
    result = db.execute(
        text("""
        SELECT tgname
        FROM pg_trigger
        WHERE tgname IN ('ideas_search_vector_trigger', 'idea_tags_search_update_insert',
                         'idea_tags_search_update_delete')
    """)
    )
    triggers = [row[0] for row in result.fetchall()]
    status["triggers_exist"] = len(triggers) >= 1

    # Count indexed ideas
    if status["columns_exist"]:
        result = db.execute(
            text("""
            SELECT COUNT(*)
            FROM ideas
            WHERE search_vector_en IS NOT NULL
        """)
        )
        status["ideas_indexed"] = result.scalar() or 0

    return status


def add_columns(db: Session) -> None:
    """Add tsvector columns if they don't exist."""
    print("Adding tsvector columns...")

    # Check if columns already exist
    result = db.execute(
        text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'ideas'
        AND column_name = 'search_vector_en'
    """)
    )
    if result.fetchone() is not None:
        print("  Columns already exist, skipping.")
        return

    # Add English search vector column
    db.execute(
        text("""
        ALTER TABLE ideas
        ADD COLUMN IF NOT EXISTS search_vector_en tsvector
    """)
    )

    # Add French search vector column
    db.execute(
        text("""
        ALTER TABLE ideas
        ADD COLUMN IF NOT EXISTS search_vector_fr tsvector
    """)
    )

    db.commit()
    print("  Columns added successfully.")


def create_indexes(db: Session) -> None:
    """Create GIN indexes for fast searching."""
    print("Creating GIN indexes...")

    # Check if indexes exist
    result = db.execute(
        text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'ideas'
        AND indexname = 'idx_ideas_search_en'
    """)
    )
    if result.fetchone() is not None:
        print("  Indexes already exist, skipping.")
        return

    # Create GIN index for English
    db.execute(
        text("""
        CREATE INDEX IF NOT EXISTS idx_ideas_search_en
        ON ideas USING GIN(search_vector_en)
    """)
    )

    # Create GIN index for French
    db.execute(
        text("""
        CREATE INDEX IF NOT EXISTS idx_ideas_search_fr
        ON ideas USING GIN(search_vector_fr)
    """)
    )

    db.commit()
    print("  GIN indexes created successfully.")


def create_trigger_function(db: Session) -> None:
    """Create the trigger function for auto-updating search vectors."""
    print("Creating trigger function...")

    # Drop existing function to ensure it's up to date
    db.execute(
        text("""
        DROP FUNCTION IF EXISTS ideas_search_vector_update() CASCADE
    """)
    )

    # Create the trigger function
    db.execute(
        text("""
        CREATE OR REPLACE FUNCTION ideas_search_vector_update() RETURNS trigger AS $$
        DECLARE
            tag_text TEXT;
        BEGIN
            -- Get concatenated tags for this idea
            SELECT STRING_AGG(t.name, ' ') INTO tag_text
            FROM tags t
            JOIN idea_tags it ON t.id = it.tag_id
            WHERE it.idea_id = NEW.id;

            -- Update English search vector with weights
            -- A = title (highest), B = description, C = tags (lowest)
            NEW.search_vector_en :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(tag_text, '')), 'C');

            -- Update French search vector with weights
            NEW.search_vector_fr :=
                setweight(to_tsvector('french', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('french', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('french', COALESCE(tag_text, '')), 'C');

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    )

    db.commit()
    print("  Trigger function created successfully.")


def create_triggers(db: Session) -> None:
    """Create triggers to auto-update search vectors."""
    print("Creating triggers...")

    # Drop existing triggers
    db.execute(
        text("""
        DROP TRIGGER IF EXISTS ideas_search_vector_trigger ON ideas
    """)
    )
    db.execute(
        text("""
        DROP TRIGGER IF EXISTS idea_tags_search_update_insert ON idea_tags
    """)
    )
    db.execute(
        text("""
        DROP TRIGGER IF EXISTS idea_tags_search_update_delete ON idea_tags
    """)
    )

    # Create trigger on ideas table for INSERT and UPDATE
    db.execute(
        text("""
        CREATE TRIGGER ideas_search_vector_trigger
            BEFORE INSERT OR UPDATE ON ideas
            FOR EACH ROW
            EXECUTE FUNCTION ideas_search_vector_update()
    """)
    )

    # Create function to update idea search vectors when tags change
    db.execute(
        text("""
        DROP FUNCTION IF EXISTS update_idea_search_on_tag_change() CASCADE
    """)
    )
    db.execute(
        text("""
        CREATE OR REPLACE FUNCTION update_idea_search_on_tag_change() RETURNS trigger AS $$
        DECLARE
            affected_idea_id INT;
            tag_text TEXT;
        BEGIN
            -- Get the affected idea ID (handle both INSERT and DELETE)
            affected_idea_id := COALESCE(NEW.idea_id, OLD.idea_id);

            -- Get concatenated tags for this idea
            SELECT STRING_AGG(t.name, ' ') INTO tag_text
            FROM tags t
            JOIN idea_tags it ON t.id = it.tag_id
            WHERE it.idea_id = affected_idea_id;

            -- Directly update the search vectors with new tag text
            UPDATE ideas
            SET search_vector_en = (
                setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(tag_text, '')), 'C')
            ),
            search_vector_fr = (
                setweight(to_tsvector('french', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('french', COALESCE(description, '')), 'B') ||
                setweight(to_tsvector('french', COALESCE(tag_text, '')), 'C')
            )
            WHERE id = affected_idea_id;

            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)
    )

    # Create triggers for idea_tags changes
    db.execute(
        text("""
        CREATE TRIGGER idea_tags_search_update_insert
            AFTER INSERT ON idea_tags
            FOR EACH ROW
            EXECUTE FUNCTION update_idea_search_on_tag_change()
    """)
    )
    db.execute(
        text("""
        CREATE TRIGGER idea_tags_search_update_delete
            AFTER DELETE ON idea_tags
            FOR EACH ROW
            EXECUTE FUNCTION update_idea_search_on_tag_change()
    """)
    )

    db.commit()
    print("  Triggers created successfully.")


def populate_search_vectors(db: Session) -> int:
    """Populate search vectors for existing ideas."""
    print("Populating search vectors for existing ideas...")

    # Count ideas
    result = db.execute(text("SELECT COUNT(*) FROM ideas"))
    total_ideas = result.scalar() or 0

    if total_ideas == 0:
        print("  No ideas to index.")
        return 0

    # Update all ideas to trigger the search vector population
    # This uses a more efficient batch update
    db.execute(
        text("""
        UPDATE ideas
        SET search_vector_en = (
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(
                (SELECT STRING_AGG(t.name, ' ')
                 FROM tags t
                 JOIN idea_tags it ON t.id = it.tag_id
                 WHERE it.idea_id = ideas.id), ''
            )), 'C')
        ),
        search_vector_fr = (
            setweight(to_tsvector('french', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('french', COALESCE(description, '')), 'B') ||
            setweight(to_tsvector('french', COALESCE(
                (SELECT STRING_AGG(t.name, ' ')
                 FROM tags t
                 JOIN idea_tags it ON t.id = it.tag_id
                 WHERE it.idea_id = ideas.id), ''
            )), 'C')
        )
    """)
    )

    db.commit()
    print(f"  Indexed {total_ideas} ideas.")
    return total_ideas


def apply_migration(db: Session) -> None:
    """Apply the full FTS migration."""
    print("\n=== PostgreSQL Full-Text Search Setup ===\n")

    if not is_postgresql():
        print("ERROR: This migration is only for PostgreSQL databases.")
        print(f"Current database: {engine.url}")
        sys.exit(1)

    # Run all setup steps
    add_columns(db)
    create_indexes(db)
    create_trigger_function(db)
    create_triggers(db)
    count = populate_search_vectors(db)

    print(f"\n=== Migration complete! {count} ideas indexed. ===\n")


def rollback_migration(db: Session) -> None:
    """Remove all FTS setup."""
    print("\n=== Rolling back PostgreSQL FTS Setup ===\n")

    if not is_postgresql():
        print("ERROR: This migration is only for PostgreSQL databases.")
        sys.exit(1)

    print("Dropping triggers...")
    db.execute(text("DROP TRIGGER IF EXISTS ideas_search_vector_trigger ON ideas"))
    db.execute(
        text("DROP TRIGGER IF EXISTS idea_tags_search_update_insert ON idea_tags")
    )
    db.execute(
        text("DROP TRIGGER IF EXISTS idea_tags_search_update_delete ON idea_tags")
    )

    print("Dropping trigger functions...")
    db.execute(text("DROP FUNCTION IF EXISTS ideas_search_vector_update() CASCADE"))
    db.execute(
        text("DROP FUNCTION IF EXISTS update_idea_search_on_tag_change() CASCADE")
    )

    print("Dropping indexes...")
    db.execute(text("DROP INDEX IF EXISTS idx_ideas_search_en"))
    db.execute(text("DROP INDEX IF EXISTS idx_ideas_search_fr"))

    print("Dropping columns...")
    db.execute(text("ALTER TABLE ideas DROP COLUMN IF EXISTS search_vector_en"))
    db.execute(text("ALTER TABLE ideas DROP COLUMN IF EXISTS search_vector_fr"))

    db.commit()
    print("\n=== Rollback complete! ===\n")


def print_status(status: dict) -> None:
    """Print the current FTS setup status."""
    print("\n=== PostgreSQL FTS Status ===\n")
    print(f"  tsvector columns:    {'YES' if status['columns_exist'] else 'NO'}")
    print(f"  GIN indexes:         {'YES' if status['indexes_exist'] else 'NO'}")
    print(
        f"  Trigger function:    {'YES' if status['trigger_function_exists'] else 'NO'}"
    )
    print(f"  Triggers attached:   {'YES' if status['triggers_exist'] else 'NO'}")
    print(f"  Ideas indexed:       {status['ideas_indexed']}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="PostgreSQL FTS Setup Migration")
    parser.add_argument(
        "--check", action="store_true", help="Check current FTS setup status"
    )
    parser.add_argument("--rollback", action="store_true", help="Remove FTS setup")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.check:
            if not is_postgresql():
                print("Not a PostgreSQL database - FTS not applicable.")
                return
            status = check_fts_setup(db)
            print_status(status)
        elif args.rollback:
            rollback_migration(db)
        else:
            apply_migration(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
