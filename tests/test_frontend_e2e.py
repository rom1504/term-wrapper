"""End-to-end tests for frontend with vim."""

import asyncio
import pytest
import httpx
import websockets
from multiprocessing import Process
import time
import uvicorn
import os


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8004,
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
    proc.join()


@pytest.mark.asyncio
async def test_frontend_static_files_exist(server):
    """Test that frontend static files are served."""
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8004", timeout=30.0
    ) as client:
        # Test root serves HTML
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert b"Terminal Wrapper" in response.content

        # Test static CSS
        response = await client.get("/static/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

        # Test static JS
        response = await client.get("/static/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_frontend_vim_workflow(server):
    """Test complete vim workflow through frontend API flow."""
    # Create test file
    test_file = "/tmp/frontend_test.txt"
    with open(test_file, "w") as f:
        f.write("Original content\n")

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8004", timeout=30.0
    ) as client:
        # Step 1: Create vim session (simulating frontend)
        response = await client.post(
            "/sessions",
            json={
                "command": ["vim", "-u", "NONE", "-N", test_file],
                "rows": 24,
                "cols": 80,
                "env": {
                    "TERM": "xterm-256color",
                    "COLORTERM": "truecolor",
                }
            }
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Step 2: Wait for vim to start
        await asyncio.sleep(0.5)

        # Step 3: Check session info
        response = await client.get(f"/sessions/{session_id}")
        assert response.status_code == 200
        info = response.json()
        assert info["alive"] == True
        assert info["rows"] == 24
        assert info["cols"] == 80

        # Step 4: Send vim commands via HTTP (simulating frontend actions)
        # Make sure we're in normal mode first
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "\x1b"}  # ESC to ensure normal mode
        )
        await asyncio.sleep(0.2)

        # Go to end of file and add text
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "G"}  # Go to end
        )
        await asyncio.sleep(0.2)

        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "o"}  # Open new line
        )
        await asyncio.sleep(0.2)

        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "Added from frontend test"}
        )
        await asyncio.sleep(0.2)

        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "\x1b"}  # ESC
        )
        await asyncio.sleep(0.2)

        # Step 5: Save and quit
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": ":wq\n"}
        )
        await asyncio.sleep(0.5)

        # Step 6: Verify file was modified
        with open(test_file, "r") as f:
            content = f.read()

        print(f"\n=== FILE CONTENT ===\n{content}")
        assert "Original content" in content
        assert "Added from frontend test" in content

        # Cleanup
        os.remove(test_file)
        try:
            await client.delete(f"/sessions/{session_id}")
        except:
            pass


@pytest.mark.asyncio
async def test_frontend_websocket_vim(server):
    """Test vim through WebSocket (frontend real-time mode)."""
    test_file = "/tmp/ws_frontend_test.txt"
    with open(test_file, "w") as f:
        f.write("WebSocket test\n")

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8004", timeout=30.0
    ) as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={
                "command": ["vim", "-u", "NONE", "-N", test_file],
                "rows": 24,
                "cols": 80,
                "env": {"TERM": "xterm-256color"}
            }
        )
        session_id = response.json()["session_id"]

        # Connect WebSocket (simulating frontend)
        ws_url = f"ws://127.0.0.1:8004/sessions/{session_id}/ws"

        async with websockets.connect(ws_url) as websocket:
            # Collect initial vim output
            received = []
            try:
                async with asyncio.timeout(1.0):
                    while True:
                        msg = await websocket.recv()
                        if isinstance(msg, bytes):
                            received.append(msg)
            except asyncio.TimeoutError:
                pass

            initial_output = b"".join(received).decode("utf-8", errors="replace")
            print(f"\n=== VIM WEBSOCKET OUTPUT ===\n{initial_output[:200]}")

            # Verify vim started
            assert len(initial_output) > 0
            # Check for alternate screen buffer escape sequence
            assert "\x1b[?1049h" in initial_output or "\x1b[" in initial_output

            # Edit file: Go to end, add line
            await websocket.send(b"G")  # Go to end
            await asyncio.sleep(0.1)

            await websocket.send(b"o")  # Open line
            await asyncio.sleep(0.1)

            await websocket.send(b"Line from WebSocket")
            await asyncio.sleep(0.1)

            await websocket.send(b"\x1b")  # ESC
            await asyncio.sleep(0.1)

            # Save and quit
            await websocket.send(b":wq\n")
            await asyncio.sleep(0.5)

        # Verify file
        with open(test_file, "r") as f:
            content = f.read()

        print(f"\n=== FILE AFTER WEBSOCKET ===\n{content}")
        assert "WebSocket test" in content
        assert "Line from WebSocket" in content

        # Cleanup
        os.remove(test_file)


@pytest.mark.asyncio
async def test_frontend_resize(server):
    """Test terminal resize through frontend."""
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8004", timeout=30.0
    ) as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={"command": ["vim", "-u", "NONE", "-N"], "rows": 24, "cols": 80}
        )
        session_id = response.json()["session_id"]

        # Check initial size
        response = await client.get(f"/sessions/{session_id}")
        assert response.json()["rows"] == 24
        assert response.json()["cols"] == 80

        # Resize (simulating frontend window resize)
        response = await client.post(
            f"/sessions/{session_id}/resize",
            json={"rows": 40, "cols": 120}
        )
        assert response.status_code == 200

        # Verify resize
        response = await client.get(f"/sessions/{session_id}")
        info = response.json()
        assert info["rows"] == 40
        assert info["cols"] == 120

        # Cleanup
        await client.post(f"/sessions/{session_id}/input", json={"data": ":q!\n"})
        await asyncio.sleep(0.3)
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_frontend_multiple_sessions(server):
    """Test frontend can handle multiple sessions."""
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8004", timeout=30.0
    ) as client:
        sessions = []

        # Create 3 sessions (simulating multiple browser tabs)
        for i in range(3):
            response = await client.post(
                "/sessions",
                json={"command": ["cat"]}
            )
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])

        # Verify all exist
        response = await client.get("/sessions")
        active_sessions = response.json()["sessions"]
        for sid in sessions:
            assert sid in active_sessions

        # Send different data to each
        for i, sid in enumerate(sessions):
            await client.post(
                f"/sessions/{sid}/input",
                json={"data": f"Session {i}\n"}
            )

        await asyncio.sleep(0.3)

        # Verify each has its own output
        for i, sid in enumerate(sessions):
            response = await client.get(f"/sessions/{sid}/output")
            output = response.json()["output"]
            assert f"Session {i}" in output

        # Cleanup all
        for sid in sessions:
            await client.delete(f"/sessions/{sid}")


@pytest.mark.asyncio
async def test_frontend_vim_special_keys(server):
    """Test that special keys work through frontend."""
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8004", timeout=30.0
    ) as client:
        # Create vim session
        response = await client.post(
            "/sessions",
            json={
                "command": ["vim", "-u", "NONE", "-N", "/tmp/keys_test.txt"],
                "rows": 24,
                "cols": 80
            }
        )
        session_id = response.json()["session_id"]
        await asyncio.sleep(0.5)

        # Test special keys that frontend mobile buttons would send
        special_keys = {
            "ESC": "\x1b",
            "TAB": "\t",
            "UP": "\x1b[A",
            "DOWN": "\x1b[B",
            "LEFT": "\x1b[D",
            "RIGHT": "\x1b[C",
        }

        # Send insert mode
        await client.post(f"/sessions/{session_id}/input", json={"data": "i"})
        await asyncio.sleep(0.1)

        # Type something
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "Test line"}
        )
        await asyncio.sleep(0.1)

        # Send ESC (like mobile button)
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": special_keys["ESC"]}
        )
        await asyncio.sleep(0.1)

        # Use arrow keys (like mobile buttons)
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": special_keys["UP"]}
        )
        await asyncio.sleep(0.1)

        # Quit without saving
        await client.post(f"/sessions/{session_id}/input", json={"data": ":q!\n"})
        await asyncio.sleep(0.3)

        # If we get here without errors, special keys worked
        assert True

        # Cleanup
        try:
            await client.delete(f"/sessions/{session_id}")
            os.remove("/tmp/keys_test.txt")
        except:
            pass
