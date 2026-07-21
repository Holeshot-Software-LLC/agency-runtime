from __future__ import annotations

import json

from agency_runtime.core.cli_transport import _parse_codex_model_catalog, discover_cli_models
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
                        "base_instructions": "secret instructions must never be projected",
                    },
                    {"slug": "hidden-model", "visibility": "hide", "priority": 1},
                    {"slug": "unsafe model", "visibility": "list", "priority": 0},
                ]
            }
        )
    )
    assert [model.slug for model in catalog.models] == ["gpt-cheap"]
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
