"""End-to-end tests for CLI subcommands with htop."""

import subprocess
import time
import json
import pytest
from multiprocessing import Process
import uvicorn
import httpx


BASE_URL = "http://localhost:8008"


def run_server():
    """Run the FastAPI server for testing."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8008,
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


def test_htop_get_screen(server):
    """Test getting htop screen buffer via CLI."""
    # Create htop session sorted by memory
    result = run_cli(["create", "--rows", "40", "--cols", "150", "--env", '{"TERM":"xterm-256color"}', "htop", "-C", "--sort-key=PERCENT_MEM"])
    assert result.returncode == 0
    session_id = json.loads(result.stdout)["session_id"]

    try:
        # Wait for htop to render
        time.sleep(2)

        # Get screen buffer
        result = run_cli(["get-screen", session_id])
        assert result.returncode == 0

        screen = json.loads(result.stdout)
        assert "lines" in screen
        assert "rows" in screen
        assert "cols" in screen
        assert screen["rows"] == 40
        assert screen["cols"] == 150

        lines = screen["lines"]
        assert isinstance(lines, list)
        assert len(lines) == 40

        # Check that htop output contains expected elements
        text = "\n".join(lines)
        assert "PID" in text or "CPU" in text or "MEM" in text

    finally:
        # Send 'q' to quit htop
        run_cli(["send", session_id, "q"])
        time.sleep(0.5)
        run_cli(["delete", session_id])


def test_htop_parse_processes(server):
    """Test parsing top memory processes from htop using CLI."""
    # Create htop session
    result = run_cli(["create", "--rows", "40", "--cols", "150", "--env", '{"TERM":"xterm-256color"}', "htop", "-C", "--sort-key=PERCENT_MEM"])
    assert result.returncode == 0
    session_id = json.loads(result.stdout)["session_id"]

    try:
        # Wait for htop
        time.sleep(2.5)

        # Get screen buffer
        result = run_cli(["get-screen", session_id])
        assert result.returncode == 0

        screen = json.loads(result.stdout)
        lines = screen["lines"]

        # Find header line
        header_idx = None
        for i, line in enumerate(lines):
            if "PID" in line and "MEM%" in line:
                header_idx = i
                break

        # Should find header
        assert header_idx is not None

        # Parse at least a few process lines
        processes = []
        for line in lines[header_idx + 1:]:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 10:
                try:
                    pid = int(parts[0])
                    user = parts[1]
                    mem = float(parts[9].rstrip('%'))
                    cmd = ' '.join(parts[10:]) if len(parts) > 10 else ''

                    if mem > 0:
                        processes.append({
                            'pid': pid,
                            'user': user,
                            'mem': mem,
                            'cmd': cmd
                        })
                except (ValueError, IndexError):
                    continue

        # Should find at least some processes
        assert len(processes) > 0

        # Get top 5
        top5 = sorted(processes, key=lambda x: x['mem'], reverse=True)[:5]
        assert len(top5) > 0

        # Verify they have reasonable values
        for p in top5:
            assert p['pid'] > 0
            assert p['mem'] >= 0
            assert isinstance(p['user'], str)

    finally:
        run_cli(["send", session_id, "q"])
        time.sleep(0.5)
        run_cli(["delete", session_id])


def test_htop_wait_quiet(server):
    """Test wait-quiet with htop (expects timeout since htop constantly updates)."""
    # Create htop session
    result = run_cli(["create", "--env", '{"TERM":"xterm-256color"}', "htop"])
    assert result.returncode == 0
    session_id = json.loads(result.stdout)["session_id"]

    try:
        # htop constantly updates, so wait-quiet should timeout
        # We need a custom subprocess call with longer timeout
        cmd = ["uv", "run", "python", "-m", "term_wrapper.cli", "--url", BASE_URL,
               "wait-quiet", session_id, "--duration", "2", "--timeout", "5"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        # Should exit with error code due to timeout
        assert result.returncode == 1
        # Should have error message in stderr
        error_data = json.loads(result.stderr)
        assert "error" in error_data

    finally:
        run_cli(["send", session_id, "q"])
        time.sleep(0.5)
        run_cli(["delete", session_id])
