"""Windows Task Scheduler and systemd service contract coverage."""

from __future__ import annotations

import pytest

from agency_runtime.core import dashboard_service_core as core
from agency_runtime.core import dashboard_service_systemd as systemd
from agency_runtime.core import dashboard_service_windows as windows


def context(tmp_path, platform="windows"):
    result = core._context(
        home_dir=tmp_path,
        platform_name=platform,
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert result is not None
    if platform == "windows":
        result = core._Context(
            **{
                name: getattr(result, name)
                for name in result.__dataclass_fields__
                if name != "windows_user"
            },
            windows_user="S-1-5-test",
        )
    return result


def command(name="command", *, code=0, stdout="", stderr=""):
    return core._CommandResult((name,), code, stdout, stderr)


def test_windows_action_create_and_task_content(tmp_path):
    assert windows._windows_action(["one two", 'quote"'])
    create = windows._windows_create_command("task.xml", force=False)
    assert create[-1] == "task.xml" and "/F" not in create
    assert windows._windows_create_command("task.xml", force=True)[-1] == "/F"
    ctx = context(tmp_path)
    content = windows._windows_task_content(ctx)
    properties = windows._windows_task_properties(content)
    assert properties is not None
    assert properties["source"] == core.OWNER_ID
    assert properties["principal_user"] == "S-1-5-test"
    assert windows._windows_xml_owned(content)
    assert windows._windows_definition_matches(ctx, content)
    missing_user = core._Context(
        **{name: getattr(ctx, name) for name in ctx.__dataclass_fields__ if name != "windows_user"},
        windows_user=None,
    )
    with pytest.raises(RuntimeError, match="no user identity"):
        windows._windows_task_content(missing_user)


@pytest.mark.parametrize(
    "content",
    [
        "<invalid",
        "<!DOCTYPE Task><Task />",
        "<!ENTITY x 'y'><Task />",
        "x" * (windows._MAX_TASK_XML_BYTES + 1),
        "é" * (windows._MAX_TASK_XML_BYTES // 2 + 1),
        "<Task />",
    ],
    ids=("parse", "doctype", "entity", "char-oversize", "byte-oversize", "schema"),
)
def test_windows_task_properties_rejects_malformed_and_oversized(content):
    assert windows._windows_task_properties(content) is None


def test_windows_task_properties_rejects_schema_injection(tmp_path):
    content = windows._windows_task_content(context(tmp_path))
    mutations = [
        content.replace(
            "  </RegistrationInfo>",
            '    <Foreign xmlns="urn:foreign" />\n  </RegistrationInfo>',
        ),
        content.replace("<Source>", '<Source injected="true">'),
        content.replace("<Source>agency-runtime</Source>", "<Source><Nested /></Source>"),
        content.replace("  </Settings>", "    <Volatile>true</Volatile>\n  </Settings>"),
        content.replace('  <Actions Context="CurrentUser">', ""),
    ]
    for mutated in mutations:
        assert windows._windows_task_properties(mutated) is None


def test_xml_helpers_missing_foreign_duplicate_and_attributes(tmp_path):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(windows._windows_task_content(context(tmp_path)))
    assert windows._xml_text(root, "t:missing") == ""
    assert windows._xml_attribute(root, "t:missing", "name") == ""
    registration = root.find(f"{{{core.WINDOWS_TASK_XML_NAMESPACE}}}RegistrationInfo")
    assert registration is not None
    assert not windows._xml_children_match(
        registration, required=("Description",), attributes={"unexpected": "value"}
    )
    foreign = ET.SubElement(registration, "foreign")
    assert not windows._xml_children_match(registration, required=("Description", "Source"))
    registration.remove(foreign)
    ET.SubElement(
        registration,
        f"{{{core.WINDOWS_TASK_XML_NAMESPACE}}}Source",
    ).text = "duplicate"
    assert not windows._xml_children_match(registration, required=("Description", "Source"))


def test_register_windows_xml_success_and_cleanup_on_early_error(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    observed = []
    result = windows._register_windows_xml(
        ctx,
        windows._windows_task_content(ctx),
        force=True,
        command_runner=lambda argv, **_kw: observed.append(argv) or {"returncode": 0},
    )
    assert result.ok and observed[0][-1] == "/F"
    original = windows.restrict_private_file
    monkeypatch.setattr(
        windows,
        "restrict_private_file",
        lambda _path: (_ for _ in ()).throw(OSError("ACL failed")),
    )
    with pytest.raises(OSError, match="ACL failed"):
        windows._register_windows_xml(
            ctx,
            "content",
            force=False,
            command_runner=lambda *_a, **_kw: {"returncode": 0},
        )
    monkeypatch.setattr(windows, "restrict_private_file", original)


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (command(code=127), "unavailable"),
        (command(code=1), "indeterminate"),
        (command(stdout="ABSENT"), "absent"),
        (command(stdout="PRESENT:0"), "present"),
        (command(stdout="PRESENT:4"), "present"),
        (command(stdout="unexpected"), "indeterminate"),
    ],
)
def test_windows_registration_state(result, expected):
    assert windows._windows_registration_state(result) == expected


def test_windows_registration_queries_and_running_states(monkeypatch):
    results = iter(
        [
            command(stdout="ABSENT"),
            command(stdout="PRESENT:3"),
            command(code=127),
            command(stdout="PRESENT:3"),
            command(code=1),
            command(stdout="PRESENT:3"),
            command(stdout="<xml />"),
        ]
    )
    monkeypatch.setattr(windows, "_run", lambda *_a, **_kw: next(results))
    assert windows._query_windows_registration(command_runner=None)[0] == "absent"
    assert windows._query_windows_registration(command_runner=None)[0] == "unavailable"
    assert windows._query_windows_registration(command_runner=None)[0] == "indeterminate"
    state, result = windows._query_windows_registration(command_runner=None)
    assert state == "present" and result.stdout == "<xml />"

    for stdout, expected in (
        ("ABSENT", None),
        ("PRESENT:4", True),
        ("PRESENT:1", False),
        ("PRESENT:3", False),
        ("PRESENT:2", None),
        ("PRESENT:0", None),
    ):
        monkeypatch.setattr(
            windows,
            "_query_windows_task_probe",
            lambda stdout=stdout, **_kw: command(stdout=stdout),
        )
        assert windows._windows_running_state(command_runner=None)[0] is expected


def test_windows_owned_capture_and_exact_assertions(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    monkeypatch.setattr(windows, "_manifest_owned", lambda _ctx: False)
    with pytest.raises(RuntimeError, match="manifest changed"):
        windows._capture_owned_windows_task(ctx, command_runner=None)
    monkeypatch.setattr(windows, "_manifest_owned", lambda _ctx: True)
    monkeypatch.setattr(
        windows,
        "_query_windows_registration",
        lambda **_kw: ("absent", command()),
    )
    with pytest.raises(RuntimeError, match="ownership marker"):
        windows._capture_owned_windows_task(ctx, command_runner=None)
    monkeypatch.setattr(
        windows,
        "_query_windows_registration",
        lambda **_kw: ("present", command(stdout="current")),
    )
    with pytest.raises(RuntimeError, match="absence could not be confirmed"):
        windows._assert_windows_task_absent(command_runner=None)
    monkeypatch.setattr(windows, "_windows_xml_owned", lambda _xml: True)
    monkeypatch.setattr(
        windows,
        "_query_windows_registration",
        lambda **_kw: ("present", command(stdout="current")),
    )
    assert windows._capture_owned_windows_task(ctx, command_runner=None)[0] == "current"
    with pytest.raises(RuntimeError, match="definition changed"):
        windows._assert_windows_task_unchanged(ctx, "expected", command_runner=None)


def test_systemd_quote_content_and_state_classification(tmp_path):
    assert systemd._systemd_quote('a\\b"%$') == '"a\\\\b\\"%%$$"'
    ctx = context(tmp_path, "linux")
    content = systemd._unit_content(ctx)
    assert core.OWNER_MARKER in content and "NoNewPrivileges=true" in content
    for result, expected in (
        (command(stdout="enabled"), True),
        (command(code=1, stdout="disabled"), False),
        (command(stdout="masked"), False),
        (command(stdout="unexpected"), None),
    ):
        assert systemd._systemd_enabled_state(result) is expected
    for result, expected in (
        (command(stdout="active"), True),
        (command(code=1, stdout="failed"), False),
        (command(stdout="dead"), False),
        (command(stdout="unexpected"), None),
    ):
        assert systemd._systemd_active_state(result) is expected


def test_systemd_assertions_missing_context_and_changed_files(tmp_path, monkeypatch):
    windows_ctx = context(tmp_path)
    with pytest.raises(RuntimeError, match="no unit path"):
        systemd._assert_systemd_files(windows_ctx, expected_unit=None, expected_manifest=None)
    with pytest.raises(RuntimeError, match="no unit path"):
        systemd._restore_systemd_state(
            windows_ctx,
            prior_unit=None,
            prior_manifest=None,
            expected_unit=None,
            expected_manifest=None,
            prior_enabled=False,
            prior_active=False,
            command_runner=None,
        )
    linux = context(tmp_path, "linux")
    monkeypatch.setattr(systemd, "_file_matches", lambda *_a: False)
    with pytest.raises(RuntimeError, match="changed before mutation"):
        systemd._assert_systemd_files(linux, expected_unit=None, expected_manifest=None)


def test_systemd_restore_success_failure_and_unsafe_manifest_cleanup(tmp_path, monkeypatch):
    ctx = context(tmp_path, "linux")
    assert ctx.unit_path is not None
    ctx.unit_path.parent.mkdir(parents=True)
    ctx.unit_path.write_bytes(b"prior")
    ctx.manifest_path.parent.mkdir(parents=True)
    ctx.manifest_path.write_bytes(b"manifest")
    monkeypatch.setattr(systemd, "_assert_systemd_files", lambda *_a, **_kw: None)
    monkeypatch.setattr(systemd, "_restore_file", lambda *_a, **_kw: None)
    results = iter(
        [
            command(),
            command(),
            command(),
            command(stdout="enabled"),
            command(stdout="active"),
        ]
    )
    monkeypatch.setattr(systemd, "_run", lambda *_a, **_kw: next(results))
    monkeypatch.setattr(systemd, "_file_matches", lambda *_a: True)
    outcome = systemd._restore_systemd_state(
        ctx,
        prior_unit=b"prior",
        prior_manifest=b"manifest",
        expected_unit=b"current",
        expected_manifest=b"current-manifest",
        prior_enabled=True,
        prior_active=True,
        command_runner=None,
    )
    assert outcome.succeeded

    calls = []
    monkeypatch.setattr(
        systemd,
        "_assert_systemd_files",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            RuntimeError("systemd service files changed before mutation")
        ),
    )
    monkeypatch.setattr(
        systemd,
        "_file_matches",
        lambda path, _expected: path == ctx.manifest_path,
    )
    monkeypatch.setattr(
        systemd,
        "_restore_file",
        lambda path, value: calls.append((path, value)),
    )
    results = iter([command(stdout="disabled"), command(stdout="inactive")])
    monkeypatch.setattr(systemd, "_run", lambda *_a, **_kw: next(results))
    outcome = systemd._restore_systemd_state(
        ctx,
        prior_unit=None,
        prior_manifest=None,
        expected_unit=b"current",
        expected_manifest=b"manifest",
        prior_enabled=False,
        prior_active=False,
        command_runner=None,
    )
    assert not outcome.succeeded and "ownership manifest removed" in outcome.error
    assert calls == [(ctx.manifest_path, None)]
