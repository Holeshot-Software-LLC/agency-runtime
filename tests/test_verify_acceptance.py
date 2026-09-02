"""Isolated single-check acceptance verification runner contracts (AR-361)."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import cli_transport
from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.delegation.backends import BoundedProcessResult
from scripts import docs_metadata, verify_acceptance, verify_docs
from tests.runtime_support import trusted_test_interpreter

_ISSUE = """---
title: "AR-999: Fixture"
status: {status}
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: []
related: []
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-999
priority: p2
tracker_url: null
depends_on: []
blocks: []
---

# AR-999: Fixture

## Acceptance

- [x] The fixture test exists
      at the candidate.
- [x] The README names the fixture.
"""

_RECORD = """---
title: "AR-999 acceptance verification record"
status: active
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: []
related:
  - docs/roadmap/issue-AR-999-fixture.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-999
candidate_commit: {candidate}
evidence_cutoff: 2026-08-31
tracker_url: null
---

# AR-999 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
{builder}
## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
"""

_BUILDER_ROWS = (
    "| 1 | test | `test_fixture` | 2026-08-31 | `tests/test_fixture.py:1-2` |\n"
    "| 2 | file | `README.md` | 2026-08-31 | `README.md#fixture` |\n"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(repo), "GIT_CONFIG_NOSYSTEM": "1"},
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A committed fixture repository whose record cites the commit it lives in."""

    repository = tmp_path / "repo"
    (repository / "docs" / "roadmap" / "acceptance").mkdir(parents=True)
    (repository / "tests").mkdir()
    (repository / "tests" / "test_fixture.py").write_text(
        "def test_fixture():\n    assert True\n", encoding="utf-8"
    )
    (repository / "README.md").write_text("# Top\n\n## Fixture\n\nNamed.\n", encoding="utf-8")
    (repository / "docs" / "roadmap" / "issue-AR-999-fixture.md").write_text(
        _ISSUE.format(status="in_progress"), encoding="utf-8"
    )
    record = repository / "docs" / "roadmap" / "acceptance" / "issue-AR-999.md"
    record.write_text(_RECORD.format(candidate="pending", builder=_BUILDER_ROWS), encoding="utf-8")
    _git(repository, "init", "-q")
    _git(repository, "add", ".")
    _git(repository, "commit", "-q", "-m", "fixture")
    candidate = _git(repository, "rev-parse", "HEAD")
    record.write_text(_RECORD.format(candidate=candidate, builder=_BUILDER_ROWS), encoding="utf-8")
    monkeypatch.setattr(verify_docs, "ROOT", repository)
    return repository


def _provider(transport: str = "claude") -> ProviderEntry:
    return ProviderEntry(name=transport, type="cli", transport=transport, model="")


def _fake_invoker(
    verdict: str | None,
    calls: list[dict[str, Any]],
) -> verify_acceptance.Invoker:
    def invoke(provider: ProviderEntry, prompt: str, schema: Any, **kwargs: Any) -> Any:
        roots = kwargs.get("read_only_roots", ())
        calls.append(
            {
                "provider": provider,
                "prompt": prompt,
                "schema": schema,
                "roots_exist": [Path(root).is_dir() for root in roots],
                "snapshot_has_test": [
                    (Path(root) / "tests" / "test_fixture.py").is_file() for root in roots
                ],
                **kwargs,
            }
        )
        if verdict is None:
            return None
        return {"verdict": verdict, "reason": "the | cited   test exists at the candidate"}

    return invoke


def _record_docs(repo: Path) -> list[verify_docs.Document]:
    docs: list[verify_docs.Document] = []
    for relative in (
        "docs/roadmap/issue-AR-999-fixture.md",
        "docs/roadmap/acceptance/issue-AR-999.md",
    ):
        doc = verify_docs.parse_document(repo / relative, [])
        assert doc is not None
        docs.append(doc)
    return docs


def _gate_errors(repo: Path) -> list[str]:
    errors: list[str] = []
    verify_docs.validate_acceptance_verification(_record_docs(repo), errors, grandfathered=set())
    return errors


def _flip_done(repo: Path) -> None:
    (repo / "docs" / "roadmap" / "issue-AR-999-fixture.md").write_text(
        _ISSUE.format(status="done"), encoding="utf-8"
    )


def test_runner_records_isolated_satisfied_verdicts_that_unlock_the_done_flip(
    repo: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    first = verify_acceptance.verify_criterion(
        "AR-999",
        1,
        provider=_provider(),
        invoker=_fake_invoker("satisfied", calls),
        today=date(2026, 9, 1),
        out=None,
    )
    second = verify_acceptance.verify_criterion(
        "AR-999",
        2,
        provider=_provider(),
        invoker=_fake_invoker("satisfied", calls),
        today=date(2026, 9, 1),
        out=None,
    )

    assert first is not None and second is not None
    assert first.verdict == second.verdict == "satisfied"
    assert first.run_id != second.run_id
    assert first.reason == "the / cited test exists at the candidate"
    assert [call["tools"] for call in calls] == [("Read", "Grep", "Glob")] * 2
    assert [call["max_turns"] for call in calls] == [16, 16]
    assert [call["roots_exist"] for call in calls] == [[True], [True]]
    assert [call["snapshot_has_test"] for call in calls] == [[True], [True]]
    assert all("Never implement, edit, fix, run" in call["system_prompt"] for call in calls)
    assert "The fixture test exists at the candidate." in calls[0]["prompt"]
    assert "README names the fixture" not in calls[0]["prompt"]
    assert "tests/test_fixture.py:1-2" in calls[0]["prompt"]
    assert "def test_fixture():" in calls[0]["prompt"]
    assert "README.md#fixture" not in calls[0]["prompt"]
    assert calls[0]["schema"]["properties"]["verdict"]["enum"] == [
        "absent",
        "contradicted",
        "satisfied",
    ]
    record_text = (repo / "docs/roadmap/acceptance/issue-AR-999.md").read_text(encoding="utf-8")
    assert "evidence_cutoff: 2026-09-01" in record_text
    assert record_text.count("| satisfied |") == 2
    assert _gate_errors(repo) == []
    _flip_done(repo)
    assert _gate_errors(repo) == []


def test_runner_refuses_to_record_when_the_verifier_is_unavailable(repo: Path) -> None:
    record = repo / "docs/roadmap/acceptance/issue-AR-999.md"
    before = record.read_text(encoding="utf-8")
    calls: list[dict[str, Any]] = []

    outcome = verify_acceptance.verify_criterion(
        "AR-999", 1, provider=_provider(), invoker=_fake_invoker(None, calls), out=None
    )
    exit_code = verify_acceptance.main(
        ["--issue", "AR-999", "--criterion", "1"], invoker=_fake_invoker(None, calls)
    )

    assert outcome is None
    assert exit_code == 2
    assert record.read_text(encoding="utf-8") == before
    assert len(calls) == 2


@pytest.mark.parametrize("answer", [{"verdict": "maybe", "reason": "x"}, {"verdict": "satisfied"}])
def test_runner_treats_answers_outside_the_vocabulary_as_unavailable(
    repo: Path,
    answer: dict[str, Any],
) -> None:
    record = repo / "docs/roadmap/acceptance/issue-AR-999.md"
    before = record.read_text(encoding="utf-8")

    outcome = verify_acceptance.verify_criterion(
        "AR-999", 1, provider=_provider(), invoker=lambda *_a, **_k: answer, out=None
    )

    assert outcome is None
    assert record.read_text(encoding="utf-8") == before


def test_runner_records_contradicted_verdicts_that_block_the_done_flip(repo: Path) -> None:
    calls: list[dict[str, Any]] = []
    for index, verdict in ((1, "satisfied"), (2, "contradicted")):
        assert (
            verify_acceptance.verify_criterion(
                "AR-999",
                index,
                provider=_provider(),
                invoker=_fake_invoker(verdict, calls),
                out=None,
            )
            is not None
        )
    _flip_done(repo)

    assert _gate_errors(repo) == [
        "docs/roadmap/issue-AR-999-fixture.md: criterion 2 verdict is 'contradicted'; "
        "the done flip is blocked"
    ]


def test_runner_records_absent_builder_evidence_without_calling_a_model(repo: Path) -> None:
    record = repo / "docs/roadmap/acceptance/issue-AR-999.md"
    candidate = verify_docs.git("rev-parse", "HEAD")
    record.write_text(
        _RECORD.format(
            candidate=candidate,
            builder="| 1 | absent | none | 2026-08-31 | none |\n"
            + "| 2 | file | `README.md` | 2026-08-31 | `README.md#fixture` |\n",
        ),
        encoding="utf-8",
    )

    def never(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("absent evidence must not reach a verifier")

    outcome = verify_acceptance.verify_criterion(
        "AR-999", 1, provider=_provider(), invoker=never, out=None
    )

    assert outcome is not None and outcome.verdict == "absent"
    assert _gate_errors(repo) == []
    _flip_done(repo)
    assert _gate_errors(repo) == [
        "docs/roadmap/issue-AR-999-fixture.md: criterion 1 verdict is 'absent'; the done flip "
        "is blocked",
        "docs/roadmap/issue-AR-999-fixture.md: criterion 2 has no verifier verdict in "
        "docs/roadmap/acceptance/issue-AR-999.md",
    ]


def test_runner_refuses_pending_records_and_unknown_criteria(repo: Path) -> None:
    record = repo / "docs/roadmap/acceptance/issue-AR-999.md"
    with pytest.raises(verify_acceptance.VerificationError, match=r"outside 1\.\.2"):
        verify_acceptance.verify_criterion(
            "AR-999", 3, provider=_provider(), invoker=_fake_invoker("satisfied", []), out=None
        )
    record.write_text(_RECORD.format(candidate="pending", builder=_BUILDER_ROWS), encoding="utf-8")

    with pytest.raises(verify_acceptance.VerificationError, match="candidate_commit is pending"):
        verify_acceptance.verify_criterion(
            "AR-999", 1, provider=_provider(), invoker=_fake_invoker("satisfied", []), out=None
        )
    assert (
        verify_acceptance.main(
            ["--issue", "AR-999", "--all"], invoker=_fake_invoker("satisfied", [])
        )
        == 1
    )


def test_runner_dry_run_prints_the_single_criterion_prompt_and_writes_nothing(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    record = repo / "docs/roadmap/acceptance/issue-AR-999.md"
    before = record.read_text(encoding="utf-8")

    exit_code = verify_acceptance.main(
        ["--issue", "AR-999", "--criterion", "2", "--dry-run"],
        invoker=lambda *_a, **_k: pytest.fail("dry runs never invoke"),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"index": 2' in output
    assert "The fixture test exists" not in output
    assert record.read_text(encoding="utf-8") == before


def test_runner_reverifies_by_replacing_the_criterion_row_and_uses_excerpts_on_codex(
    repo: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    for verdict in ("contradicted", "satisfied"):
        verify_acceptance.verify_criterion(
            "AR-999",
            1,
            provider=_provider("codex"),
            invoker=_fake_invoker(verdict, calls),
            out=None,
        )
    text = (repo / "docs/roadmap/acceptance/issue-AR-999.md").read_text(encoding="utf-8")

    assert text.count("\n| 1 | ") == 2  # one builder row and one verification row
    assert "| contradicted |" not in text
    assert "tools" not in calls[0] and "read_only_roots" not in calls[0]
    assert '"snapshot_root": null' in calls[0]["prompt"]
    assert (
        verify_acceptance.main(
            ["--issue", "AR-999", "--all"], invoker=_fake_invoker("satisfied", calls)
        )
        == 0
    )
    assert len(calls) == 4


def test_transport_grants_only_bounded_read_only_investigation_options(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        captured["argv"] = argv
        return BoundedProcessResult(
            0,
            '{"subtype": "success", "structured_output": {"verdict": "absent", "reason": "r"}}',
            "",
        )

    common: dict[str, Any] = {
        "timeout": 1,
        "resolver": lambda _name: str(trusted_test_interpreter()),
        "runner": run,
        "environ": {"HOME": str(Path.home())},
    }
    result = cli_transport.invoke_cli_structured(
        _provider(),
        "judge",
        verify_acceptance.VERDICT_SCHEMA,
        tools=("Read", "Grep", "Glob"),
        max_turns=16,
        read_only_roots=(tmp_path,),
        **common,
    )
    argv = captured["argv"]

    assert result == {"verdict": "absent", "reason": "r"}
    assert "--tools=Read,Grep,Glob" in argv and "--restricted" in argv
    assert argv[argv.index("--add-dir") + 1] == str(tmp_path)
    assert argv[argv.index("--max-turns") + 1] == "16"
    assert "--tools=" not in argv

    captured.clear()
    assert cli_transport.invoke_cli_structured(
        _provider(), "judge", verify_acceptance.VERDICT_SCHEMA, **common
    ) == {"verdict": "absent", "reason": "r"}
    assert "--tools=" in captured["argv"] and "--restricted" not in captured["argv"]
    assert captured["argv"][captured["argv"].index("--max-turns") + 1] == "3"

    rejected = [
        {"tools": ("Bash",)},
        {"tools": "Read"},
        {"tools": ("Read",), "read_only_roots": (tmp_path / "missing",)},
        {"tools": ("Read",), "read_only_roots": ("relative",)},
        {"read_only_roots": (tmp_path,)},
        {"max_turns": 0},
        {"max_turns": True},
        {"max_turns": 33},
    ]
    for options in rejected:
        captured.clear()
        assert (
            cli_transport.invoke_cli_structured(
                _provider(), "judge", verify_acceptance.VERDICT_SCHEMA, **options, **common
            )
            is None
        )
        assert captured == {}
    assert (
        cli_transport.invoke_cli_structured(
            _provider("codex"), "judge", verify_acceptance.VERDICT_SCHEMA, tools=("Read",), **common
        )
        is None
    )


def test_docs_metadata_classifies_acceptance_records_as_active_pending_drafts() -> None:
    record = docs_metadata.ROOT / "docs" / "roadmap" / "acceptance" / "issue-AR-361.md"
    readme = docs_metadata.ROOT / "docs" / "roadmap" / "acceptance" / "README.md"

    assert docs_metadata.classification(record) == ("roadmap", "active")
    assert docs_metadata.classification(readme) == ("roadmap", "active")
    assert docs_metadata.variant_fields(record)[:3] == [
        "type: acceptance-verification",
        "issue_id: AR-361",
        "candidate_commit: pending",
    ]
    assert docs_metadata.variant_fields(readme) == []
