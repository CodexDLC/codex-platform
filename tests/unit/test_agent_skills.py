"""Offline installer lifecycle and safety boundaries."""

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from codex_platform.agent_skills.cli import main
from codex_platform.agent_skills.fs_transaction import FSError, FSTransaction, check_regular_file, validate_no_symlinks
from codex_platform.agent_skills.manifest_rules import (
    MANIFEST_NAME,
    MARKER_END,
    MARKER_START,
    ManifestError,
    build_manifest,
    parse_manifest,
    update_agents_md_bytes,
    validate_normalized_posix_path,
)
from codex_platform.agent_skills.orchestrator import (
    OrchestratorError,
    check_status,
    get_payload_files,
    perform_delete,
    perform_install,
)

pytestmark = pytest.mark.unit
PAYLOAD = {"SKILL.md": b"# Skill\n", "references/redis.md": b"# Redis\n"}


def skill_dir(project: Path) -> Path:
    return project / ".agents/skills/codex-platform"


def test_install_update_status_delete_preserve_user_content(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    original = b"\xef\xbb\xbf# Local rules\r\nKeep this.\r\n"
    agents.write_bytes(original)
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
        perform_install(tmp_path)
        assert check_status(tmp_path) == (True, "Installed and up to date.")
    installed = skill_dir(tmp_path)
    assert parse_manifest((installed / MANIFEST_NAME).read_bytes())["skill"] == "codex-platform"
    (installed / "my-notes.md").write_text("local", encoding="utf-8")
    changed = {"SKILL.md": b"# New\n", "references/streams.md": b"# Streams\n"}
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=changed):
        assert check_status(tmp_path)[0] is False
        perform_install(tmp_path, update=True)
        assert check_status(tmp_path)[0] is True
    assert not (installed / "references/redis.md").exists()
    assert (installed / "my-notes.md").read_text(encoding="utf-8") == "local"
    perform_delete(tmp_path)
    assert agents.read_bytes() == original
    assert (installed / "my-notes.md").exists()


def test_created_agents_file_removed_only_when_empty(tmp_path: Path) -> None:
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    perform_delete(tmp_path)
    assert not (tmp_path / "AGENTS.md").exists()
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    agents = tmp_path / "AGENTS.md"
    agents.write_bytes(agents.read_bytes() + b"# My rules\n")
    perform_delete(tmp_path)
    assert agents.read_bytes() == b"# My rules\n"


@pytest.mark.parametrize("action", ["update", "delete"])
def test_local_edits_refuse_mutation(tmp_path: Path, action: str) -> None:
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    target = skill_dir(tmp_path) / "SKILL.md"
    target.write_bytes(b"local edit")
    before = (tmp_path / "AGENTS.md").read_bytes()
    with pytest.raises(OrchestratorError, match="edited or removed"):
        if action == "update":
            perform_install(tmp_path, update=True)
        else:
            perform_delete(tmp_path)
    assert target.read_bytes() == b"local edit"
    assert (tmp_path / "AGENTS.md").read_bytes() == before


def test_collision_and_corrupt_marker_refuse_mutation(tmp_path: Path) -> None:
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    installed = skill_dir(tmp_path)
    (installed / "new.md").write_text("mine", encoding="utf-8")
    expanded = {**PAYLOAD, "new.md": b"managed"}
    with (
        patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=expanded),
        pytest.raises(OrchestratorError, match="colliding"),
    ):
        perform_install(tmp_path, update=True)
    agents = tmp_path / "AGENTS.md"
    agents.write_bytes(agents.read_bytes().replace(MARKER_START, b"<!-- broken:start -->"))
    with pytest.raises(OrchestratorError, match="Corrupt AGENTS.md block"):
        perform_delete(tmp_path)
    assert (installed / "SKILL.md").read_bytes() == PAYLOAD["SKILL.md"]


@pytest.mark.parametrize("bad", ["../escape", "/absolute", "a//b", "CON.txt", "a/..", "a\\b", "a:thing"])
def test_manifest_rejects_unsafe_paths(bad: str) -> None:
    with pytest.raises(ManifestError):
        validate_normalized_posix_path(bad)


def test_manifest_rejects_duplicate_key_and_invalid_hash() -> None:
    bad = (
        b'{"version":"1.0","skill":"codex-platform","package_version":"1",'
        b'"agents_created":false,"files":{"SKILL.md":"x","SKILL.md":"y"}}'
    )
    with pytest.raises(ManifestError):
        parse_manifest(bad)
    data = json.loads(bad.decode())
    with pytest.raises(ManifestError):
        parse_manifest(json.dumps(data).encode())


def test_marker_round_trip_preserves_unrelated_bytes() -> None:
    original = b"\xef\xbb\xbf# Rules\r\nNo final newline"
    marked = update_agents_md_bytes(original)
    assert update_agents_md_bytes(marked, remove=True) == original
    with pytest.raises(ManifestError):
        update_agents_md_bytes(marked + MARKER_START)


def test_symlink_target_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    (tmp_path / ".agents/skills").mkdir(parents=True)
    try:
        (tmp_path / ".agents/skills/codex-platform").symlink_to(outside, target_is_directory=False)
    except OSError:
        pytest.skip("Symlink creation unavailable")
    with pytest.raises(FSError, match="Symlink or reparse"):
        perform_install(tmp_path)
    assert outside.read_text(encoding="utf-8") == "outside"


def test_failed_write_rolls_back(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_bytes(b"# Existing\n")
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    installed = skill_dir(tmp_path)
    before = {p: p.read_bytes() for p in [installed / "SKILL.md", installed / MANIFEST_NAME, tmp_path / "AGENTS.md"]}
    original_replace = os.replace
    failed = False

    def fail_once(src: Path, dst: Path) -> None:
        nonlocal failed
        if dst.name == "AGENTS.md" and not failed:
            failed = True
            raise OSError("injected write failure")
        original_replace(src, dst)

    with (
        patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value={"SKILL.md": b"new"}),
        patch("os.replace", side_effect=fail_once),
        pytest.raises(FSError, match="rolled back"),
    ):
        perform_install(tmp_path, update=True)
    assert all(path.read_bytes() == content for path, content in before.items())
    assert (installed / "references/redis.md").read_bytes() == PAYLOAD["references/redis.md"]


def test_cli_requires_existing_project(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["install", "--project", str(tmp_path / "absent")])
    assert exc.value.code == 1
    assert "does not exist" in capsys.readouterr().err


def test_packaged_payload_and_cli_lifecycle(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    payload = get_payload_files()
    assert "SKILL.md" in payload
    assert "references/messaging.md" in payload
    assert b"codex_platform.messaging" in payload["references/messaging.md"]
    with pytest.raises(SystemExit) as absent:
        main(["status", "--project", str(tmp_path)])
    assert absent.value.code == 1
    assert "Not installed" in capsys.readouterr().out
    for action in ("install", "status", "update", "delete"):
        main([action, "--project", str(tmp_path)])
    assert "Deleted successfully" in capsys.readouterr().out
    with pytest.raises(SystemExit) as missing:
        main(["update", "--project", str(tmp_path)])
    assert missing.value.code == 1
    assert "Not installed" in capsys.readouterr().err


def test_messaging_reference_example_runs() -> None:
    reference = get_payload_files()["references/messaging.md"].decode("utf-8")
    example = reference.split("```python\n", 1)[1].split("\n```", 1)[0]
    exec(compile(example, "messaging.md", "exec"), {})


def test_cli_imports_no_optional_runtime_dependencies() -> None:
    script = (
        "import sys; import codex_platform.agent_skills.cli; "
        "sys.exit(1 if {'redis', 'arq', 'aiosmtplib', 'jinja2'} & set(sys.modules) else 0)"
    )
    result = subprocess.run([sys.executable, "-c", script], check=False)
    assert result.returncode == 0


def test_status_reports_stale_version_payload_and_missing_files(tmp_path: Path) -> None:
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    installed = skill_dir(tmp_path)
    with patch("codex_platform.agent_skills.orchestrator.get_package_version", return_value="future"):
        assert "version differs" in check_status(tmp_path)[1]
    expanded = {**PAYLOAD, "references/more.md": b"new"}
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=expanded):
        assert "file list differs" in check_status(tmp_path)[1]
    changed = {**PAYLOAD, "SKILL.md": b"new content"}
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=changed):
        assert "payload differs" in check_status(tmp_path)[1]
    (installed / "SKILL.md").unlink()
    assert "Missing file" in check_status(tmp_path)[1]
    with pytest.raises(OrchestratorError, match="edited or removed"):
        perform_delete(tmp_path)


def test_unmanaged_and_orphan_states_refuse_mutation(tmp_path: Path) -> None:
    assert check_status(tmp_path) == (False, "Not installed.")
    perform_delete(tmp_path)
    with pytest.raises(OrchestratorError, match="Not installed"):
        perform_install(tmp_path, update=True)
    installed = skill_dir(tmp_path)
    installed.mkdir(parents=True)
    assert "not managed" in check_status(tmp_path)[1]
    with pytest.raises(OrchestratorError, match="Destination exists"):
        perform_install(tmp_path)
    with pytest.raises(OrchestratorError, match="No ownership manifest"):
        perform_delete(tmp_path)
    installed.rmdir()
    (tmp_path / "AGENTS.md").write_bytes(update_agents_md_bytes(b""))
    assert "Orphan" in check_status(tmp_path)[1]
    with pytest.raises(OrchestratorError, match="Orphan"):
        perform_install(tmp_path)


def test_corrupt_manifest_and_missing_marker_refuse_mutation(tmp_path: Path) -> None:
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    installed = skill_dir(tmp_path)
    manifest = installed / MANIFEST_NAME
    original = manifest.read_bytes()
    manifest.write_bytes(b"not json")
    assert "Corrupt ownership manifest" in check_status(tmp_path)[1]
    with pytest.raises(OrchestratorError, match="Corrupt ownership manifest"):
        perform_delete(tmp_path)
    manifest.write_bytes(original)
    agents = tmp_path / "AGENTS.md"
    agents.write_bytes(b"# Removed marker\n")
    assert "instruction missing" in check_status(tmp_path)[1]
    with pytest.raises(OrchestratorError, match="instruction missing"):
        perform_install(tmp_path, update=True)


def test_manifest_name_conflicts_and_marker_corruption() -> None:
    for names in (
        {"SKILL.md": b"x", "skill.md": b"y"},
        {"SKILL.md": b"x", "references": b"a", "references/a.md": b"b"},
        {"SKILL.md": b"x", ".manifest.json": b"owned"},
    ):
        with pytest.raises(ManifestError):
            build_manifest("1", names)
    with pytest.raises(ManifestError):
        build_manifest("", PAYLOAD)
    for broken in (MARKER_START, MARKER_END, update_agents_md_bytes(b"") + MARKER_START):
        with pytest.raises(ManifestError):
            update_agents_md_bytes(broken)


def test_filesystem_rejects_unsafe_targets(tmp_path: Path) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(FSError, match="Not a regular file"):
        check_regular_file(directory)
    with FSTransaction(tmp_path) as tx:
        with pytest.raises(FSError, match="outside project"):
            tx.stage_write(tmp_path.parent / "outside.md", b"x")
        with pytest.raises(FSError, match="transaction directory"):
            tx.stage_write(tx.temp_dir / "inside.md", b"x")
        with pytest.raises(FSError, match="Unsafe directory"):
            tx.stage_prune_empty(tmp_path)
        tx.stage_write(tmp_path / "duplicate.md", b"one")
        tx.stage_write(tmp_path / "duplicate.md", b"two")
        with pytest.raises(FSError, match="multiple operations"):
            tx.apply()
    assert validate_no_symlinks(tmp_path) == tmp_path.absolute()


def test_staging_creation_error_is_wrapped(tmp_path: Path) -> None:
    with (
        patch("codex_platform.agent_skills.fs_transaction.tempfile.mkdtemp", side_effect=OSError("denied")),
        pytest.raises(FSError, match="Cannot create staging directory"),
    ):
        FSTransaction(tmp_path)


def test_windows_reparse_point_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "junction"
    target.mkdir()
    original_lstat = Path.lstat

    def fake_lstat(path: Path):
        if path == target:
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        return original_lstat(path)

    with patch.object(Path, "lstat", fake_lstat), pytest.raises(FSError, match="reparse point"):
        validate_no_symlinks(target / "child")


def test_recovery_failure_retains_backups(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_bytes(b"# Existing\n")
    with patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value=PAYLOAD):
        perform_install(tmp_path)
    original_replace = os.replace
    original_copy = shutil.copy2
    failed = False

    def fail_replace(src: Path, dst: Path) -> None:
        nonlocal failed
        if dst.name == "AGENTS.md" and not failed:
            failed = True
            raise OSError("write failure")
        original_replace(src, dst)

    def fail_restore(src: Path, dst: Path, *args: object, **kwargs: object):
        if src.name.startswith("backup_") and dst.name == "AGENTS.md":
            raise OSError("restore failure")
        return original_copy(src, dst, *args, **kwargs)

    with (
        patch("codex_platform.agent_skills.orchestrator.get_payload_files", return_value={"SKILL.md": b"updated"}),
        patch("os.replace", side_effect=fail_replace),
        patch("shutil.copy2", side_effect=fail_restore),
        pytest.raises(FSError, match="Backups retained at") as raised,
    ):
        perform_install(tmp_path, update=True)
    retained = Path(str(raised.value).split("Backups retained at ", 1)[1])
    assert retained.is_dir()
    assert any((retained / "backup").iterdir())
    shutil.rmtree(retained)


def test_manifest_schema_identity_and_marker_ordering() -> None:
    good = json.loads(build_manifest("1", PAYLOAD))
    for bad in (
        {**good, "version": "2.0"},
        {**good, "skill": "another"},
        {**good, "agents_created": 1},
        {**good, "files": []},
        {**good, "extra": True},
    ):
        with pytest.raises(ManifestError):
            parse_manifest(json.dumps(bad).encode())
    with pytest.raises(ManifestError, match="Malformed AGENTS.md block"):
        update_agents_md_bytes(MARKER_END + b"\n" + MARKER_START)
