"""
Migration: Add deleted_at, deleted_by, deletion_reason columns to ideas table.

Run this if your database was created before soft-delete fields were added.

Usage:
    cd backend
    uv run python -m migrations.add_deleted_columns
"""

import sqlite3
import sys
from pathlib import Path


def migrate_sqlite(db_path: str) -> bool:
    """Add deleted columns to SQLite ideas table if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(ideas)")
        columns = {row[1] for row in cursor.fetchall()}

        columns_added = []

        if "deleted_at" not in columns:
            cursor.execute("ALTER TABLE ideas ADD COLUMN deleted_at DATETIME")
            columns_added.append("deleted_at")

        if "deleted_by" not in columns:
            cursor.execute("ALTER TABLE ideas ADD COLUMN deleted_by INTEGER")
            columns_added.append("deleted_by")

        if "deletion_reason" not in columns:
            cursor.execute("ALTER TABLE ideas ADD COLUMN deletion_reason TEXT")
            columns_added.append("deletion_reason")

        # Ensure index on deleted_at for fast lookups
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_ideas_deleted_at ON ideas (deleted_at)"
        )

        conn.commit()

        if columns_added:
            print(f"✓ Added columns: {', '.join(columns_added)}")
        else:
            print("✓ Deleted columns already exist, no changes needed")

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def main() -> int:
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
