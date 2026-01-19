"""Test vim editor integration."""

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
        port=8003,
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
async def test_vim_simple_open_quit(server):
    """Test opening vim and immediately quitting."""
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8003", timeout=30.0
    ) as client:
        # Create session with vim
        response = await client.post(
            "/sessions",
            json={
                "command": ["vim", "-u", "NONE", "-N"],  # No config, nocompatible
                "rows": 24,
                "cols": 80,
            },
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for vim to start
        await asyncio.sleep(0.5)

        # Get initial output
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]

        print(f"\n=== VIM INITIAL OUTPUT ({len(output)} bytes) ===")
        print(repr(output[:500]))

        # Try to quit vim with :q
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": ":q\n"}
        )

        await asyncio.sleep(0.5)

        # Get output after quit
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]
        print(f"\n=== AFTER :q ({len(output)} bytes) ===")
        print(repr(output[:500]))

        # Clean up
        try:
            await client.delete(f"/sessions/{session_id}")
        except:
            pass


@pytest.mark.asyncio
async def test_vim_edit_file(server):
    """Test editing a file with vim."""
    # Create a test file
    test_file = "/tmp/vim_test.txt"
    with open(test_file, "w") as f:
        f.write("Hello World\n")

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8003", timeout=30.0
    ) as client:
        # Open vim with the file
        response = await client.post(
            "/sessions",
            json={
                "command": ["vim", "-u", "NONE", "-N", test_file],
                "rows": 24,
                "cols": 80,
            },
        )
        session_id = response.json()["session_id"]

        await asyncio.sleep(0.5)

        # Get initial screen
        response = await client.get(f"/sessions/{session_id}/output")
        initial_output = response.json()["output"]
        print(f"\n=== VIM WITH FILE ({len(initial_output)} bytes) ===")
        print(repr(initial_output[:500]))

        # Go to end of line and add text
        # ESC to ensure normal mode, then A to append at end of line
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "\x1b"}  # ESC
        )
        await asyncio.sleep(0.1)

        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "A"}  # Append at end of line
        )
        await asyncio.sleep(0.1)

        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": " - edited"}
        )
        await asyncio.sleep(0.2)

        # Get output to see if editing worked
        response = await client.get(f"/sessions/{session_id}/output")
        edit_output = response.json()["output"]
        print(f"\n=== AFTER EDITING ({len(edit_output)} bytes) ===")
        print(repr(edit_output[:500]))

        # Save and quit: ESC :wq
        await client.post(f"/sessions/{session_id}/input", json={"data": "\x1b"})
        await asyncio.sleep(0.1)
        await client.post(f"/sessions/{session_id}/input", json={"data": ":wq\n"})
        await asyncio.sleep(0.5)

        # Check if file was modified
        with open(test_file, "r") as f:
            content = f.read()

        print(f"\n=== FILE CONTENT ===")
        print(content)

        assert "edited" in content, "File should contain the edited text"

        # Clean up
        os.remove(test_file)
        try:
            await client.delete(f"/sessions/{session_id}")
        except:
            pass


@pytest.mark.asyncio
async def test_vim_websocket_interaction(server):
    """Test vim via WebSocket for real-time interaction."""
    test_file = "/tmp/vim_ws_test.txt"
    with open(test_file, "w") as f:
        f.write("Line 1\n")

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8003", timeout=30.0
    ) as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={
                "command": ["vim", "-u", "NONE", "-N", test_file],
                "rows": 24,
                "cols": 80,
            },
        )
        session_id = response.json()["session_id"]

        # Connect via WebSocket
        ws_url = f"ws://127.0.0.1:8003/sessions/{session_id}/ws"

        async with websockets.connect(ws_url) as websocket:
            # Collect initial output
            received = []
            try:
                async with asyncio.timeout(1.0):
                    while True:
                        message = await websocket.recv()
                        if isinstance(message, bytes):
                            received.append(message)
            except asyncio.TimeoutError:
                pass

            initial = b"".join(received)
            print(f"\n=== VIM WEBSOCKET INITIAL ({len(initial)} bytes) ===")
            print(repr(initial[:500]))

            # Try to add a line: o (open line below), type text, ESC
            await websocket.send(b"o")  # Open line below
            await asyncio.sleep(0.1)

            await websocket.send(b"New line from websocket")
            await asyncio.sleep(0.1)

            await websocket.send(b"\x1b")  # ESC
            await asyncio.sleep(0.1)

            # Save and quit
            await websocket.send(b":wq\n")
            await asyncio.sleep(0.5)

            # Collect any remaining output
            try:
                async with asyncio.timeout(0.5):
                    while True:
                        message = await websocket.recv()
                        if isinstance(message, bytes):
                            received.append(message)
            except asyncio.TimeoutError:
                pass

        # Check file content
        with open(test_file, "r") as f:
            content = f.read()

        print(f"\n=== FILE AFTER WEBSOCKET EDIT ===")
        print(content)

        # Clean up
        os.remove(test_file)
        try:
            await client.delete(f"/sessions/{session_id}")
        except:
            pass


@pytest.mark.asyncio
async def test_vim_inspect_output(server):
    """Inspect what vim actually sends to understand terminal behavior."""
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8003", timeout=30.0
    ) as client:
        # Create session with vim
        response = await client.post(
            "/sessions",
            json={
                "command": ["vim", "-u", "NONE", "-N"],
                "rows": 24,
                "cols": 80,
                "env": {"TERM": "xterm-256color"}  # Explicit TERM
            },
        )
        session_id = response.json()["session_id"]

        await asyncio.sleep(0.5)

        # Get raw output
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]

        print(f"\n=== VIM RAW OUTPUT ANALYSIS ===")
        print(f"Length: {len(output)} bytes")
        print(f"First 100 bytes (repr): {repr(output[:100])}")
        print(f"First 100 bytes (hex): {output[:100].encode().hex()}")

        # Look for specific escape sequences
        escape_sequences = {
            "clear_screen": "\x1b[2J" in output or "\x1b[H\x1b[J" in output,
            "alt_screen": "\x1b[?1049h" in output,
            "cursor_pos": "\x1b[" in output and ("H" in output or "f" in output),
            "colors": "\x1b[3" in output or "\x1b[4" in output,
            "mouse_tracking": "\x1b[?1000h" in output,
        }

        print(f"\nDetected escape sequences:")
        for name, present in escape_sequences.items():
            print(f"  {name}: {'YES' if present else 'NO'}")

        # Send a simple command that should echo
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": ":echo 'test'\n"}
        )
        await asyncio.sleep(0.3)

        response = await client.get(f"/sessions/{session_id}/output")
        after_echo = response.json()["output"]

        print(f"\n=== AFTER :echo 'test' ===")
        print(f"Length: {len(after_echo)} bytes")
        print(f"Content (repr): {repr(after_echo[:200])}")

        if "test" in after_echo:
            print("✓ Echo command worked!")
        else:
            print("✗ Echo not found in output")

        # Quit
        await client.post(f"/sessions/{session_id}/input", json={"data": ":q\n"})
        await asyncio.sleep(0.3)

        try:
            await client.delete(f"/sessions/{session_id}")
        except:
            pass
