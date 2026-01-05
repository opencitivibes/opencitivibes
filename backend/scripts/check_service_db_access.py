#!/usr/bin/env python3
"""
Service Layer Database Access Checker.

Detects direct database operations in service layer files that should go
through repositories instead. This enforces the Router → Service → Repository
architectural pattern.

Forbidden patterns in services:
- db.query()    - Should use repository methods
- db.add()      - Should use repository.create()
- db.delete()   - Should use repository.delete()
- db.commit()   - Repositories handle commits
- db.flush()    - Repositories handle flushes
- db.rollback() - Repositories handle rollbacks

Usage:
    python scripts/check_service_db_access.py
    python scripts/check_service_db_access.py services/my_service.py

Exit codes:
    0 - No violations found
    1 - Violations found
"""

import ast
import sys
from pathlib import Path

# Forbidden method calls on 'db' parameter
FORBIDDEN_DB_METHODS = {"query", "add", "delete", "commit", "flush", "rollback"}

# Service files to check (relative to backend/)
SERVICE_DIR = Path("services")

# Exclude these files (they have legitimate reasons for direct DB access)
EXCLUDED_FILES: set[str] = set()


class ServiceDBAccessChecker(ast.NodeVisitor):
    """AST visitor to detect direct DB operations in service methods."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.violations: list[tuple[int, str, str]] = []
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track current function for better error messages."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node: ast.Call) -> None:
        """Check for forbidden db.method() calls."""
        if isinstance(node.func, ast.Attribute):
            # Check for pattern: db.query(), db.add(), etc.
            if isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                method_name = node.func.attr

                if obj_name == "db" and method_name in FORBIDDEN_DB_METHODS:
                    self.violations.append(
                        (
                            node.lineno,
                            method_name,
                            self.current_function or "<module>",
                        )
                    )

        self.generic_visit(node)


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Check a single file for violations."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content, str(filepath))
        checker = ServiceDBAccessChecker(str(filepath))
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        print(f"  Syntax error in {filepath}: {e}")
        return []


def main() -> int:
    """Run the checker on all service files."""
    # Determine which files to check
    if len(sys.argv) > 1:
        # Check specific files
        files = [Path(f) for f in sys.argv[1:]]
    else:
        # Check all service files
        if not SERVICE_DIR.exists():
            print(f"Service directory not found: {SERVICE_DIR}")
            return 1
        files = list(SERVICE_DIR.glob("*.py"))

    files = [f for f in files if f.name not in EXCLUDED_FILES]

    if not files:
        print("No service files to check")
        return 0

    total_violations = 0
    files_with_violations = []

    for filepath in sorted(files):
        violations = check_file(filepath)
        if violations:
            files_with_violations.append((filepath, violations))
            total_violations += len(violations)

    # Report results
    if files_with_violations:
        print("=" * 70)
        print("ARCHITECTURE VIOLATION: Direct DB access in service layer")
        print("=" * 70)
        print()
        print("Services should use repositories for all database operations.")
        print("Move these operations to the appropriate repository.")
        print()

        for filepath, violations in files_with_violations:
            print(f"  {filepath}:")
            for line, method, function in violations:
                print(f"    Line {line}: db.{method}() in {function}()")
            print()

        print(
            f"Total: {total_violations} violation(s) in {len(files_with_violations)} file(s)"
        )
        print()
        print("Fix: Move db.query/add/delete/commit calls to repository methods")
        return 1

    print(f"✅ No direct DB access violations in {len(files)} service file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
