"""Quality gate for codex-platform."""

from pathlib import Path

from codex_core.dev.check_runner import BaseCheckRunner


class CheckRunner(BaseCheckRunner):
    """Thin launcher; project policy lives in pyproject.toml."""


if __name__ == "__main__":
    import os

    os.system("cls" if os.name == "nt" else "clear")
    CheckRunner(Path(__file__).parent.parent.parent).main()
