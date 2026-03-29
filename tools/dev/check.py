"""Quality gate for codex-platform."""

from pathlib import Path

from codex_core.dev.check_runner import BaseCheckRunner


class CheckRunner(BaseCheckRunner):
    PROJECT_NAME = "codex-platform"
    INTEGRATION_REQUIRES = "Redis"
    RUN_LINT = True
    RUN_TYPES = True
    RUN_SECURITY = True
    RUN_EXTRA_CHECKS = False
    RUN_UNIT_TESTS = True
    RUN_INTEGRATION_TESTS = True
    # CVE-2026-4539: pygments — no fix available yet (latest version)
    AUDIT_FLAGS = "--skip-editable --ignore-vuln CVE-2026-4539"


if __name__ == "__main__":
    CheckRunner(Path(__file__).parent.parent.parent).main()
