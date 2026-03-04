"""Tests for task_scheduler_sdk — confirm, ask, choose with mocked stdin/stdout."""

import json
import os
from io import StringIO
from unittest.mock import patch

import pytest

from task_scheduler_sdk import ENV_MARKER, ask, choose, confirm, is_run_by_task_scheduler, output
from task_scheduler_sdk._protocol import InteractionError


class TestConfirm:
    """Tests for confirm()."""

    def test_confirm_true(self):
        response = json.dumps({"id": "test-id", "value": True})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            result = confirm("Deploy?")

        assert result is True
        sent = json.loads(mock_out.getvalue().strip())
        assert sent["_interactive"] is True
        assert sent["type"] == "confirm"
        assert sent["message"] == "Deploy?"

    def test_confirm_false(self):
        response = json.dumps({"id": "test-id", "value": False})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            result = confirm("Deploy?")

        assert result is False

    def test_confirm_with_default(self):
        response = json.dumps({"id": "test-id", "value": True, "timed_out": True})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            result = confirm("Deploy?", default=True)

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["default"] is True
        assert result is True

    def test_confirm_with_custom_id(self):
        response = json.dumps({"id": "my-id", "value": True})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
        ):
            result = confirm("Deploy?", id="my-id")

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["id"] == "my-id"


class TestAsk:
    """Tests for ask()."""

    def test_ask_returns_string(self):
        response = json.dumps({"id": "test-id", "value": "2.0.0"})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            result = ask("Version:")

        assert result == "2.0.0"

    def test_ask_with_default(self):
        response = json.dumps({"id": "test-id", "value": "1.0.0"})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            result = ask("Version:", default="1.0.0")

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["default"] == "1.0.0"


class TestChoose:
    """Tests for choose()."""

    def test_choose_returns_index(self):
        response = json.dumps({"id": "test-id", "value": 1})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            result = choose("Select env:", ["staging", "production"])

        assert result == 1

    def test_choose_sends_options(self):
        response = json.dumps({"id": "test-id", "value": 0})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            choose("Select:", ["a", "b", "c"])

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["options"] == ["a", "b", "c"]
        assert sent["type"] == "choice"


    def test_choose_sends_hidden_options(self):
        response = json.dumps({"id": "test-id", "value": 2})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            result = choose(
                "Pick:", ["Continue", "Retry"],
                hidden_options={"a": "Abort"},
            )

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["hidden_options"] == {"a": "Abort"}
        assert result == 2

    def test_choose_omits_hidden_options_when_none(self):
        response = json.dumps({"id": "test-id", "value": 0})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            choose("Pick:", ["a", "b"])

        sent = json.loads(mock_out.getvalue().strip())
        assert "hidden_options" not in sent


class TestErrorHandling:
    """Tests for error responses."""

    def test_error_response_raises(self):
        response = json.dumps({"id": "test-id", "error": "Timeout: no response"})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("task_scheduler_sdk._protocol._generate_id", return_value="test-id"),
        ):
            with pytest.raises(InteractionError, match="Timeout"):
                confirm("Deploy?")


class TestIsRunByTaskScheduler:
    """Tests for is_run_by_task_scheduler()."""

    def test_returns_true_when_env_set(self):
        """With TASK_SCHEDULER=1, returns True."""
        with patch.dict(os.environ, {ENV_MARKER: "1"}):
            assert is_run_by_task_scheduler() is True

    def test_returns_false_when_missing(self):
        """Without env var, returns False."""
        env = os.environ.copy()
        env.pop(ENV_MARKER, None)
        with patch.dict(os.environ, env, clear=True):
            assert is_run_by_task_scheduler() is False

    def test_returns_false_when_wrong_value(self):
        """With TASK_SCHEDULER=0, returns False."""
        with patch.dict(os.environ, {ENV_MARKER: "0"}):
            assert is_run_by_task_scheduler() is False


class TestOutput:
    """Tests for output()."""

    def test_output_sends_json_when_under_scheduler(self):
        """output() sends correct JSON protocol message when running under scheduler."""
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            output("Processing item 5 of 10")

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["_interactive"] is True
        assert sent["type"] == "output"
        assert sent["id"] == ""
        assert sent["message"] == "Processing item 5 of 10"

    def test_output_falls_back_to_print_when_not_under_scheduler(self, capsys):
        """output() prints directly when not running under scheduler."""
        env = os.environ.copy()
        env.pop(ENV_MARKER, None)
        with patch.dict(os.environ, env, clear=True):
            output("Hello world")

        captured = capsys.readouterr()
        assert captured.out == "Hello world\n"

    def test_output_does_not_read_stdin(self):
        """output() is fire-and-forget — never reads from stdin."""
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", new_callable=StringIO) as mock_in,
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            output("status update")

        # stdin should not have been read
        assert mock_in.tell() == 0

    def test_output_empty_string_produces_no_json(self):
        """output("") under scheduler produces no stdout — no JSON sent."""
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            output("")

        assert mock_out.getvalue() == ""

    def test_output_empty_string_prints_nothing_outside_scheduler(self, capsys):
        """output("") outside scheduler prints empty line (same as print(""))."""
        env = os.environ.copy()
        env.pop(ENV_MARKER, None)
        with patch.dict(os.environ, env, clear=True):
            output("")

        captured = capsys.readouterr()
        assert captured.out == "\n"
