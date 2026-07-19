"""Private dashboard runtime descriptor and service-worker tests."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import dashboard_runtime as runtime_module
from agency_runtime.core.config import AgencyConfig, DashboardConfig
from agency_runtime.core.dashboard_runtime import (
    dashboard_runtime_instance_fingerprint,
    dashboard_runtime_path,
    dashboard_service_reachable,
    open_dashboard_service,
    read_dashboard_runtime,
    remove_dashboard_runtime,
    write_dashboard_runtime,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import dashboard as dashboard_module
from agency_runtime.server.dashboard import DashboardHTTPServer
from tests.runtime_support import ensure_private_test_directory


def test_runtime_instance_fingerprint_tracks_generation_without_exposing_token(
    tmp_path: Path,
) -> None:
    assert dashboard_runtime_instance_fingerprint(home_dir=tmp_path) is None
    first_token = "first-private-token-" + ("a" * 32)
    write_dashboard_runtime(
        token=first_token,
        port=7810,
        pid=111,
        home_dir=tmp_path,
    )
    first = dashboard_runtime_instance_fingerprint(home_dir=tmp_path)
    write_dashboard_runtime(
        token="second-private-token-" + ("b" * 32),
        port=7810,
        pid=111,
        home_dir=tmp_path,
    )
    second = dashboard_runtime_instance_fingerprint(home_dir=tmp_path)

    assert first is not None and first.startswith("sha256:")
    assert second is not None and second != first
    assert first_token not in first


def test_runtime_descriptor_rotates_and_only_owner_can_remove(tmp_path: Path) -> None:
    first = write_dashboard_runtime(
        token="a" * 48,
        port=7810,
        pid=111,
        home_dir=tmp_path,
    )
    target = dashboard_runtime_path(home_dir=tmp_path)

    assert read_dashboard_runtime(home_dir=tmp_path) == first
    assert (
        remove_dashboard_runtime(
            token="b" * 48,
            pid=111,
            home_dir=tmp_path,
        )
        is False
    )
    assert target.exists()

    second = write_dashboard_runtime(
        token="c" * 48,
        port=7811,
        pid=222,
        home_dir=tmp_path,
    )
    assert second["token"] != first["token"]
    assert (
        remove_dashboard_runtime(
            token=second["token"],
            pid=222,
            home_dir=tmp_path,
        )
        is True
    )
    assert not target.exists()


def test_runtime_removal_serializes_against_new_worker_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_token = "old-worker-" + "a" * 40
    new_token = "new-worker-" + "b" * 40

    write_dashboard_runtime(
        token=old_token,
        port=7810,
        pid=111,
        home_dir=tmp_path,
    )

    compare_entered = threading.Event()
    writer_attempted = threading.Event()
    failures: list[BaseException] = []
    original_compare = runtime_module.hmac.compare_digest

    def coordinated_compare(left: str, right: str) -> bool:
        compare_entered.set()
        assert writer_attempted.wait(timeout=2)
        return original_compare(left, right)

    def publish_new_worker() -> None:
        try:
            assert compare_entered.wait(timeout=2)
            writer_attempted.set()
            write_dashboard_runtime(
                token=new_token,
                port=7811,
                pid=222,
                home_dir=tmp_path,
            )
        except BaseException as exc:  # pragma: no cover - reported below
            failures.append(exc)

    monkeypatch.setattr(runtime_module.hmac, "compare_digest", coordinated_compare)
    thread = threading.Thread(target=publish_new_worker, daemon=True)
    thread.start()

    assert (
        remove_dashboard_runtime(
            token=old_token,
            pid=111,
            home_dir=tmp_path,
        )
        is True
    )
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert failures == []
    current = read_dashboard_runtime(home_dir=tmp_path)
    assert current["pid"] == 222
    assert current["token"] == new_token


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_runtime_descriptor_is_owner_only_on_posix(tmp_path: Path) -> None:
    write_dashboard_runtime(token="a" * 48, port=7810, home_dir=tmp_path)

    mode = dashboard_runtime_path(home_dir=tmp_path).stat().st_mode & 0o777

    assert mode == 0o600


def test_runtime_descriptor_hardens_empty_temp_before_writing_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    target = dashboard_runtime_path(home_dir=tmp_path)
    ensure_private_test_directory(target.parent, parents=True)
    target.write_bytes(b"original-descriptor")
    token = "never-written-dashboard-token-" + "x" * 32
    observed_temporary_bytes: list[bytes] = []
    replace_calls: list[tuple[Path, Path]] = []
    monkeypatch.setattr(
        runtime_module,
        "os",
        os_facade(runtime_module.os, name="nt"),
    )
    monkeypatch.setitem(
        sys.modules,
        "msvcrt",
        SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=lambda *_args: None),
    )

    def fail_hardening(candidate: str | Path) -> None:
        observed_temporary_bytes.append(Path(candidate).read_bytes())
        raise PermissionError("simulated private-file hardening failure")

    monkeypatch.setattr(runtime_module, "restrict_private_file", fail_hardening)
    monkeypatch.setattr(
        runtime_module.os,
        "replace",
        lambda source, destination: replace_calls.append((source, destination)),
    )

    with pytest.raises(PermissionError, match="hardening failure"):
        write_dashboard_runtime(
            token=token,
            port=7810,
            path=target,
        )

    # Both the lock and descriptor temp are hardened while still empty; the
    # lock sentinel and rotating bearer token are written only afterwards.
    assert observed_temporary_bytes == [b"", b""]
    assert replace_calls == []
    assert target.read_bytes() == b"original-descriptor"
    assert token.encode() not in target.read_bytes()
    assert list(target.parent.glob(".dashboard.json.*.tmp")) == []


def test_runtime_descriptor_rejects_untrusted_shapes(tmp_path: Path) -> None:
    target = dashboard_runtime_path(home_dir=tmp_path)
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"token": "visible"}), encoding="utf-8")

    with pytest.raises(ValueError, match="schema"):
        read_dashboard_runtime(home_dir=tmp_path)


def test_runtime_descriptor_rejects_duplicate_fields(tmp_path: Path) -> None:
    target = dashboard_runtime_path(home_dir=tmp_path)
    target.parent.mkdir(parents=True)
    target.write_text(
        '{"schema_version":1,"pid":1,"pid":2,"port":7810,'
        '"token":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx","started_at":"now"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid"):
        read_dashboard_runtime(home_dir=tmp_path)


def test_open_result_never_contains_the_private_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "private-token-" + "x" * 40
    write_dashboard_runtime(token=token, port=7810, pid=111, home_dir=tmp_path)
    opened: list[str] = []
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_service_reachable",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.webbrowser.open",
        lambda url, new=0: opened.append(url),
    )

    result = open_dashboard_service(home_dir=tmp_path)

    assert result["ok"] is True
    assert token not in json.dumps(result)
    assert opened == [f"http://127.0.0.1:7810/#token={token}"]


def test_reachability_uses_authenticated_health(tmp_path: Path) -> None:
    store = Store(tmp_path / "dashboard.db")
    server = DashboardHTTPServer(
        store,
        auth_token="health-token-" + "x" * 32,
        port=0,
        host_inspector=lambda: [],
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    descriptor = {
        "schema_version": 1,
        "pid": os.getpid(),
        "port": int(server.server_address[1]),
        "token": "health-token-" + "x" * 32,
        "started_at": "2026-07-11T00:00:00+00:00",
    }
    try:
        assert dashboard_service_reachable(descriptor=descriptor) is True
        assert (
            dashboard_service_reachable(
                descriptor={**descriptor, "token": "wrong-token-" + "x" * 32}
            )
            is False
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_reachability_rejects_oversized_health_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OversizedResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, size: int) -> bytes:
            assert size == runtime_module._MAX_HEALTH_RESPONSE_BYTES + 1
            return b"x" * size

    def fake_open_no_redirect(request, *, timeout: float):
        assert request.full_url == "http://127.0.0.1:7810/api/health"
        assert request.get_header("Authorization") == ("Bearer bounded-health-token-" + "x" * 32)
        assert timeout == 0.25
        return OversizedResponse()

    monkeypatch.setattr(runtime_module, "open_no_redirect", fake_open_no_redirect)
    descriptor = {
        "schema_version": 1,
        "pid": 123,
        "port": 7810,
        "token": "bounded-health-token-" + "x" * 32,
        "started_at": "2026-07-11T00:00:00+00:00",
    }

    assert dashboard_service_reachable(descriptor=descriptor, timeout=0.25) is False


def test_service_mode_publishes_descriptor_without_printing_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    published: list[dict] = []
    removed: list[dict] = []

    class FakeStore:
        def trim_runtime_tables(self, **_kwargs):
            return {}

    class FakeServer:
        server_address = ("127.0.0.1", 8123)

        def __init__(
            self,
            _store,
            *,
            auth_token,
            port,
            config_path,
            runtime_control_home,
        ):
            self.auth_token = auth_token
            assert port == 8123
            assert Path(config_path).is_absolute()
            assert runtime_control_home == tmp_path

        def serve_forever(self, *, poll_interval):
            assert poll_interval == 0.1

        def server_close(self):
            return None

        def shutdown(self):
            return None

    class ImmediateThread:
        def __init__(self, *, target, daemon, name=""):
            assert daemon is True
            self.target = target
            self.name = name

        def start(self):
            self.target()

        def join(self, *, timeout):
            assert timeout == 0.5

    monkeypatch.setattr(
        dashboard_module,
        "load_config",
        lambda *_args, **_kwargs: AgencyConfig(dashboard=DashboardConfig(port=8123)),
    )
    monkeypatch.setattr(dashboard_module, "Store", lambda *_args, **_kwargs: FakeStore())
    monkeypatch.setattr(dashboard_module, "DashboardHTTPServer", FakeServer)
    monkeypatch.setattr(dashboard_module, "Thread", ImmediateThread)
    monkeypatch.setattr(
        dashboard_module,
        "write_dashboard_runtime",
        lambda **kwargs: published.append(kwargs),
    )
    monkeypatch.setattr(
        dashboard_module,
        "remove_dashboard_runtime",
        lambda **kwargs: removed.append(kwargs),
    )

    dashboard_module.run_dashboard(
        service_mode=True,
        open_browser=False,
        home_dir=tmp_path,
    )

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""
    assert published[0]["port"] == 8123
    assert len(published[0]["token"]) >= 32
    assert removed[0]["token"] == published[0]["token"]
    assert removed[0]["pid"] == os.getpid()
    assert published[0]["token"] not in output.out
