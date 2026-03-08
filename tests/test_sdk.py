"""Tests for interactions_sdk — confirm, ask, choose with mocked stdin/stdout."""

import json
import os
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from interactions_sdk import (
    ENV_MARKER,
    AbortError,
    InteractionChoice,
    ask,
    ask_or_accept,
    choose,
    confirm,
    is_interactive,
    output,
    start_output_capture,
    stop_output_capture,
)
from interactions_sdk._protocol import InteractionError


# ---------------------------------------------------------------------------
# Helper: environment without the INTERACTIVE marker
# ---------------------------------------------------------------------------

def _env_without_marker() -> dict[str, str]:
    env = os.environ.copy()
    env.pop(ENV_MARKER, None)
    return env


# =========================================================================
# Interactive-mode tests (JSON protocol over stdin/stdout)
# =========================================================================

class TestConfirm:
    """Tests for confirm() in interactive mode."""

    def test_confirm_true(self):
        response = json.dumps({"id": "test-id", "value": True})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
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
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            result = confirm("Deploy?")

        assert result is False

    def test_confirm_with_default(self):
        response = json.dumps({"id": "test-id", "value": True, "timed_out": True})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
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
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            result = confirm("Deploy?", id="my-id")

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["id"] == "my-id"

    def test_confirm_raises_abort_on_none(self):
        response = json.dumps({"id": "test-id", "value": None})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            with pytest.raises(AbortError):
                confirm("Deploy?")


class TestAsk:
    """Tests for ask() in interactive mode."""

    def test_ask_returns_string(self):
        response = json.dumps({"id": "test-id", "value": "2.0.0"})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            result = ask("Version:")

        assert result == "2.0.0"

    def test_ask_with_default(self):
        response = json.dumps({"id": "test-id", "value": "1.0.0"})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            result = ask("Version:", default="1.0.0")

        sent = json.loads(mock_out.getvalue().strip())
        assert sent["default"] == "1.0.0"

    def test_ask_raises_abort_on_none(self):
        response = json.dumps({"id": "test-id", "value": None})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            with pytest.raises(AbortError):
                ask("Version:")


class TestChoose:
    """Tests for choose() in interactive mode."""

    def test_choose_returns_index(self):
        response = json.dumps({"id": "test-id", "value": 1})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            result = choose("Select env:", ["staging", "production"])

        assert result == 1

    def test_choose_sends_options(self):
        response = json.dumps({"id": "test-id", "value": 0})
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
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
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
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
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            choose("Pick:", ["a", "b"])

        sent = json.loads(mock_out.getvalue().strip())
        assert "hidden_options" not in sent

    def test_choose_raises_abort_on_none(self):
        response = json.dumps({"id": "test-id", "value": None})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            with pytest.raises(AbortError):
                choose("Pick:", ["a", "b"])


class TestErrorHandling:
    """Tests for error responses."""

    def test_error_response_raises(self):
        response = json.dumps({"id": "test-id", "error": "Timeout: no response"})
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", StringIO(response + "\n")),
            patch("interactions_sdk._protocol._generate_id", return_value="test-id"),
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            with pytest.raises(InteractionError, match="Timeout"):
                confirm("Deploy?")


class TestIsInteractive:
    """Tests for is_interactive()."""

    def test_returns_true_when_env_set(self):
        with patch.dict(os.environ, {ENV_MARKER: "1"}):
            assert is_interactive() is True

    def test_returns_false_when_missing(self):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert is_interactive() is False

    def test_returns_false_when_wrong_value(self):
        with patch.dict(os.environ, {ENV_MARKER: "0"}):
            assert is_interactive() is False


# =========================================================================
# Output tests
# =========================================================================

class TestOutput:
    """Tests for output()."""

    def test_output_sends_json_when_under_scheduler(self):
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
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            output("Hello world")

        captured = capsys.readouterr()
        assert captured.out == "Hello world\n"

    def test_output_does_not_read_stdin(self):
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", new_callable=StringIO) as mock_in,
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            output("status update")

        assert mock_in.tell() == 0

    def test_output_empty_string_produces_no_json(self):
        with (
            patch("sys.stdout", new_callable=StringIO) as mock_out,
            patch.dict(os.environ, {ENV_MARKER: "1"}),
        ):
            output("")

        assert mock_out.getvalue() == ""

    def test_output_empty_string_prints_nothing_outside_scheduler(self, capsys):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            output("")

        captured = capsys.readouterr()
        assert captured.out == "\n"

    def test_output_unicode_safety(self):
        """output() should not crash on unencodable characters in CLI mode."""
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            with patch("builtins.print", side_effect=[UnicodeEncodeError("ascii", "", 0, 1, "bad"), None]) as mock_print:
                output("Hello \u2603 world")

        # Second call should be the ascii-safe fallback
        assert mock_print.call_count == 2


# =========================================================================
# CLI fallback tests (no INTERACTIVE env var)
# =========================================================================

class TestConfirmCLI:
    """Tests for confirm() CLI fallback."""

    @patch("builtins.input", return_value="y")
    def test_cli_confirm_yes(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert confirm("Continue?") is True

    @patch("builtins.input", return_value="n")
    def test_cli_confirm_no(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert confirm("Continue?", default=True) is False

    @patch("builtins.input", return_value="")
    def test_cli_confirm_empty_uses_default_true(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert confirm("Continue?", default=True) is True

    @patch("builtins.input", return_value="")
    def test_cli_confirm_empty_uses_default_false(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert confirm("Continue?", default=False) is False

    @patch("builtins.input", return_value="")
    def test_cli_confirm_empty_no_default_returns_false(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert confirm("Continue?") is False

    @patch("builtins.input", return_value="yes")
    def test_cli_confirm_yes_word(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert confirm("Continue?") is True

    @patch("builtins.input", return_value="Y")
    def test_cli_confirm_uppercase(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert confirm("Continue?") is True

    @patch("builtins.input", return_value="")
    def test_cli_confirm_hint_with_default_true(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            confirm("Continue?", default=True)
        mock_input.assert_called_once_with("Continue? [Y/n]: ")

    @patch("builtins.input", return_value="")
    def test_cli_confirm_hint_with_default_false(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            confirm("Continue?", default=False)
        mock_input.assert_called_once_with("Continue? [y/N]: ")

    @patch("builtins.input", return_value="")
    def test_cli_confirm_hint_with_no_default(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            confirm("Continue?")
        mock_input.assert_called_once_with("Continue? [y/n]: ")


class TestAskCLI:
    """Tests for ask() CLI fallback."""

    @patch("builtins.input", return_value="custom")
    def test_cli_ask_returns_input(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert ask("Name:") == "custom"

    @patch("builtins.input", return_value="")
    def test_cli_ask_empty_returns_default(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert ask("Name:", default="Alice") == "Alice"

    @patch("builtins.input", return_value="")
    def test_cli_ask_empty_no_default_returns_empty(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert ask("Name:") == ""

    @patch("builtins.input", return_value="")
    def test_cli_ask_prompt_shows_default(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            ask("Name:", default="Alice")
        mock_input.assert_called_once_with("Name: [Alice]: ")

    @patch("builtins.input", return_value="")
    def test_cli_ask_prompt_no_default(self, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            ask("Name:")
        mock_input.assert_called_once_with("Name:: ")


class TestChooseCLI:
    """Tests for choose() CLI fallback."""

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_cli_choose_empty_returns_default(self, mock_print: MagicMock, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert choose("Pick:", ["a", "b", "c"], default=1) == 1

    @patch("builtins.input", return_value="2")
    @patch("builtins.print")
    def test_cli_choose_returns_selected_index(self, mock_print: MagicMock, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert choose("Pick:", ["a", "b", "c"], default=0) == 2

    @patch("builtins.input", return_value="a")
    @patch("builtins.print")
    def test_cli_choose_hidden_shortcut(self, mock_print: MagicMock, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            result = choose("Pick:", ["x", "y"], default=0, hidden_options={"a": "Abort"})
        assert result == 2  # len(["x", "y"]) + 0

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_cli_choose_shows_hidden_hint(self, mock_print: MagicMock, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            choose("Pick:", ["x", "y"], default=0, hidden_options={"a": "Abort"})
        printed = [str(c) for c in mock_print.call_args_list]
        assert any("a=Abort" in line for line in printed)

    @patch("builtins.input", side_effect=["bad", "0"])
    @patch("builtins.print")
    def test_cli_choose_retries_on_invalid(self, mock_print: MagicMock, mock_input: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            assert choose("Pick:", ["a", "b"], default=None) == 0


# =========================================================================
# Output capture tests
# =========================================================================

class TestOutputCapture:
    """Tests for start_output_capture / stop_output_capture."""

    def test_capture_collects_output(self):
        import interactions_sdk as sdk
        old_buf = sdk._capture_buffer
        old_silent = sdk._capture_silent
        try:
            start_output_capture()
            with patch.dict(os.environ, _env_without_marker(), clear=True):
                with patch("builtins.print"):
                    output("line1")
                    output("line2")
            result = stop_output_capture()
            assert result == "line1\nline2"
        finally:
            sdk._capture_buffer = old_buf
            sdk._capture_silent = old_silent

    def test_capture_silent_suppresses_output(self):
        import interactions_sdk as sdk
        old_buf = sdk._capture_buffer
        old_silent = sdk._capture_silent
        try:
            start_output_capture(silent=True)
            mock_print = MagicMock()
            with patch.dict(os.environ, _env_without_marker(), clear=True):
                with patch("builtins.print", mock_print):
                    output("hidden")
            mock_print.assert_not_called()
            result = stop_output_capture()
            assert result == "hidden"
        finally:
            sdk._capture_buffer = old_buf
            sdk._capture_silent = old_silent

    def test_stop_capture_resets_state(self):
        import interactions_sdk as sdk
        old_buf = sdk._capture_buffer
        old_silent = sdk._capture_silent
        try:
            start_output_capture(silent=True)
            stop_output_capture()
            assert sdk._capture_buffer is None
            assert sdk._capture_silent is False
        finally:
            sdk._capture_buffer = old_buf
            sdk._capture_silent = old_silent

    def test_stop_capture_returns_empty_when_nothing_captured(self):
        import interactions_sdk as sdk
        old_buf = sdk._capture_buffer
        old_silent = sdk._capture_silent
        try:
            start_output_capture()
            result = stop_output_capture()
            assert result == ""
        finally:
            sdk._capture_buffer = old_buf
            sdk._capture_silent = old_silent


# =========================================================================
# ask_or_accept tests
# =========================================================================

class TestAskOrAccept:
    """Tests for ask_or_accept helper."""

    @patch("interactions_sdk.ask")
    @patch("interactions_sdk.choose", return_value=0)
    def test_accept_returns_default(self, mock_choose: MagicMock, mock_ask: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            result = ask_or_accept("Title:", default="My Todo")
        assert result == "My Todo"
        mock_choose.assert_called_once_with("Title: My Todo", ["Accept", "Edit"], default=0)
        mock_ask.assert_not_called()

    @patch("interactions_sdk.ask", return_value="Edited Title")
    @patch("interactions_sdk.choose", return_value=1)
    def test_edit_delegates_to_ask(self, mock_choose: MagicMock, mock_ask: MagicMock):
        with patch.dict(os.environ, _env_without_marker(), clear=True):
            result = ask_or_accept("Title:", default="My Todo")
        assert result == "Edited Title"
        mock_ask.assert_called_once_with("Title:", default="My Todo")


# =========================================================================
# InteractionChoice tests
# =========================================================================

class TestInteractionChoice:
    """Tests for InteractionChoice class."""

    @patch("interactions_sdk.choose", return_value=0)
    def test_returns_action_key(self, mock_choose: MagicMock):
        ic = InteractionChoice("Action:", [("A", "a_key"), ("B", "b_key")])
        result = ic.choose()
        assert result == "a_key"

    @patch("interactions_sdk.choose", return_value=2)
    def test_abort_returns_abort_action(self, mock_choose: MagicMock):
        ic = InteractionChoice("Action:", [("A", "a_key"), ("B", "b_key")], abort=True)
        result = ic.choose()
        assert result == "abort"
        mock_choose.assert_called_once_with(
            "Action:", ["A", "B"], default=0, hidden_options={"a": "Abort"},
        )

    @patch("interactions_sdk.choose", return_value=0)
    def test_normal_choice_with_abort_enabled(self, mock_choose: MagicMock):
        ic = InteractionChoice("Action:", [("A", "a_key"), ("B", "b_key")], abort=True)
        result = ic.choose()
        assert result == "a_key"

    @patch("interactions_sdk.choose", return_value=1)
    def test_custom_default(self, mock_choose: MagicMock):
        ic = InteractionChoice("Action:", [("A", "a_key"), ("B", "b_key")], default=1)
        ic.choose()
        mock_choose.assert_called_once_with(
            "Action:", ["A", "B"], default=1, hidden_options=None,
        )

    @patch("interactions_sdk.choose", return_value=0)
    def test_no_abort_no_hidden_options(self, mock_choose: MagicMock):
        ic = InteractionChoice("Action:", [("A", "a_key")])
        ic.choose()
        mock_choose.assert_called_once_with(
            "Action:", ["A"], default=0, hidden_options=None,
        )
