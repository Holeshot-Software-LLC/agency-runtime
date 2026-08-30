from __future__ import annotations

import json
import time

import pytest

from agency_runtime.core import cli_transport
from agency_runtime.core.cli_transport import (
    CLIModelCatalog,
    CLIModelInfo,
    _discover_cli_models_uncached,
    _parse_codex_model_catalog,
    discover_cli_models,
)
from agency_runtime.core.delegation.backends import BoundedProcessResult
from tests.runtime_support import trusted_test_interpreter


def test_codex_model_catalog_projects_only_visible_safe_metadata() -> None:
    catalog = _parse_codex_model_catalog(
        json.dumps(
            {
                "models": [
                    {
                        "slug": "gpt-cheap",
                        "display_name": "Cheap",
                        "description": "Low-cost routing",
                        "visibility": "list",
                        "priority": 2,
                        "default_reasoning_level": "low",
                        "supported_reasoning_levels": [
                            {"effort": "low", "description": "Fast"},
                            {"effort": "high", "description": "Deep"},
                            {"effort": "danger;run", "description": "Invalid"},
                        ],
                        "base_instructions": "secret instructions must never be projected",
                    },
                    {"slug": "hidden-model", "visibility": "hide", "priority": 1},
                    {"slug": "unsafe model", "visibility": "list", "priority": 0},
                ]
            }
        )
    )
    assert [model.slug for model in catalog.models] == ["gpt-cheap"]
    assert catalog.models[0].supported_reasoning_levels == ("low", "high")
    assert catalog.as_dict()["models"][0]["supported_reasoning_levels"] == ["low", "high"]
    assert "secret instructions" not in json.dumps(catalog.as_dict())


def test_cli_model_discovery_invokes_bounded_codex_catalog_command() -> None:
    calls = []

    def runner(argv, **kwargs):
        calls.append((tuple(argv), kwargs))
        return BoundedProcessResult(
            0,
            json.dumps(
                {
                    "models": [
                        {
                            "slug": "gpt-cheap",
                            "display_name": "Cheap",
                            "visibility": "list",
                            "priority": 1,
                        }
                    ]
                }
            ),
            "",
        )

    catalog = discover_cli_models(
        "codex",
        refresh=True,
        resolver=lambda *_args, **_kwargs: str(trusted_test_interpreter()),
        runner=runner,
        timeout=2,
    )
    assert [model.slug for model in catalog.models] == ["gpt-cheap"]
    assert calls[0][0][-2:] == ("debug", "models")
    assert calls[0][1]["max_output_chars"] == 1_048_576


def test_unsupported_cli_model_discovery_is_explicit() -> None:
    catalog = discover_cli_models("claude", refresh=True)
    assert catalog.models == ()
    assert "not available" in catalog.error


def test_codex_model_catalog_rejects_bad_documents_and_bounds_rows() -> None:
    assert "invalid model catalog" in _parse_codex_model_catalog("{").error
    assert "invalid shape" in _parse_codex_model_catalog("[]").error
    assert "invalid shape" in _parse_codex_model_catalog(json.dumps({"models": [{}] * 513})).error

    rows = [
        None,
        {"slug": "hidden", "visibility": "hide"},
        {"slug": "duplicate", "visibility": "list", "priority": True},
        {"slug": "duplicate", "visibility": "list"},
    ]
    rows.extend(
        {"slug": f"model-{index:02d}", "visibility": "list", "priority": "bad"}
        for index in range(70)
    )
    catalog = _parse_codex_model_catalog(json.dumps({"models": rows}))
    assert len(catalog.models) == 64
    assert catalog.models[0].slug == "duplicate"
    assert all(model.priority == 1_000 for model in catalog.models)
    assert (
        "no visible"
        in _parse_codex_model_catalog(
            json.dumps({"models": [{"slug": "hidden", "visibility": "hide"}]})
        ).error
    )


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (BoundedProcessResult(0, "", "", timed_out=True), "timed out"),
        (BoundedProcessResult(1, "", ""), "incomplete"),
        (BoundedProcessResult(0, "{}", "", stdout_truncated=True), "incomplete"),
        (BoundedProcessResult(0, "{}", "", stderr_truncated=True), "incomplete"),
    ],
)
def test_uncached_model_discovery_reports_process_failures(result, message) -> None:
    catalog = _discover_cli_models_uncached(
        "codex",
        timeout=1,
        resolver=lambda *_args, **_kwargs: str(trusted_test_interpreter()),
        runner=lambda *_args, **_kwargs: result,
        environ={},
    )
    assert message in catalog.error


def test_uncached_model_discovery_reports_resolution_and_runner_failures() -> None:
    unsupported = _discover_cli_models_uncached(
        "claude", timeout=1, resolver=lambda *_a, **_k: None, runner=lambda: None, environ={}
    )
    assert "not available" in unsupported.error
    missing = _discover_cli_models_uncached(
        "codex", timeout=1, resolver=lambda *_a, **_k: None, runner=lambda: None, environ={}
    )
    assert "not found" in missing.error

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    failed = _discover_cli_models_uncached(
        "codex",
        timeout=1,
        resolver=lambda *_args, **_kwargs: str(trusted_test_interpreter()),
        runner=explode,
        environ={},
    )
    assert "failed" in failed.error


def test_discovery_validates_inputs_uses_cache_and_cleans_singleflight(monkeypatch) -> None:
    with cli_transport._MODEL_CATALOG_CONDITION:
        cli_transport._MODEL_CATALOG_CACHE.clear()
        cli_transport._MODEL_CATALOG_IN_FLIGHT.clear()
    assert "unsupported" in discover_cli_models("other").error
    assert "timeout" in discover_cli_models("codex", timeout=False).error

    value = CLIModelCatalog(
        "codex", (CLIModelInfo("cached", "Cached", "", 1, "low"),), "test", "now"
    )
    with cli_transport._MODEL_CATALOG_CONDITION:
        cli_transport._MODEL_CATALOG_CACHE["codex"] = (time.monotonic() + 60, value)
    cached = discover_cli_models("codex")
    assert cached.cache_hit and cached.models[0].slug == "cached"

    with cli_transport._MODEL_CATALOG_CONDITION:
        cli_transport._MODEL_CATALOG_CACHE.clear()
        cli_transport._MODEL_CATALOG_IN_FLIGHT.add("codex")
    busy = discover_cli_models("codex", timeout=0.001)
    assert "already in progress" in busy.error
    with cli_transport._MODEL_CATALOG_CONDITION:
        cli_transport._MODEL_CATALOG_IN_FLIGHT.clear()

    monkeypatch.setattr(
        cli_transport,
        "_discover_cli_models_uncached",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(RuntimeError, match="boom"):
        discover_cli_models("codex", refresh=True)
    assert "codex" not in cli_transport._MODEL_CATALOG_IN_FLIGHT


def test_discovery_reuses_cache_filled_while_waiting(monkeypatch) -> None:
    value = CLIModelCatalog(
        "codex", (CLIModelInfo("shared", "Shared", "", 1, "low"),), "test", "now"
    )

    class FillingCondition:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        @staticmethod
        def wait(*, timeout):
            assert timeout > 0
            cli_transport._MODEL_CATALOG_CACHE["codex"] = (time.monotonic() + 60, value)
            cli_transport._MODEL_CATALOG_IN_FLIGHT.discard("codex")

    monkeypatch.setattr(cli_transport, "_MODEL_CATALOG_CONDITION", FillingCondition())
    cli_transport._MODEL_CATALOG_CACHE.clear()
    cli_transport._MODEL_CATALOG_IN_FLIGHT.clear()
    cli_transport._MODEL_CATALOG_IN_FLIGHT.add("codex")
    catalog = discover_cli_models("codex", refresh=True, timeout=1)
    assert catalog.cache_hit is True
    assert catalog.models[0].slug == "shared"
