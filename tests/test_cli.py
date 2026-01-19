"""Unit tests for CLI client."""

import pytest
import time
from multiprocessing import Process
import uvicorn
from term_wrapper.cli import TerminalClient
import httpx


BASE_URL = "http://localhost:8007"


def run_server():
    """Run the FastAPI server for testing."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8007,
        log_level="error",
    )


@pytest.fixture(scope="module")
def server():
    """Start server for tests."""
    proc = Process(target=run_server, daemon=True)
    proc.start()

    # Wait for server to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            resp = httpx.get(f"{BASE_URL}/health", timeout=1.0)
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("Server failed to start")

    yield
    proc.terminate()
    proc.join(timeout=5)


@pytest.fixture
def client(server):
    """Create TerminalClient instance with increased timeout."""
    client = TerminalClient(base_url=BASE_URL)
    # Increase timeout to 30 seconds
    client.http_client.timeout = httpx.Timeout(30.0)
    yield client
    client.close()


def test_create_session(client):
    """Test creating a session via TerminalClient."""
    session_id = client.create_session(command=["echo", "test"], rows=24, cols=80)
    assert isinstance(session_id, str)
    assert len(session_id) > 0

    # Cleanup
    client.delete_session(session_id)


def test_list_sessions(client):
    """Test listing sessions."""
    session_id = client.create_session(command=["cat"])

    sessions = client.list_sessions()
    assert isinstance(sessions, list)
    assert session_id in sessions

    # Cleanup
    client.delete_session(session_id)


def test_get_session_info(client):
    """Test getting session info."""
    session_id = client.create_session(command=["cat"], rows=30, cols=100)

    info = client.get_session_info(session_id)
    assert info["session_id"] == session_id
    assert "alive" in info
    assert info["rows"] == 30
    assert info["cols"] == 100

    # Cleanup
    client.delete_session(session_id)


def test_write_input(client):
    """Test writing input to terminal."""
    session_id = client.create_session(command=["cat"])

    # Should not raise
    client.write_input(session_id, "test input\n")

    # Cleanup
    client.delete_session(session_id)


def test_get_output(client):
    """Test getting terminal output."""
    session_id = client.create_session(
        command=["sh", "-c", "echo 'test output'; sleep 0.5"]
    )

    time.sleep(1)
    output = client.get_output(session_id)

    assert isinstance(output, str)
    assert "test output" in output

    # Cleanup
    client.delete_session(session_id)


def test_get_screen(client):
    """Test getting parsed screen buffer."""
    # Create session with simple output
    session_id = client.create_session(
        command=["sh", "-c", "echo 'Line 1'; echo 'Line 2'; echo 'Line 3'; sleep 1"],
        rows=10,
        cols=40
    )

    time.sleep(0.5)
    screen_data = client.get_screen(session_id)

    # Verify structure
    assert "lines" in screen_data
    assert "rows" in screen_data
    assert "cols" in screen_data
    assert "cursor" in screen_data

    # Verify dimensions
    assert screen_data["rows"] == 10
    assert screen_data["cols"] == 40

    # Verify cursor
    assert "row" in screen_data["cursor"]
    assert "col" in screen_data["cursor"]

    # Verify lines
    lines = screen_data["lines"]
    assert isinstance(lines, list)
    assert len(lines) == 10

    # Check output content
    assert any("Line 1" in line for line in lines)
    assert any("Line 2" in line for line in lines)
    assert any("Line 3" in line for line in lines)

    # Cleanup
    client.delete_session(session_id)


def test_get_screen_with_ansi_codes(client):
    """Test that get_screen handles ANSI codes properly."""
    # Create session with ANSI color codes
    session_id = client.create_session(
        command=["sh", "-c", "echo -e '\\x1b[31mRed Text\\x1b[0m Normal'; sleep 1"],
        rows=10,
        cols=40
    )

    time.sleep(0.5)
    screen_data = client.get_screen(session_id)
    lines = screen_data["lines"]

    # ANSI codes should be stripped, only text remains
    assert any("Red Text" in line and "Normal" in line for line in lines)

    # Cleanup
    client.delete_session(session_id)


def test_get_screen_vs_get_output(client):
    """Test difference between get_screen and get_output."""
    # Create session with cursor positioning
    session_id = client.create_session(
        command=["sh", "-c", "echo -e 'Line 1\\nLine 2\\nLine 3'; sleep 1"],
        rows=10,
        cols=40
    )

    time.sleep(0.5)

    # Get raw output (has ANSI codes)
    raw_output = client.get_output(session_id, clear=False)

    # Get screen (parsed)
    screen_data = client.get_screen(session_id)
    lines = screen_data["lines"]

    # Both should contain the text
    assert "Line 1" in raw_output
    assert any("Line 1" in line for line in lines)

    # Screen should be structured as list
    assert isinstance(lines, list)

    # Raw output is a string
    assert isinstance(raw_output, str)

    # Cleanup
    client.delete_session(session_id)


def test_delete_session(client):
    """Test deleting a session."""
    session_id = client.create_session(command=["echo", "test"])

    # Give it time to start
    time.sleep(0.5)

    # Verify session exists
    info = client.get_session_info(session_id)
    assert info["session_id"] == session_id

    # Delete should not raise
    client.delete_session(session_id)
