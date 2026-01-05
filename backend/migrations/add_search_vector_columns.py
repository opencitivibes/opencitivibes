"""
Migration: Add search_vector_en and search_vector_fr columns to ideas table.

This migration adds the full-text search vector columns to SQLite databases
that were created before the FTS feature was implemented.

For SQLite, these columns are just TEXT type (nullable) and are not used
for actual searching - SQLite uses FTS5 virtual tables instead.

Usage:
    cd backend
    uv run python -m migrations.add_search_vector_columns
"""

import sqlite3
import sys
from pathlib import Path


def migrate_sqlite(db_path: str) -> bool:
    """Add search vector columns to SQLite ideas table if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(ideas)")
        columns = {row[1] for row in cursor.fetchall()}

        columns_added = []

        if "search_vector_en" not in columns:
            cursor.execute("ALTER TABLE ideas ADD COLUMN search_vector_en TEXT")
            columns_added.append("search_vector_en")

        if "search_vector_fr" not in columns:
            cursor.execute("ALTER TABLE ideas ADD COLUMN search_vector_fr TEXT")
            columns_added.append("search_vector_fr")

        conn.commit()

        if columns_added:
            print(f"✓ Added columns: {', '.join(columns_added)}")
        else:
            print("✓ Columns already exist, no changes needed")

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def main() -> int:
    """Run the migration on the default database."""
    # Default database path
    db_path = Path(__file__).parent.parent / "data" / "idees_montreal.db"

    if not db_path.exists():
        print(f"✗ Database not found: {db_path}")
        return 1

    print(f"Migrating database: {db_path}")

    if migrate_sqlite(str(db_path)):
        print("Migration completed successfully!")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
