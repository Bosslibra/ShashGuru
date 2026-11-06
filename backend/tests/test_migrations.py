# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""The Alembic migrations must build exactly the schema the models describe."""
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.db.models import Base

BACKEND = Path(__file__).resolve().parent.parent


def test_migrations_match_the_models(tmp_path):
    db_file = tmp_path / "m.db"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", f"url=sqlite+aiosqlite:///{db_file}", "upgrade", "head"],
        cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)
    engine.dispose()
    assert diff == [], f"models and migrations have drifted: {diff}"


def test_migrations_are_reversible(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'r.db'}"
    for command in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        result = subprocess.run([sys.executable, "-m", "alembic", "-x", f"url={url}", *command],
                                cwd=BACKEND, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

