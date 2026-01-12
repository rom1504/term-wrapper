"""End-to-end tests for terminal wrapper."""

import asyncio
import pytest
import httpx
import websockets
from multiprocessing import Process
import time
import uvicorn


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8001,
        log_level="error",
    )


@pytest.fixture(scope="module")
def server():
    """Start server for tests."""
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(2)  # Wait for server to start
    yield
    proc.terminate()
    proc.join()


@pytest.mark.asyncio
async def test_e2e_simple_command(server):
    """Test running a simple command end-to-end."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001") as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={"command": ["echo", "test123"], "rows": 24, "cols": 80},
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for output
        await asyncio.sleep(0.5)

        # Get output
        response = await client.get(f"/sessions/{session_id}/output")
        assert response.status_code == 200
        output = response.json()["output"]
        assert "test123" in output

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_e2e_interactive_cat(server):
    """Test interactive command with input/output."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001") as client:
        # Create session with cat command
        response = await client.post(
            "/sessions",
            json={"command": ["cat"], "rows": 24, "cols": 80},
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Write input
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "hello world\n"},
        )

        # Wait for echo
        await asyncio.sleep(0.3)

        # Get output
        response = await client.get(f"/sessions/{session_id}/output")
        assert response.status_code == 200
        output = response.json()["output"]
        assert "hello world" in output

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_e2e_websocket_interaction(server):
    """Test WebSocket interaction."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001") as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={"command": ["cat"], "rows": 24, "cols": 80},
        )
        session_id = response.json()["session_id"]

        # Connect via WebSocket
        ws_url = f"ws://127.0.0.1:8001/sessions/{session_id}/ws"

        async with websockets.connect(ws_url) as websocket:
            # Send input
            await websocket.send(b"websocket test\n")

            # Receive output
            received = []
            try:
                # Collect output for a short time
                async with asyncio.timeout(1.0):
                    while True:
                        message = await websocket.recv()
                        if isinstance(message, bytes):
                            received.append(message)
                        if b"websocket test" in b"".join(received):
                            break
            except asyncio.TimeoutError:
                pass

            output = b"".join(received).decode()
            assert "websocket test" in output

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_e2e_session_lifecycle(server):
    """Test complete session lifecycle."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001") as client:
        # List sessions (should be empty or from other tests)
        response = await client.get("/sessions")
        initial_count = len(response.json()["sessions"])

        # Create session
        response = await client.post(
            "/sessions",
            json={"command": ["sleep", "10"]},
        )
        session_id = response.json()["session_id"]

        # Verify session exists
        response = await client.get("/sessions")
        assert len(response.json()["sessions"]) == initial_count + 1

        # Get session info
        response = await client.get(f"/sessions/{session_id}")
        assert response.json()["alive"] == True

        # Delete session
        response = await client.delete(f"/sessions/{session_id}")
        assert response.status_code == 200

        # Verify deletion
        response = await client.get("/sessions")
        assert len(response.json()["sessions"]) == initial_count


@pytest.mark.asyncio
async def test_e2e_resize_terminal(server):
    """Test resizing terminal."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001") as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={"command": ["cat"], "rows": 24, "cols": 80},
        )
        session_id = response.json()["session_id"]

        # Check initial size
        response = await client.get(f"/sessions/{session_id}")
        info = response.json()
        assert info["rows"] == 24
        assert info["cols"] == 80

        # Resize
        response = await client.post(
            f"/sessions/{session_id}/resize",
            json={"rows": 40, "cols": 120},
        )
        assert response.status_code == 200

        # Verify resize
        response = await client.get(f"/sessions/{session_id}")
        info = response.json()
        assert info["rows"] == 40
        assert info["cols"] == 120

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_e2e_multiple_sessions(server):
    """Test managing multiple concurrent sessions."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001") as client:
        session_ids = []

        # Create multiple sessions
        for i in range(3):
            response = await client.post(
                "/sessions",
                json={"command": ["sleep", "10"]},
            )
            session_ids.append(response.json()["session_id"])

        # Verify all sessions exist
        response = await client.get("/sessions")
        sessions = response.json()["sessions"]
        for sid in session_ids:
            assert sid in sessions

        # Clean up all sessions
        for sid in session_ids:
            await client.delete(f"/sessions/{sid}")
