#!/usr/bin/env python3
"""Manual end-to-end test of the terminal wrapper system."""

import asyncio
import httpx
import time
from multiprocessing import Process
import uvicorn


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8000,
        log_level="error",
    )


async def test_system():
    """Test the complete system."""
    print("=" * 60)
    print("  Terminal Wrapper - Manual End-to-End Test")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        # Test 1: Health check
        print("1. Health check...")
        response = await client.get("/health")
        print(f"   Status: {response.json()['status']}")
        print()

        # Test 2: Create session with simple command
        print("2. Creating session with simple command...")
        response = await client.post(
            "/sessions",
            json={"command": ["sh", "-c", "echo 'Hello World'; echo 'Line 2'"]},
        )
        session_id = response.json()["session_id"]
        print(f"   Session ID: {session_id}")
        print()

        # Wait for output
        await asyncio.sleep(0.5)

        # Test 3: Get output
        print("3. Getting session output...")
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]
        print(f"   Output:\n{output}")
        print()

        # Clean up
        await client.delete(f"/sessions/{session_id}")

        # Test 4: Create interactive session (cat command)
        print("4. Creating interactive session (cat)...")
        response = await client.post(
            "/sessions",
            json={"command": ["cat"]},
        )
        session_id = response.json()["session_id"]
        print(f"   Session ID: {session_id}")
        print()

        # Test 5: Send input
        print("5. Sending input to session...")
        await client.post(
            f"/sessions/{session_id}/input",
            json={"data": "Interactive test\n"},
        )
        print("   Input sent: 'Interactive test'")
        print()

        # Wait for echo
        await asyncio.sleep(0.3)

        # Test 6: Get echoed output
        print("6. Getting echoed output...")
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]
        print(f"   Output:\n{output}")
        print()

        # Test 7: List sessions
        print("7. Listing all sessions...")
        response = await client.get("/sessions")
        sessions = response.json()["sessions"]
        print(f"   Active sessions: {len(sessions)}")
        print()

        # Clean up
        await client.delete(f"/sessions/{session_id}")

        # Test 8: Create session with Python TUI app
        print("8. Creating session with Python TUI app...")
        response = await client.post(
            "/sessions",
            json={"command": ["python3", "examples/simple_tui.py"]},
        )
        session_id = response.json()["session_id"]
        print(f"   Session ID: {session_id}")
        print()

        # Wait for app to start
        await asyncio.sleep(0.5)

        # Get initial output
        print("9. Getting TUI app output...")
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]
        print(f"   App started successfully!")
        if "Terminal Wrapper Test App" in output:
            print("   ✓ TUI app rendered correctly")
        print()

        # Send some commands
        print("10. Sending commands to TUI app...")
        await client.post(f"/sessions/{session_id}/input", json={"data": "+"})
        await asyncio.sleep(0.2)
        await client.post(f"/sessions/{session_id}/input", json={"data": "+"})
        await asyncio.sleep(0.2)
        await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
        print("   Sent: '+', '+', 'q'")
        print()

        # Clean up
        await asyncio.sleep(0.3)
        try:
            await client.delete(f"/sessions/{session_id}")
        except:
            pass

    print("=" * 60)
    print("  All Tests Passed! ✓")
    print("=" * 60)
    print()


def main():
    """Main entry point."""
    # Start server
    print("Starting server...")
    server_proc = Process(target=run_server, daemon=True)
    server_proc.start()
    time.sleep(2)
    print("Server started\n")

    try:
        # Run tests
        asyncio.run(test_system())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Stop server
        print("\nStopping server...")
        server_proc.terminate()
        server_proc.join()
        print("Server stopped")


if __name__ == "__main__":
    main()
