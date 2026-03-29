# Development & Validation Tools

This directory contains small wrappers around the shared `codex-core.dev` tooling used across Codex libraries.

## `check.py`

Project quality gate built on top of `codex_core.dev.check_runner.BaseCheckRunner`.

### Enabled stages

1. `pre-commit` hooks
2. `mypy`
3. `pip-audit`
4. unit tests
5. integration tests

`extra_checks()` is intentionally disabled for this repository because there are no project-specific stages beyond the shared baseline.

### Usage

- Show CLI help: `python tools/dev/check.py`
- Run developer flow: `python tools/dev/check.py --all`
- Run CI flow: `python tools/dev/check.py --ci`
- Run only unit tests: `python tools/dev/check.py --tests unit`
- Run only integration tests: `python tools/dev/check.py --tests integration`

Integration tests require Redis.

## `generate_project_tree.py`

Interactive wrapper around `codex_core.dev.project_tree.ProjectTreeGenerator` for generating `project_structure.txt`.
