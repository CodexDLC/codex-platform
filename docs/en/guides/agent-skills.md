# Agent skill installer

Starting in version 0.6.0, `codex-platform` includes an optional offline consumer skill. The package owns its source in `codex_platform.agent_skills.resources`; installation copies it into an existing project at `.agents/skills/codex-platform/` and adds a bounded reference block to that project's root `AGENTS.md`. Runtime use of the library does not require installing the skill.

Use the Python environment containing `codex-platform`:

```bash
python -m codex_platform.agent_skills install --project /path/to/project
python -m codex_platform.agent_skills status --project /path/to/project
python -m codex_platform.agent_skills update --project /path/to/project
python -m codex_platform.agent_skills delete --project /path/to/project
```

`--project` must name an existing directory. `install` is idempotent for a current installation. After a package upgrade, `status` reports that the copy needs an update; run `update` to refresh it. `status` exits with code 0 only when the installed version, payload hashes, and `AGENTS.md` block are current. Absence, edits, or corruption return code 1.

The installer tracks owned file hashes and the package version in `.agents/skills/codex-platform/.manifest.json`. It preserves unrelated `AGENTS.md` text and unowned files under the skill directory. `update` and `delete` refuse to change locally edited or missing managed files. If that happens, back up the changed files, move custom guidance into a separate project skill, and restore the original managed bytes from the same installed package version before retrying. For a damaged marker, back up `AGENTS.md` and repair the bounded block from the installer documentation before retrying. Do not edit the manifest hashes to accept changes. Unowned path collisions, malformed manifests or markers, symlinks, and Windows reparse points also stop the operation. Writes are staged with best-effort rollback for ordinary errors; this is not a crash-safe multi-file transaction or a concurrency lock.

The managed block is exactly the following four lines (with the project's line endings); the separator value is `0` when the block did not need a leading newline and `1` when it did:

```markdown
<!-- codex-platform:skill:start -->
<!-- codex-platform:skill:separator=0 -->
Use [codex-platform](.agents/skills/codex-platform/SKILL.md) for codex_platform work.
<!-- codex-platform:skill:end -->
```

The installed skill guides use of the public Redis, Streams, ARQ, and messaging APIs. It does not own a consumer's business rules, data keys, service adapters, or runtime configuration.
