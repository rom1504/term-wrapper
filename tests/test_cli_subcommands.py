"""Unit tests for CLI subcommands."""

import json
import sys
from unittest.mock import Mock, patch, MagicMock
import pytest
from contextlib import contextmanager


@contextmanager
def mock_cli_environment():
    """Context manager that mocks both ServerManager and TerminalClient."""
    with patch("term_wrapper.cli.ServerManager") as MockServerManager:
        mock_server_manager = MockServerManager.return_value
        mock_server_manager.get_server_url.return_value = "http://localhost:8888"

        with patch("term_wrapper.cli.TerminalClient") as MockClient:
            yield MockClient, mock_server_manager


def test_cli_create_session():
    """Test 'create' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.create_session.return_value = "test-session-123"

        with patch("sys.argv", ["term-wrapper", "create", "bash", "-c", "ls"]):
            with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
                from term_wrapper.cli import sync_main
                sync_main()

                # Check that create_session was called with correct args
                mock_instance.create_session.assert_called_once()
                args, kwargs = mock_instance.create_session.call_args
                assert kwargs["command"] == ["bash", "-c", "ls"]
                assert kwargs["rows"] == 24  # default
                assert kwargs["cols"] == 80  # default


def test_cli_create_with_dimensions():
    """Test 'create' subcommand with custom rows/cols."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.create_session.return_value = "test-session-456"

        # Flags must come before command when using argparse.REMAINDER
        with patch("sys.argv", ["term-wrapper", "create", "--rows", "40", "--cols", "120", "vim"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                args, kwargs = mock_instance.create_session.call_args
                assert kwargs["command"] == ["vim"]
                assert kwargs["rows"] == 40
                assert kwargs["cols"] == 120


def test_cli_list_sessions():
    """Test 'list' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.list_sessions.return_value = ["session-1", "session-2"]

        with patch("sys.argv", ["term-wrapper", "list"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.list_sessions.assert_called_once()


def test_cli_get_info():
    """Test 'info' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.get_session_info.return_value = {
            "session_id": "test-123",
            "alive": True,
            "rows": 24,
            "cols": 80
        }

        with patch("sys.argv", ["term-wrapper", "info", "test-123"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.get_session_info.assert_called_once_with("test-123")


def test_cli_delete_session():
    """Test 'delete' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value

        with patch("sys.argv", ["term-wrapper", "delete", "test-123"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.delete_session.assert_called_once_with("test-123")


def test_cli_send_input():
    """Test 'send' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value

        with patch("sys.argv", ["term-wrapper", "send", "test-123", "hello\\nworld"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                # Check that escape sequences were processed
                mock_instance.write_input.assert_called_once_with("test-123", "hello\nworld")


def test_cli_send_input_with_enter():
    """Test 'send' subcommand with \\r (enter)."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value

        with patch("sys.argv", ["term-wrapper", "send", "test-123", "ls\\r"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.write_input.assert_called_once_with("test-123", "ls\r")


def test_cli_get_output():
    """Test 'get-output' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.get_output.return_value = "test output"

        with patch("sys.argv", ["term-wrapper", "get-output", "test-123"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                # Default is to clear buffer
                mock_instance.get_output.assert_called_once_with("test-123", clear=True)


def test_cli_get_output_no_clear():
    """Test 'get-output' subcommand with --no-clear."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.get_output.return_value = "test output"

        with patch("sys.argv", ["term-wrapper", "get-output", "test-123", "--no-clear"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.get_output.assert_called_once_with("test-123", clear=False)


def test_cli_get_text():
    """Test 'get-text' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.get_text.return_value = "clean text"

        with patch("sys.argv", ["term-wrapper", "get-text", "test-123"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                # Default is to strip ANSI and use output source
                mock_instance.get_text.assert_called_once_with(
                    "test-123",
                    strip_ansi_codes=True,
                    source="output"
                )


def test_cli_get_text_no_strip():
    """Test 'get-text' with --no-strip-ansi."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.get_text.return_value = "text with ansi"

        with patch("sys.argv", ["term-wrapper", "get-text", "test-123", "--no-strip-ansi"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.get_text.assert_called_once_with(
                    "test-123",
                    strip_ansi_codes=False,
                    source="output"
                )


def test_cli_get_text_screen_source():
    """Test 'get-text' with --source screen."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.get_text.return_value = "screen text"

        with patch("sys.argv", ["term-wrapper", "get-text", "test-123", "--source", "screen"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.get_text.assert_called_once_with(
                    "test-123",
                    strip_ansi_codes=True,
                    source="screen"
                )


def test_cli_get_screen():
    """Test 'get-screen' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.get_screen.return_value = {
            "lines": ["line1", "line2"],
            "rows": 24,
            "cols": 80,
            "cursor": {"row": 0, "col": 0}
        }

        with patch("sys.argv", ["term-wrapper", "get-screen", "test-123"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.get_screen.assert_called_once_with("test-123")


def test_cli_wait_text():
    """Test 'wait-text' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.wait_for_text.return_value = True

        with patch("sys.argv", ["term-wrapper", "wait-text", "test-123", "Welcome"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                # Default timeout and poll interval
                mock_instance.wait_for_text.assert_called_once_with(
                    "test-123",
                    "Welcome",
                    timeout=30,
                    poll_interval=0.5
                )


def test_cli_wait_text_custom_timeout():
    """Test 'wait-text' with custom timeout."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.wait_for_text.return_value = True

        with patch("sys.argv", ["term-wrapper", "wait-text", "test-123", "Welcome", "--timeout", "60"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.wait_for_text.assert_called_once_with(
                    "test-123",
                    "Welcome",
                    timeout=60,
                    poll_interval=0.5
                )


def test_cli_wait_quiet():
    """Test 'wait-quiet' subcommand."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.wait_for_quiet.return_value = True

        with patch("sys.argv", ["term-wrapper", "wait-quiet", "test-123"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                # Default duration and timeout
                mock_instance.wait_for_quiet.assert_called_once_with(
                    "test-123",
                    duration=2.0,
                    timeout=30
                )


def test_cli_wait_quiet_custom_duration():
    """Test 'wait-quiet' with custom duration."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.wait_for_quiet.return_value = True

        with patch("sys.argv", ["term-wrapper", "wait-quiet", "test-123", "--duration", "5", "--timeout", "60"]):
            with patch("sys.stdout", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                sync_main()

                mock_instance.wait_for_quiet.assert_called_once_with(
                    "test-123",
                    duration=5.0,
                    timeout=60
                )


def test_cli_timeout_error():
    """Test CLI handles TimeoutError correctly."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.wait_for_text.side_effect = TimeoutError("Text not found")

        with patch("sys.argv", ["term-wrapper", "wait-text", "test-123", "NotFound"]):
            with patch("sys.stderr", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                with pytest.raises(SystemExit) as exc:
                    sync_main()
                assert exc.value.code == 1


def test_cli_generic_error():
    """Test CLI handles generic errors correctly."""
    with mock_cli_environment() as (MockClient, _):
        mock_instance = MockClient.return_value
        mock_instance.create_session.side_effect = Exception("Connection failed")

        with patch("sys.argv", ["term-wrapper", "create", "bash"]):
            with patch("sys.stderr", new_callable=MagicMock):
                from term_wrapper.cli import sync_main
                with pytest.raises(SystemExit) as exc:
                    sync_main()
                assert exc.value.code == 1


def test_cli_web():
    """Test 'web' subcommand opens browser with existing session ID."""
    with mock_cli_environment() as (MockClient, MockServerManager):
        mock_instance = MockClient.return_value

        # Use valid UUID format for session ID
        test_session_id = "12345678-1234-1234-1234-123456789abc"

        with patch("sys.argv", ["term-wrapper", "web", test_session_id]):
            with patch("sys.stdout", new_callable=MagicMock):
                with patch("term_wrapper.cli.webbrowser.open") as mock_browser:
                    from term_wrapper.cli import sync_main
                    sync_main()

                    # Check that browser was opened with correct URL
                    mock_browser.assert_called_once_with(f"http://localhost:8888/?session={test_session_id}")


def test_cli_web_create_command():
    """Test 'web' subcommand creates session and opens browser when command is provided."""
    with mock_cli_environment() as (MockClient, MockServerManager):
        mock_instance = MockClient.return_value
        mock_instance.create_session.return_value = "new-session-uuid"

        with patch("sys.argv", ["term-wrapper", "web", "htop"]):
            with patch("sys.stdout", new_callable=MagicMock):
                with patch("term_wrapper.cli.webbrowser.open") as mock_browser:
                    from term_wrapper.cli import sync_main
                    sync_main()

                    # Check that create_session was called
                    mock_instance.create_session.assert_called_once_with(
                        command=["htop"],
                        rows=40,
                        cols=120
                    )

                    # Check that browser was opened with the new session
                    mock_browser.assert_called_once_with("http://localhost:8888/?session=new-session-uuid")
