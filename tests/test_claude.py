"""E2E tests for Claude CLI running in the terminal wrapper."""

import asyncio
import pytest
import httpx
import time
from multiprocessing import Process
import uvicorn

BASE_URL = "http://localhost:8004"


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
    proc.join(timeout=5)


async def wait_for_output(client, session_id, timeout=10.0):
    """Wait for output from the terminal session."""
    start_time = time.time()
    all_output = b""

    while time.time() - start_time < timeout:
        response = await client.get(f"/sessions/{session_id}/output")
        if response.status_code == 200:
            data = response.json()
            output = data.get("output", b"")
            if isinstance(output, str):
                output = output.encode()
            all_output += output

            if len(all_output) > 0:
                await asyncio.sleep(0.1)  # Give it a bit more time to accumulate

        await asyncio.sleep(0.1)

    return all_output


@pytest.mark.asyncio
async def test_claude_basic_launch(server):
    """Test launching Claude CLI in the terminal wrapper."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create Claude session
        response = await client.post("/sessions", json={
            "command": ["claude"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for Claude to start
        await asyncio.sleep(2.0)

        # Get output
        output = await wait_for_output(client, session_id, timeout=5.0)
        output_text = output.decode('utf-8', errors='ignore')

        # Claude should show some initial output (prompt or welcome message)
        assert len(output_text) > 0
        print(f"Claude initial output:\n{output_text}")

        # Cleanup
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_claude_simple_prompt(server):
    """Test sending a simple prompt to Claude in print mode."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # Create Claude session with -p (print mode) and prompt as argument
        response = await client.post("/sessions", json={
            "command": ["claude", "--dangerously-skip-permissions", "-p", "What is 2+2? Answer with just the number."],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for Claude to respond (print mode exits after response)
        await asyncio.sleep(12.0)

        # Get output
        output = await wait_for_output(client, session_id, timeout=10.0)
        output_text = output.decode('utf-8', errors='ignore')

        print(f"Claude response:\n{output_text}")

        # Should have some response
        assert len(output_text) > 0
        # Response should contain the answer
        assert "4" in output_text

        # Cleanup
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_claude_conversation(server):
    """Test having a multi-turn conversation with Claude."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        # Create Claude session without -p flag for interactive mode
        response = await client.post("/sessions", json={
            "command": ["claude", "--dangerously-skip-permissions"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for Claude to be ready (show initial prompt)
        await asyncio.sleep(3.0)
        initial = await wait_for_output(client, session_id, timeout=5.0)
        print(f"Initial output:\n{initial.decode('utf-8', errors='ignore')}")

        # First turn
        await client.post(f"/sessions/{session_id}/input", json={"data": "Hello! Say 'hi' back.\n"})
        await asyncio.sleep(10.0)
        output1 = await wait_for_output(client, session_id, timeout=10.0)
        output1_text = output1.decode('utf-8', errors='ignore')
        print(f"Turn 1:\n{output1_text}")
        assert len(output1_text) > 0

        # Second turn
        await client.post(f"/sessions/{session_id}/input", json={"data": "What's your name?\n"})
        await asyncio.sleep(10.0)
        output2 = await wait_for_output(client, session_id, timeout=10.0)
        output2_text = output2.decode('utf-8', errors='ignore')
        print(f"Turn 2:\n{output2_text}")
        assert len(output2_text) > 0

        # Cleanup
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_claude_exit(server):
    """Test exiting Claude CLI properly."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create Claude session
        response = await client.post("/sessions", json={
            "command": ["claude"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for Claude to start
        await asyncio.sleep(3.0)

        # Send exit command (Ctrl+C or Ctrl+D)
        await client.post(f"/sessions/{session_id}/input", json={"data": "\x03"})  # Ctrl+C
        await asyncio.sleep(1.0)

        # Try to get session info - it might still exist briefly
        response = await client.get(f"/sessions/{session_id}")
        # Session might be gone or still cleaning up
        assert response.status_code in [200, 404]

        # Cleanup if still exists
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_claude_help_command(server):
    """Test Claude help command."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create Claude session
        response = await client.post("/sessions", json={
            "command": ["claude", "--help"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait for help output
        await asyncio.sleep(2.0)

        # Get output
        output = await wait_for_output(client, session_id, timeout=5.0)
        output_text = output.decode('utf-8', errors='ignore')

        print(f"Claude help output:\n{output_text}")

        # Help should contain some usage information
        assert len(output_text) > 0
        # Common help text indicators
        assert any(word in output_text.lower() for word in ["usage", "help", "options", "command"])

        # Cleanup
        await client.delete(f"/sessions/{session_id}")
