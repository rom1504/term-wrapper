"""End-to-end tests for CLI subcommands with vim."""

import subprocess
import time
import tempfile
import os
import json
import pytest
from multiprocessing import Process
import uvicorn
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


def run_cli(args):
    """Helper to run CLI commands."""
    cmd = ["uv", "run", "python", "-m", "term_wrapper.cli", "--url", BASE_URL] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10
    )
    return result


def test_vim_create_file_via_cli(server):
    """Test creating a file with vim using CLI subcommands."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.txt")

        # Create session with vim
        result = run_cli(["create", "vim", filepath])
        assert result.returncode == 0
        session_data = json.loads(result.stdout)
        session_id = session_data["session_id"]

        try:
            # Wait for vim to load
            time.sleep(1)

            # Enter insert mode
            result = run_cli(["send", session_id, "i"])
            assert result.returncode == 0

            time.sleep(0.3)

            # Type some text
            text = "Hello from CLI!\\nLine 2\\nLine 3"
            result = run_cli(["send", session_id, text])
            assert result.returncode == 0

            time.sleep(0.5)

            # Exit insert mode (ESC)
            result = run_cli(["send", session_id, "\\x1b"])
            assert result.returncode == 0

            time.sleep(0.3)

            # Save and quit
            result = run_cli(["send", session_id, ":wq\\r"])
            assert result.returncode == 0

            time.sleep(1)

            # Verify file was created
            assert os.path.exists(filepath)
            with open(filepath) as f:
                content = f.read()
                assert "Hello from CLI!" in content
                assert "Line 2" in content
                assert "Line 3" in content

        finally:
            # Cleanup session
            run_cli(["delete", session_id])


def test_vim_wait_for_text(server):
    """Test wait-text with vim."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test2.txt")

        # Create session
        result = run_cli(["create", "vim", filepath])
        assert result.returncode == 0
        session_id = json.loads(result.stdout)["session_id"]

        try:
            # Wait for vim UI to appear (wait for specific vim text)
            result = run_cli(["wait-text", session_id, filepath, "--timeout", "10"])
            assert result.returncode == 0
            result_data = json.loads(result.stdout)
            assert result_data["found"] == True

        finally:
            run_cli(["delete", session_id])


def test_vim_get_text(server):
    """Test get-text with vim."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test3.txt")

        # Create session
        result = run_cli(["create", "vim", filepath])
        assert result.returncode == 0
        session_id = json.loads(result.stdout)["session_id"]

        try:
            time.sleep(1)

            # Get clean text
            result = run_cli(["get-text", session_id])
            assert result.returncode == 0
            text = result.stdout

            # Vim output should contain the filename
            assert filepath in text or "test3.txt" in text

        finally:
            run_cli(["delete", session_id])


def test_vim_list_and_info(server):
    """Test list and info commands."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test4.txt")

        # Create session
        result = run_cli(["create", "vim", filepath])
        assert result.returncode == 0
        session_id = json.loads(result.stdout)["session_id"]

        try:
            # List sessions
            result = run_cli(["list"])
            assert result.returncode == 0
            sessions = json.loads(result.stdout)["sessions"]
            assert session_id in sessions

            # Get info
            result = run_cli(["info", session_id])
            assert result.returncode == 0
            info = json.loads(result.stdout)
            assert info["session_id"] == session_id
            assert info["alive"] == True

        finally:
            run_cli(["delete", session_id])
