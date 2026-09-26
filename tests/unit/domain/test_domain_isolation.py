"""Integration verification test: Domain layer import boundary AST linter."""

import subprocess
import sys
from pathlib import Path


def test_domain_layer_has_zero_external_imports():
    """Verify that the AST import boundary linter reports 0 violations across all domain modules."""
    workspace_root = Path(__file__).resolve().parent.parent.parent.parent
    script_path = workspace_root / "scripts" / "lint_domain_imports.py"

    assert script_path.exists(), f"Linter script missing at {script_path}"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(workspace_root),
    )

    assert result.returncode == 0, f"Domain boundary linter failed:\n{result.stdout}\n{result.stderr}"
    assert "0 violations" in result.stdout
