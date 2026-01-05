"""Migration helper script

Usage:
    python scripts/migrate.py upgrade
    python scripts/migrate.py downgrade -1

This script is a convenience wrapper around Alembic's API so you can run
migrations from deployment scripts without depending on the alembic CLI.
"""

from __future__ import annotations

import sys
from alembic.config import Config
from alembic import command
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(ROOT / "alembic.ini")


def _get_config() -> Config:
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return cfg


def upgrade(rev: str = "head") -> None:
    cfg = _get_config()
    command.upgrade(cfg, rev)


def downgrade(rev: str = "-1") -> None:
    cfg = _get_config()
    command.downgrade(cfg, rev)


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    if len(argv) < 1:
        print("Usage: python scripts/migrate.py <upgrade|downgrade> [revision]")
        sys.exit(2)

    op = argv[0]
    rev = argv[1] if len(argv) > 1 else None

    if op == "upgrade":
        upgrade(rev or "head")
    elif op == "downgrade":
        downgrade(rev or "-1")
    else:
        print("Unknown operation. Use 'upgrade' or 'downgrade'")
        sys.exit(2)


if __name__ == "__main__":
    main()
