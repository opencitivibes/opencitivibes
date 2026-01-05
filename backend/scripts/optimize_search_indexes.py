#!/usr/bin/env python
"""Optimize search indexes for better performance.

This script provides utilities for managing and optimizing the search indexes
for both SQLite FTS5 and PostgreSQL backends.

Usage:
    python scripts/optimize_search_indexes.py [--optimize | --rebuild | --analyze | --info]

Options:
    --optimize  Optimize the FTS index (SQLite: run optimize, PostgreSQL: VACUUM ANALYZE)
    --rebuild   Rebuild the entire search index from scratch
    --analyze   Show index statistics and health
    --info      Show current backend configuration

Examples:
    # Show current backend info
    python scripts/optimize_search_indexes.py --info

    # Optimize the index
    python scripts/optimize_search_indexes.py --optimize

    # Full rebuild
    python scripts/optimize_search_indexes.py --rebuild

    # View statistics
    python scripts/optimize_search_indexes.py --analyze
"""

import argparse
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


from sqlalchemy import text  # noqa: E402

from models.config import get_settings  # noqa: E402
from repositories.database import SessionLocal  # noqa: E402
from services.search import SearchService  # noqa: E402


def get_database_type() -> str:
    """Determine database type from URL."""
    settings = get_settings()
    if settings.DATABASE_URL.startswith("postgresql"):
        return "postgresql"
    return "sqlite"


def optimize_sqlite_fts() -> None:
    """Optimize SQLite FTS5 index."""
    print("Optimizing SQLite FTS5 index...")
    db = SessionLocal()
    try:
        # Run FTS5 optimize command
        db.execute(text("INSERT INTO ideas_fts(ideas_fts) VALUES('optimize')"))
        db.commit()
        print("  SQLite FTS5 index optimized successfully")

        # Get index info
        result = db.execute(
            text("""
            SELECT COUNT(*) FROM ideas_fts
        """)
        )
        count = result.scalar() or 0
        print(f"  Indexed documents: {count}")
    except Exception as e:
        print(f"  Error optimizing SQLite FTS5: {e}")
        db.rollback()
    finally:
        db.close()


def optimize_postgresql_fts() -> None:
    """Optimize PostgreSQL FTS indexes."""
    print("Optimizing PostgreSQL FTS indexes...")
    db = SessionLocal()
    try:
        # Run ANALYZE on ideas table
        db.execute(text("ANALYZE ideas"))
        db.commit()
        print("  PostgreSQL statistics updated (ANALYZE)")

        # Optionally VACUUM ANALYZE for more thorough optimization
        # Note: VACUUM cannot run inside a transaction
        print("  Note: For full optimization, run 'VACUUM ANALYZE ideas' separately")
    except Exception as e:
        print(f"  Error optimizing PostgreSQL: {e}")
        db.rollback()
    finally:
        db.close()


def rebuild_index() -> None:
    """Rebuild the entire search index."""
    print("Rebuilding search index...")
    db = SessionLocal()
    try:
        count = SearchService.rebuild_index(db)
        print(f"  Successfully indexed {count} ideas")
    except Exception as e:
        print(f"  Error rebuilding index: {e}")
    finally:
        db.close()


def analyze_sqlite_fts() -> None:
    """Show SQLite FTS5 index statistics."""
    print("\nSQLite FTS5 Index Analysis")
    print("=" * 40)
    db = SessionLocal()
    try:
        # Check if FTS table exists
        result = db.execute(
            text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='ideas_fts'
        """)
        )
        if not result.fetchone():
            print("  FTS table 'ideas_fts' does not exist")
            return

        # Count indexed documents
        result = db.execute(text("SELECT COUNT(*) FROM ideas_fts"))
        fts_count = result.scalar() or 0
        print(f"  Indexed documents: {fts_count}")

        # Count total ideas
        result = db.execute(text("SELECT COUNT(*) FROM ideas"))
        total_count = result.scalar() or 0
        print(f"  Total ideas in database: {total_count}")

        if total_count > 0:
            coverage = (fts_count / total_count) * 100
            print(f"  Index coverage: {coverage:.1f}%")

        if fts_count != total_count:
            print("  WARNING: Index may be out of sync. Consider running --rebuild")

    except Exception as e:
        print(f"  Error analyzing index: {e}")
    finally:
        db.close()


def analyze_postgresql_fts() -> None:
    """Show PostgreSQL FTS index statistics."""
    print("\nPostgreSQL FTS Index Analysis")
    print("=" * 40)
    db = SessionLocal()
    try:
        # Check if search vector columns exist
        result = db.execute(
            text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'ideas'
            AND column_name IN ('search_vector_en', 'search_vector_fr')
        """)
        )
        columns = [row[0] for row in result.fetchall()]
        print(f"  Search vector columns: {', '.join(columns) or 'None'}")

        if len(columns) < 2:
            print("  WARNING: Missing search vector columns. Run migrations.")
            return

        # Count ideas with populated search vectors
        result = db.execute(
            text("""
            SELECT
                COUNT(*) as total,
                COUNT(search_vector_en) as en_indexed,
                COUNT(search_vector_fr) as fr_indexed
            FROM ideas
        """)
        )
        row = result.fetchone()
        if row:
            print(f"  Total ideas: {row[0]}")
            print(f"  English indexed: {row[1]}")
            print(f"  French indexed: {row[2]}")

        # Get index usage statistics
        result = db.execute(
            text("""
            SELECT
                indexrelname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            WHERE indexrelname LIKE '%search%'
        """)
        )

        print("\n  Index Usage Statistics:")
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"    {row[0]}: {row[1]} scans, {row[2]} tuples read")
        else:
            print("    No search indexes found")

    except Exception as e:
        print(f"  Error analyzing index: {e}")
    finally:
        db.close()


def show_backend_info() -> None:
    """Show current search backend configuration."""
    print("\nSearch Backend Information")
    print("=" * 40)
    settings = get_settings()
    db = SessionLocal()

    try:
        info = SearchService.get_backend_info(db)
        print(f"  Backend: {info.backend}")
        print(f"  Available: {info.available}")
        print(f"  Database URL: {settings.DATABASE_URL[:50]}...")
        print(f"  Min query length: {settings.SEARCH_MIN_QUERY_LENGTH}")
        print(f"  Max results: {settings.SEARCH_MAX_RESULTS}")
        print(f"  Freshness boost: {settings.SEARCH_FRESHNESS_BOOST}")
        print(f"  Popularity boost: {settings.SEARCH_POPULARITY_BOOST}")
    except Exception as e:
        print(f"  Error getting backend info: {e}")
    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Optimize search indexes for better performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--optimize", action="store_true", help="Optimize the search index"
    )
    parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild the entire search index"
    )
    parser.add_argument(
        "--analyze", action="store_true", help="Show index statistics and health"
    )
    parser.add_argument(
        "--info", action="store_true", help="Show backend configuration"
    )

    args = parser.parse_args()

    # Default to showing info if no arguments
    if not any([args.optimize, args.rebuild, args.analyze, args.info]):
        args.info = True

    db_type = get_database_type()
    print(f"Database type: {db_type}")

    if args.info:
        show_backend_info()

    if args.analyze:
        if db_type == "postgresql":
            analyze_postgresql_fts()
        else:
            analyze_sqlite_fts()

    if args.optimize:
        if db_type == "postgresql":
            optimize_postgresql_fts()
        else:
            optimize_sqlite_fts()

    if args.rebuild:
        rebuild_index()

    print("\nDone.")


if __name__ == "__main__":
    main()
