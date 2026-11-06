# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Vendor decoupling is enforced, not just intended.

Anything that talks to Clerk / Stripe / a JWT library lives in ``app/adapters``. The domain,
the API and the database schema must stay free of vendor names, so swapping a provider means
writing one adapter and changing configuration.
"""
import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"
VENDOR_MODULES = {"stripe", "jwt", "svix", "clerk", "clerk_backend_api", "auth0"}
VENDOR_WORDS = re.compile(r"\b(stripe|clerk|auth0|supabase|paddle|lemonsqueezy)\b", re.I)


def _python_files(*, outside_adapters: bool):
    for path in APP.rglob("*.py"):
        in_adapters = "adapters" in path.relative_to(APP).parts
        if in_adapters != outside_adapters:
            yield path


def _imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def test_vendor_sdks_are_only_imported_by_adapters():
    offenders = {str(p.relative_to(APP)): sorted(_imports(p) & VENDOR_MODULES)
                 for p in _python_files(outside_adapters=True) if _imports(p) & VENDOR_MODULES}
    assert offenders == {}


def test_domain_never_imports_adapters_directly():
    """Only the composition root may name concrete adapters."""
    allowed = {"bootstrap.py"}
    offenders = []
    for path in _python_files(outside_adapters=True):
        if path.name in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("app.adapters"):
                offenders.append(str(path.relative_to(APP)))
    assert offenders == []


def test_database_schema_has_no_vendor_columns():
    from app.db.models import Base
    names = [f"{t.name}.{c.name}" for t in Base.metadata.tables.values() for c in t.columns]
    names += list(Base.metadata.tables)
    assert [n for n in names if VENDOR_WORDS.search(n)] == []


def test_ports_and_domain_do_not_mention_vendors_in_code():
    """Vendor names may appear in config (it selects the adapter) and in docs, not in domain logic."""
    checked = [APP / "ports", APP / "services", APP / "api", APP / "db"]
    hits = []
    for base in checked:
        for path in base.rglob("*.py"):
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#")[0]
                if VENDOR_WORDS.search(code) and '"""' not in code:
                    hits.append(f"{path.relative_to(APP)}:{n}: {line.strip()}")
    # docstrings may explain the design, string literals in code may not
    assert [h for h in hits if '"' in h.split(":", 2)[2] or "'" in h.split(":", 2)[2]] == []
