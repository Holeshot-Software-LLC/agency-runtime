from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.core.codex_global_guidance import (
    CODEX_GUIDANCE_BEGIN,
    CODEX_GUIDANCE_END,
    CodexGlobalGuidanceError,
    install_codex_global_guidance,
    plan_codex_global_guidance,
    remove_codex_global_guidance,
    render_codex_global_guidance,
)


def test_codex_global_guidance_preserves_owner_content_and_is_idempotent(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    agents = codex_home / "AGENTS.md"
    agents.write_text("# Owner guidance\n", encoding="utf-8")

    first = install_codex_global_guidance(codex_home)
    document = agents.read_text(encoding="utf-8")

    assert first["changed"] is True
    assert first["path"] == str(agents.resolve())
    assert document.startswith("# Owner guidance\n")
    assert document.count(CODEX_GUIDANCE_BEGIN) == 1
    assert document.count(CODEX_GUIDANCE_END) == 1
    assert "[AGENCY DELEGATION PLAN]" in document
    assert "explicitly requests Codex native subagent delegation" in document
    assert "every accepted persisted plan row exactly once" in document
    assert "does not choose, name, or replace any specialist" in document

    second = install_codex_global_guidance(codex_home)

    assert second["changed"] is False
    assert agents.read_text(encoding="utf-8") == document

    removed = remove_codex_global_guidance(codex_home)

    assert removed["changed"] is True
    assert agents.read_text(encoding="utf-8") == "# Owner guidance\n"
    assert remove_codex_global_guidance(codex_home)["changed"] is False


def test_codex_global_guidance_uses_active_override_without_touching_base(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    base = codex_home / "AGENTS.md"
    override = codex_home / "AGENTS.override.md"
    base.write_text("# Base\n", encoding="utf-8")
    override.write_text("# Override\n", encoding="utf-8")

    result = install_codex_global_guidance(codex_home)

    assert result["path"] == str(override.resolve())
    assert base.read_text(encoding="utf-8") == "# Base\n"
    assert CODEX_GUIDANCE_BEGIN in override.read_text(encoding="utf-8")

    removed = remove_codex_global_guidance(codex_home)

    assert removed["changed"] is True
    assert base.read_text(encoding="utf-8") == "# Base\n"
    assert override.read_text(encoding="utf-8") == "# Override\n"


def test_codex_global_guidance_rejects_malformed_managed_boundaries(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    agents = codex_home / "AGENTS.md"
    original = f"# Owner\n{CODEX_GUIDANCE_BEGIN}\ntruncated\n"
    agents.write_text(original, encoding="utf-8")

    with pytest.raises(CodexGlobalGuidanceError, match="managed boundary"):
        install_codex_global_guidance(codex_home)

    assert agents.read_text(encoding="utf-8") == original


def test_rendered_codex_global_guidance_is_bounded_and_plan_scoped() -> None:
    document = render_codex_global_guidance()

    assert len(document.encode("utf-8")) < 2_048
    assert document.startswith(CODEX_GUIDANCE_BEGIN)
    assert document.endswith(CODEX_GUIDANCE_END + "\n")
    assert "only when the current turn contains" in document
    assert "Inference remains the only staffing authority" in document


def test_codex_global_guidance_preserves_owner_content_without_final_newline(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    agents = codex_home / "AGENTS.md"
    agents.write_text("owner content", encoding="utf-8")

    install_codex_global_guidance(codex_home)
    remove_codex_global_guidance(codex_home)

    assert agents.read_text(encoding="utf-8") == "owner content"


def test_codex_global_guidance_rejects_non_utf8_without_change(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    agents = codex_home / "AGENTS.md"
    original = b"\xff\xfeowner"
    agents.write_bytes(original)

    with pytest.raises(CodexGlobalGuidanceError, match="must be UTF-8"):
        install_codex_global_guidance(codex_home)

    assert agents.read_bytes() == original


def test_codex_global_guidance_plan_is_write_free_and_matches_install(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"

    plan = plan_codex_global_guidance(codex_home)

    assert plan["status"] == "planned"
    assert plan["root_exists"] is False
    assert plan["changed"] is True
    assert codex_home.exists() is False

    installed = install_codex_global_guidance(codex_home)

    assert installed["root_created"] is True
    assert installed["document_sha256"] == plan["document_sha256"]


def test_codex_global_guidance_remove_is_idempotent_when_profile_is_absent(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / ".codex"

    result = remove_codex_global_guidance(codex_home)

    assert result["status"] == "absent"
    assert result["changed"] is False
    assert codex_home.exists() is False
