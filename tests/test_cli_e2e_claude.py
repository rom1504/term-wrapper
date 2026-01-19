"""End-to-end tests for CLI subcommands with Claude Code."""

import subprocess
import time
import os
import json
import pytest
import tempfile
from multiprocessing import Process
import uvicorn
import httpx


BASE_URL = "http://localhost:8009"


def run_server():
    """Run the FastAPI server for testing."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8009,
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


def run_cli(args, timeout=10):
    """Helper to run CLI commands."""
    cmd = ["uv", "run", "python", "-m", "term_wrapper.cli", "--url", BASE_URL] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result


def test_claude_interactive_session(server):
    """Test full interactive Claude Code session using CLI subcommands."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Claude Code session
        result = run_cli(["create", "--rows", "40", "--cols", "120", "bash", "-c", f"cd {tmpdir} && claude"])
        assert result.returncode == 0
        session_id = json.loads(result.stdout)["session_id"]

        try:
            # Step 1: Wait for trust prompt
            result = run_cli(["wait-text", session_id, "Do you trust", "--timeout", "10"])
            assert result.returncode == 0
            found = json.loads(result.stdout)["found"]
            assert found == True

            # Accept trust prompt
            result = run_cli(["send", session_id, "\\r"])
            assert result.returncode == 0

            # Wait for main UI
            result = run_cli(["wait-text", session_id, "Welcome", "--timeout", "10"])
            assert result.returncode == 0

            # Step 2: Submit request
            request = "create test.txt that contains hello world"
            result = run_cli(["send", session_id, request])
            assert result.returncode == 0

            result = run_cli(["send", session_id, "\\r"])
            assert result.returncode == 0

            # Step 3: Wait a bit for Claude to process and potentially generate code
            time.sleep(5)

            # Get current text to see state
            result = run_cli(["get-text", session_id])
            text = result.stdout.lower()

            # If there's an approval UI, approve it
            if "esc to cancel" in text or "tab to add" in text or "enter" in text:
                # Wait for UI to stabilize
                time.sleep(2)
                # Approve with Enter
                result = run_cli(["send", session_id, "\\r"])
                assert result.returncode == 0
                time.sleep(2)

            # Wait more for potential file creation
            time.sleep(5)

            # Verify file was created
            files = os.listdir(tmpdir)
            txt_files = [f for f in files if f.endswith('.txt')]
            assert len(txt_files) > 0

            # Check file content
            filepath = os.path.join(tmpdir, txt_files[0])
            with open(filepath) as f:
                content = f.read()
                assert "hello world" in content.lower()

        finally:
            run_cli(["delete", session_id])


def test_claude_wait_for_text(server):
    """Test wait-text with Claude Code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_cli(["create", "bash", "-c", f"cd {tmpdir} && claude"])
        assert result.returncode == 0
        session_id = json.loads(result.stdout)["session_id"]

        try:
            # Wait for trust prompt
            result = run_cli(["wait-text", session_id, "Do you trust", "--timeout", "10"])
            assert result.returncode == 0
            assert json.loads(result.stdout)["found"] == True

        finally:
            run_cli(["delete", session_id])


def test_claude_get_text(server):
    """Test get-text with Claude Code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_cli(["create", "bash", "-c", f"cd {tmpdir} && claude"])
        assert result.returncode == 0
        session_id = json.loads(result.stdout)["session_id"]

        try:
            # Wait for UI to load
            time.sleep(3)

            # Get clean text
            result = run_cli(["get-text", session_id])
            assert result.returncode == 0
            text = result.stdout

            # Should contain Claude UI elements
            assert "Claude" in text or "trust" in text.lower()

        finally:
            run_cli(["delete", session_id])
