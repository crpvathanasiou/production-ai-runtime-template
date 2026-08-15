"""Focused tests for rendered operational logging."""

from __future__ import annotations

import json
import logging

from app.core.logging import format_operational_log


def assert_visible_correlation(
    message: str,
    *,
    request_id: str,
    run_id: str,
    node_name: str,
    event: str,
    thread_id: str | None = None,
) -> None:
    """Assert correlation fields are visible in the rendered log message."""
    assert event in message
    assert request_id in message
    assert run_id in message
    assert node_name in message
    if thread_id is not None:
        assert thread_id in message
        assert '"thread_id"' in message
    else:
        assert '"thread_id"' not in message


def test_format_operational_log_renders_required_fields():
    message = format_operational_log(
        "demo.event",
        request_id="req-1",
        run_id="run-1",
        thread_id="thread-1",
        node_name="demo",
        status="ok",
        count=2,
    )

    payload = json.loads(message)
    assert payload["event"] == "demo.event"
    assert payload["request_id"] == "req-1"
    assert payload["run_id"] == "run-1"
    assert payload["thread_id"] == "thread-1"
    assert payload["node_name"] == "demo"
    assert payload["status"] == "ok"
    assert payload["count"] == 2
    assert_visible_correlation(
        message,
        request_id="req-1",
        run_id="run-1",
        node_name="demo",
        event="demo.event",
        thread_id="thread-1",
    )


def test_format_operational_log_omits_none_thread_id():
    message = format_operational_log(
        "demo.event",
        request_id="req-2",
        run_id="run-2",
        thread_id=None,
        node_name="demo",
        optional=None,
    )

    payload = json.loads(message)
    assert "thread_id" not in payload
    assert "optional" not in payload
    assert_visible_correlation(
        message,
        request_id="req-2",
        run_id="run-2",
        node_name="demo",
        event="demo.event",
        thread_id=None,
    )


def test_format_operational_log_message_is_what_logger_records(caplog):
    logger = logging.getLogger("tests.operational_logging")
    with caplog.at_level(logging.INFO, logger="tests.operational_logging"):
        logger.info(
            format_operational_log(
                "demo.logged",
                request_id="req-3",
                run_id="run-3",
                node_name="demo",
                decision="allow",
            )
        )

    assert len(caplog.records) == 1
    rendered = caplog.records[0].getMessage()
    assert_visible_correlation(
        rendered,
        request_id="req-3",
        run_id="run-3",
        node_name="demo",
        event="demo.logged",
        thread_id=None,
    )
    assert "allow" in rendered
