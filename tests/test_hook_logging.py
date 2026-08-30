"""Opt-in hook log sink contracts."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from agency_runtime.core.hook_logging import (
    LEVEL_VARIABLE,
    PATH_VARIABLE,
    install_hook_log_sink,
)

_PACKAGE_LOGGER = "agency_runtime"
_SINK_ATTRIBUTE = "_agency_hook_log_sink"


@pytest.fixture(autouse=True)
def _restore_package_logger() -> Iterator[None]:
    """Leave the shared package logger exactly as the suite found it."""

    logger = logging.getLogger(_PACKAGE_LOGGER)
    handlers = list(logger.handlers)
    level = logger.level
    propagate = logger.propagate
    marked = getattr(logger, _SINK_ATTRIBUTE, False)
    yield
    for handler in list(logger.handlers):
        if handler not in handlers:
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(level)
    logger.propagate = propagate
    if marked:
        setattr(logger, _SINK_ATTRIBUTE, marked)
    else:
        logger.__dict__.pop(_SINK_ATTRIBUTE, None)


def test_absent_variable_installs_nothing() -> None:
    logger = logging.getLogger(_PACKAGE_LOGGER)
    before = list(logger.handlers)

    assert install_hook_log_sink({}) is False
    assert logger.handlers == before


def test_records_reach_the_configured_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "hooks.log"

    assert install_hook_log_sink({PATH_VARIABLE: str(target)}) is True
    logging.getLogger("agency_runtime.adapters.hooks").error("evidence contract failed")

    for handler in logging.getLogger(_PACKAGE_LOGGER).handlers:
        handler.flush()
    assert "evidence contract failed" in target.read_text(encoding="utf-8")


def test_sink_never_propagates_to_stderr(tmp_path: Path) -> None:
    """lastResort must not be reachable while the sink is installed."""

    target = tmp_path / "hooks.log"

    assert install_hook_log_sink({PATH_VARIABLE: str(target)}) is True
    assert logging.getLogger(_PACKAGE_LOGGER).propagate is False


def test_repeated_installs_do_not_stack_handlers(tmp_path: Path) -> None:
    target = tmp_path / "hooks.log"
    environment = {PATH_VARIABLE: str(target)}
    logger = logging.getLogger(_PACKAGE_LOGGER)
    before = len(logger.handlers)

    assert install_hook_log_sink(environment) is True
    assert install_hook_log_sink(environment) is True
    assert install_hook_log_sink(environment) is True

    assert len(logger.handlers) == before + 1


def test_relative_path_is_refused(tmp_path: Path) -> None:
    logger = logging.getLogger(_PACKAGE_LOGGER)
    before = list(logger.handlers)

    assert install_hook_log_sink({PATH_VARIABLE: "hooks.log"}) is False
    assert logger.handlers == before


def test_unopenable_sink_degrades_instead_of_raising(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")

    assert install_hook_log_sink({PATH_VARIABLE: str(blocker / "hooks.log")}) is False


def test_configured_level_is_honoured(tmp_path: Path) -> None:
    target = tmp_path / "hooks.log"

    assert (
        install_hook_log_sink(
            {PATH_VARIABLE: str(target), LEVEL_VARIABLE: "error"},
        )
        is True
    )
    assert logging.getLogger(_PACKAGE_LOGGER).level == logging.ERROR


def test_unknown_level_falls_back_to_debug(tmp_path: Path) -> None:
    target = tmp_path / "hooks.log"

    assert (
        install_hook_log_sink(
            {PATH_VARIABLE: str(target), LEVEL_VARIABLE: "not-a-level"},
        )
        is True
    )
    assert logging.getLogger(_PACKAGE_LOGGER).level == logging.DEBUG
