#!/usr/bin/env python3
"""
Service Layer HTTPException Checker.

Detects HTTPException usage in service layer files. Services should raise
domain exceptions (from models/exceptions.py), never FastAPI HTTPExceptions.
Exception handlers in main.py convert domain exceptions to HTTP responses.

Forbidden patterns in services:
- from fastapi import HTTPException
- from fastapi.exceptions import HTTPException
- raise HTTPException(...)

Usage:
    python scripts/check_service_http_exceptions.py
    python scripts/check_service_http_exceptions.py services/my_service.py

Exit codes:
    0 - No violations found
    1 - Violations found
"""

import ast
import sys
from pathlib import Path


SERVICE_DIR = Path("services")
EXCLUDED_FILES: set[str] = set()


class HTTPExceptionChecker(ast.NodeVisitor):
    """AST visitor to detect HTTPException usage in services."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []
        self.imports_http_exception = False

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for HTTPException imports."""
        if node.module in ("fastapi", "fastapi.exceptions"):
            for alias in node.names:
                if alias.name == "HTTPException":
                    self.violations.append(
                        (
                            node.lineno,
                            f"Import: from {node.module} import HTTPException",
                        )
                    )
                    self.imports_http_exception = True
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """Check for raise HTTPException(...)."""
        if node.exc is not None:
            if isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name):
                    if node.exc.func.id == "HTTPException":
                        self.violations.append(
                            (node.lineno, "raise HTTPException(...)")
                        )
                elif isinstance(node.exc.func, ast.Attribute):
                    if node.exc.func.attr == "HTTPException":
                        self.violations.append(
                            (node.lineno, "raise ...HTTPException(...)")
                        )
        self.generic_visit(node)


def check_file(filepath: Path) -> list[tuple[int, str]]:
    """Check a single file for violations."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content, str(filepath))
        checker = HTTPExceptionChecker(str(filepath))
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        print(f"  Syntax error in {filepath}: {e}")
        return []


def main() -> int:
    """Run the checker on all service files."""
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:]]
    else:
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

    if files_with_violations:
        print("=" * 70)
        print("ARCHITECTURE VIOLATION: HTTPException in service layer")
        print("=" * 70)
        print()
        print("Services must raise domain exceptions, not HTTPException.")
        print("Use exceptions from models/exceptions.py instead.")
        print()
        print("Examples:")
        print("  raise NotFoundException('User not found')")
        print("  raise PermissionDeniedException('Not authorized')")
        print("  raise ValidationException('Invalid input')")
        print()

        for filepath, violations in files_with_violations:
            print(f"  {filepath}:")
            for line, desc in violations:
                print(f"    Line {line}: {desc}")
            print()

        print(
            f"Total: {total_violations} violation(s) in {len(files_with_violations)} file(s)"
        )
        return 1

    print(f"No HTTPException usage in {len(files)} service file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
