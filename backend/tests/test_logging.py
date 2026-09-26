import json
import logging

from app.logging_config import JsonFormatter, request_id_var


def test_json_formatter_emits_request_id_and_extras():
    token = request_id_var.set("rid-42")
    try:
        record = logging.LogRecord(
            "app.test", logging.INFO, __file__, 1, "hello %s", ("world",), None
        )
        record_extra = {"path": "/api/complaints", "status": 201}
        for key, value in record_extra.items():
            setattr(record, key, value)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)

    assert payload["request_id"] == "rid-42"
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["path"] == "/api/complaints"
    assert payload["status"] == 201
    assert "ts" in payload


def test_json_formatter_is_valid_json_for_exceptions():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "app.test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["level"] == "ERROR"
    assert "ValueError: boom" in payload["exc"]
