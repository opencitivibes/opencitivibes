#!/usr/bin/env python3
"""
Layer Import Boundary Checker.

Enforces the layered architecture by detecting forbidden cross-layer imports.

Architecture layers (top to bottom):
  routers -> services -> repositories -> models

Import rules:
  - Routers: CAN import services, models, helpers, authentication
            CANNOT import repositories directly
  - Services: CAN import repositories, models, helpers
              CANNOT import routers
  - Repositories: CAN import models
                  CANNOT import services or routers

Usage:
    python scripts/check_layer_imports.py
    python scripts/check_layer_imports.py routers/my_router.py

Exit codes:
    0 - No violations found
    1 - Violations found
"""

import ast
import sys
from pathlib import Path

# Define forbidden imports for each layer
LAYER_RULES: dict[str, dict[str, list[str] | str]] = {
    "routers": {
        "forbidden": ["repositories"],
        "reason": "Routers must use services, not repositories directly",
    },
    "services": {
        "forbidden": ["routers"],
        "reason": "Services cannot depend on routers (wrong direction)",
    },
    "repositories": {
        "forbidden": ["routers", "services"],
        "reason": "Repositories cannot depend on higher layers",
    },
}

# These repository modules are allowed in routers (infrastructure, not business logic)
ALLOWED_REPO_IMPORTS = {
    "repositories.database",  # get_db dependency injection
    "repositories.db_models",  # Type hints for SQLAlchemy models
}

# Specific repository classes that are FORBIDDEN in routers
# (importing the class directly means bypassing the service layer)
FORBIDDEN_REPO_CLASSES = {
    "Repository",  # Any class ending in Repository
}


class LayerImportChecker(ast.NodeVisitor):
    """AST visitor to detect forbidden layer imports."""

    def __init__(self, filepath: str, layer: str, forbidden: list[str]) -> None:
        self.filepath = filepath
        self.layer = layer
        self.forbidden = forbidden
        self.violations: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Check regular imports."""
        for alias in node.names:
            self._check_import(node.lineno, alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from...import statements."""
        if node.module:
            self._check_import(node.lineno, node.module)
        self.generic_visit(node)

    def _check_import(self, lineno: int, module: str) -> None:
        """Check if an import violates layer boundaries."""
        for forbidden_layer in self.forbidden:
            # Check if importing from forbidden layer
            if module.startswith(f"{forbidden_layer}.") or module == forbidden_layer:
                # Allow specific infrastructure imports
                if module in ALLOWED_REPO_IMPORTS:
                    continue
                self.violations.append((lineno, f"import from '{module}'"))


def get_layer(filepath: Path) -> str | None:
    """Determine which layer a file belongs to."""
    parts = filepath.parts
    for layer in LAYER_RULES:
        if layer in parts:
            return layer
    return None


def check_file(filepath: Path) -> list[tuple[int, str]]:
    """Check a single file for layer import violations."""
    layer = get_layer(filepath)
    if layer is None or layer not in LAYER_RULES:
        return []

    rules = LAYER_RULES[layer]
    forbidden = rules["forbidden"]

    if not forbidden:
        return []

    try:
        content = filepath.read_text()
        tree = ast.parse(content, str(filepath))
        checker = LayerImportChecker(str(filepath), layer, forbidden)
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        print(f"  Syntax error in {filepath}: {e}")
        return []


def main() -> int:
    """Run the checker on all layer files."""
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:]]
    else:
        # Check all Python files in layer directories
        files = []
        for layer in LAYER_RULES:
            layer_dir = Path(layer)
            if layer_dir.exists():
                files.extend(layer_dir.glob("**/*.py"))

    # Filter out __init__.py and test files
    files = [f for f in files if f.name != "__init__.py" and "test" not in str(f)]

    if not files:
        print("No files to check")
        return 0

    total_violations = 0
    files_with_violations = []

    for filepath in sorted(files):
        violations = check_file(filepath)
        if violations:
            layer = get_layer(filepath)
            files_with_violations.append((filepath, layer, violations))
            total_violations += len(violations)

    if files_with_violations:
        print("=" * 70)
        print("ARCHITECTURE VIOLATION: Forbidden cross-layer imports")
        print("=" * 70)
        print()
        print("Layer hierarchy: routers -> services -> repositories -> models")
        print()

        for filepath, layer, violations in files_with_violations:
            reason = LAYER_RULES[layer]["reason"] if layer else "Unknown"
            print(f"  {filepath} ({layer}):")
            print(f"    Rule: {reason}")
            for line, desc in violations:
                print(f"    Line {line}: {desc}")
            print()

        print(
            f"Total: {total_violations} violation(s) in {len(files_with_violations)} file(s)"
        )
        return 1

    print(f"No layer import violations in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
