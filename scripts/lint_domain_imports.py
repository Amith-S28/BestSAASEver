#!/usr/bin/env python3
"""AST-based Domain Import Boundary Linter for MedRAG v2.0.

Scans all Python files in src/medrag/domain/ and enforces pure hexagonal isolation:
- ZERO external dependencies allowed.
- Permitted: Python standard library modules + internal medrag.domain modules.
- Banned: fastapi, pydantic, lancedb, torch, httpx, etc.

Exit code 0 on success; exit code 1 if any banned import is detected.
"""

import ast
import os
import sys
from pathlib import Path

# Explicitly permitted standard library root modules for clinical domain logic
ALLOWED_STDLIB_MODULES = {
    "dataclasses",
    "datetime",
    "enum",
    "typing",
    "uuid",
    "abc",
    "math",
    "re",
    "sys",
    "copy",
    "collections",
    "itertools",
    "functools",
    "decimal",
    "numbers",
}


def check_file(file_path: Path) -> list[str]:
    violations: list[str] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except Exception as e:
        return [f"Failed to parse {file_path}: {e}"]

    for node in ast.walk(tree):
        # Case 1: import foo, import foo.bar
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg == "medrag":
                    parts = alias.name.split(".")
                    if len(parts) < 2 or parts[1] != "domain":
                        violations.append(
                            f"{file_path}:{node.lineno}: Banned non-domain medrag import '{alias.name}'"
                        )
                elif root_pkg not in ALLOWED_STDLIB_MODULES:
                    violations.append(
                        f"{file_path}:{node.lineno}: Banned external import '{alias.name}' in domain layer"
                    )

        # Case 2: from foo import bar
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                # Relative import (e.g. from .exceptions import ... or from ..domain ...)
                # Within domain, relative imports are internal to domain.
                continue
            if node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg == "medrag":
                    parts = node.module.split(".")
                    if len(parts) < 2 or parts[1] != "domain":
                        violations.append(
                            f"{file_path}:{node.lineno}: Banned non-domain medrag import '{node.module}'"
                        )
                elif root_pkg not in ALLOWED_STDLIB_MODULES:
                    violations.append(
                        f"{file_path}:{node.lineno}: Banned external import '{node.module}' in domain layer"
                    )

    return violations


def main() -> int:
    workspace_root = Path(__file__).resolve().parent.parent
    domain_dir = workspace_root / "src" / "medrag" / "domain"

    if not domain_dir.exists():
        print(f"[ERROR] Domain directory not found at {domain_dir}")
        return 1

    all_violations: list[str] = []
    py_files = list(domain_dir.rglob("*.py"))

    if not py_files:
        print(f"[WARN] No python files found in {domain_dir}")
        return 0

    for py_file in py_files:
        violations = check_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        print("=" * 70)
        print("[FAIL] Domain Layer Boundary Violations Detected:")
        print("The domain layer must remain pure with zero external dependencies.")
        print("=" * 70)
        for v in all_violations:
            print(f"  ❌ {v}")
        print("=" * 70)
        return 1

    print(f"[SUCCESS] Domain layer boundary verified: {len(py_files)} files scanned, 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
