"""
Migration script to add Tag and IdeaTag tables to existing database.
Run this script if you have an existing database and need to add tag functionality.
For new databases, the tables will be created automatically by init_db.py
"""

from sqlalchemy import text
from repositories.database import SessionLocal


def migrate():
    """Add tags and idea_tags tables to existing database"""
    db = SessionLocal()

    try:
        # Check if tables already exist
        check_query = text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('tags', 'idea_tags')
        """)
        result = db.execute(check_query)
        existing_tables = [row[0] for row in result]

        if "tags" in existing_tables and "idea_tags" in existing_tables:
            print("[INFO] Tag tables already exist. Migration not needed.")
            return

        print("[INFO] Creating tag tables...")

        # Create tags table
        if "tags" not in existing_tables:
            create_tags = text("""
                CREATE TABLE tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    display_name VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(create_tags)

            # Create index on tag name
            create_index = text("CREATE INDEX ix_tags_name ON tags (name)")
            db.execute(create_index)
            print("[OK] Tags table created")

        # Create idea_tags junction table
        if "idea_tags" not in existing_tables:
            create_idea_tags = text("""
                CREATE TABLE idea_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idea_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (idea_id) REFERENCES ideas (id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id),
                    UNIQUE (idea_id, tag_id)
                )
            """)
            db.execute(create_idea_tags)
            print("[OK] IdeaTags table created")

        db.commit()
        print("\n[OK] Tag tables migration complete!")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Tag Tables Migration Script")
    print("=" * 60)
    migrate()
