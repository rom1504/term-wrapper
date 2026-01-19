"""E2E tests for htop running in the terminal wrapper."""

import asyncio
import pytest
import httpx
import time
from multiprocessing import Process
import uvicorn


BASE_URL = "http://localhost:8005"


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8005,
        log_level="error",
    )


@pytest.fixture(scope="module")
def server():
    """Start server for tests."""
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(2)
    yield
    proc.terminate()
    proc.join(timeout=5)


@pytest.mark.asyncio
async def test_htop_basic_launch(server):
    """Test launching htop in the terminal wrapper."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create htop session
        response = await client.post("/sessions", json={
            "command": ["htop", "--version"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
            }
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for htop version output
        await asyncio.sleep(1.0)

        # Get output
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]

        # htop --version should output version information
        assert "htop" in output.lower()

        # Cleanup
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_htop_interactive_mode(server):
    """Test launching htop in interactive mode."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create htop session
        response = await client.post("/sessions", json={
            "command": ["htop"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for htop to start
        await asyncio.sleep(1.0)

        # Get output
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]

        # htop should render its interface with ANSI codes
        assert len(output) > 100  # Should have substantial output
        # Look for common htop indicators (ANSI escape sequences, CPU, MEM, etc.)
        assert "\x1b[" in output or "CPU" in output or "MEM" in output

        # Send 'q' to quit
        await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
        await asyncio.sleep(0.5)

        # Cleanup
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_htop_navigation(server):
    """Test navigating htop with keyboard input."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create htop session
        response = await client.post("/sessions", json={
            "command": ["htop"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
            }
        })

        session_id = response.json()["session_id"]
        await asyncio.sleep(1.0)

        # Clear initial output
        await client.get(f"/sessions/{session_id}/output")

        # Send arrow down
        await client.post(f"/sessions/{session_id}/input", json={"data": "\x1b[B"})
        await asyncio.sleep(0.2)

        # Send arrow up
        await client.post(f"/sessions/{session_id}/input", json={"data": "\x1b[A"})
        await asyncio.sleep(0.2)

        # Get output after navigation
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]

        # Should have received some updates
        assert len(output) > 0

        # Quit
        await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
        await asyncio.sleep(0.5)

        # Cleanup
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_htop_help_screen(server):
    """Test opening htop help screen."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create htop session
        response = await client.post("/sessions", json={
            "command": ["htop"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
            }
        })

        session_id = response.json()["session_id"]
        await asyncio.sleep(1.0)

        # Clear initial output
        await client.get(f"/sessions/{session_id}/output")

        # Press F1 or 'h' for help
        await client.post(f"/sessions/{session_id}/input", json={"data": "h"})
        await asyncio.sleep(0.5)

        # Get help screen output
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]

        # Help screen should have substantial output
        assert len(output) > 50

        # Close help (typically ESC or q)
        await client.post(f"/sessions/{session_id}/input", json={"data": "\x1b"})
        await asyncio.sleep(0.2)

        # Quit htop
        await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
        await asyncio.sleep(0.5)

        # Cleanup
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_htop_resize(server):
    """Test resizing htop terminal."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create htop session with initial size
        response = await client.post("/sessions", json={
            "command": ["htop"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
            }
        })

        session_id = response.json()["session_id"]
        await asyncio.sleep(1.0)

        # Resize terminal
        response = await client.post(f"/sessions/{session_id}/resize", json={
            "rows": 40,
            "cols": 120
        })
        assert response.status_code == 200

        await asyncio.sleep(0.5)

        # htop should adapt to new size
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]

        # Should have received updates after resize
        assert len(output) > 0

        # Quit
        await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
        await asyncio.sleep(0.5)

        # Cleanup
        await client.delete(f"/sessions/{session_id}")
