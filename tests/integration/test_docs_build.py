"""
Integration test: verifies that mkdocs build completes without errors.

Catches:
- Nav references to non-existent files       → ERROR + returncode != 0
- mkdocstrings import errors (bad module)     → ERROR + returncode != 0
- i18n plugin misconfiguration               → ERROR + returncode != 0

Note: --strict is intentionally NOT used because mkdocs-static-i18n + mkdocstrings
produce known informational warnings (e.g. griffe docstring format hints,
autorefs duplicate anchors across i18n builds). These do not affect site correctness.
The build is considered healthy if returncode == 0 and no ERROR lines are present.
"""

import pathlib
import subprocess
import tempfile

import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


@pytest.mark.integration
def test_mkdocs_build_succeeds() -> None:
    """mkdocs build must complete with returncode 0 and no ERROR-level messages.

    If this test fails after a docs change, the CI docs deploy would also fail.
    Check the output below for which file/module caused the failure.
    """
    with tempfile.TemporaryDirectory() as tmp_site:
        result = subprocess.run(
            ["mkdocs", "build", "--site-dir", tmp_site],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

    combined = result.stdout + result.stderr
    error_lines = [line for line in combined.splitlines() if line.strip().startswith("ERROR")]

    assert result.returncode == 0, (
        f"mkdocs build failed (returncode={result.returncode}).\n\n"
        f"--- STDOUT ---\n{result.stdout}\n"
        f"--- STDERR ---\n{result.stderr}"
    )
    assert not error_lines, (
        "mkdocs build produced ERROR-level messages:\n"
        + "\n".join(error_lines)
        + f"\n\n--- Full output ---\n{combined}"
    )
