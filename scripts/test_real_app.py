#!/usr/bin/env python3
"""Test with a real TUI application to see what actually works."""

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


async def test_real_apps():
    """Test with real TUI applications."""
    print("=" * 60)
    print("  Testing Real TUI Applications")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:

        # Test 1: top command (simpler than htop)
        print("1. Testing 'top' command (batch mode, 1 iteration)...")
        try:
            response = await client.post(
                "/sessions",
                json={"command": ["top", "-b", "-n", "1"]},
            )
            session_id = response.json()["session_id"]
            await asyncio.sleep(1.0)

            response = await client.get(f"/sessions/{session_id}/output")
            output = response.json()["output"]

            if "PID" in output or "top -" in output:
                print("   ✓ 'top' works! Got process list")
            else:
                print("   ✗ 'top' output unclear")
                print(f"   Output preview: {output[:200]}")

            await client.delete(f"/sessions/{session_id}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        print()

        # Test 2: ls with colors
        print("2. Testing 'ls' with colors...")
        try:
            response = await client.post(
                "/sessions",
                json={"command": ["ls", "--color=always", "-la"]},
            )
            session_id = response.json()["session_id"]
            await asyncio.sleep(0.5)

            response = await client.get(f"/sessions/{session_id}/output")
            output = response.json()["output"]

            if "\x1b[" in output:  # ANSI escape codes
                print("   ✓ 'ls' works! Colors (ANSI codes) present")
            else:
                print("   ? 'ls' works but no colors detected")

            await client.delete(f"/sessions/{session_id}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        print()

        # Test 3: Python with readline
        print("3. Testing Python REPL...")
        try:
            response = await client.post(
                "/sessions",
                json={"command": ["python3", "-c", "print('Hello'); print(1+1)"]},
            )
            session_id = response.json()["session_id"]
            await asyncio.sleep(0.5)

            response = await client.get(f"/sessions/{session_id}/output")
            output = response.json()["output"]

            if "Hello" in output and "2" in output:
                print("   ✓ Python script execution works!")
            else:
                print("   ✗ Python output unclear")

            await client.delete(f"/sessions/{session_id}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        print()

        # Test 4: Interactive Python REPL
        print("4. Testing interactive Python REPL with input...")
        try:
            response = await client.post(
                "/sessions",
                json={"command": ["python3"]},
            )
            session_id = response.json()["session_id"]
            await asyncio.sleep(0.5)

            # Send Python command
            await client.post(
                f"/sessions/{session_id}/input",
                json={"data": "2 + 2\n"}
            )
            await asyncio.sleep(0.3)

            response = await client.get(f"/sessions/{session_id}/output")
            output = response.json()["output"]

            if ">>>" in output and "4" in output:
                print("   ✓ Interactive Python REPL works!")
            else:
                print("   ? Python REPL unclear")
                print(f"   Output: {output[:200]}")

            # Quit
            await client.post(f"/sessions/{session_id}/input", json={"data": "exit()\n"})
            await asyncio.sleep(0.2)
            await client.delete(f"/sessions/{session_id}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        print()

        # Test 5: Check what happens with vim (will probably fail or be limited)
        print("5. Testing 'vim' (this might not work fully)...")
        try:
            response = await client.post(
                "/sessions",
                json={"command": ["vim", "-c", "q"]},  # Immediately quit
            )
            session_id = response.json()["session_id"]
            await asyncio.sleep(0.5)

            response = await client.get(f"/sessions/{session_id}/output")
            output = response.json()["output"]

            print(f"   Output length: {len(output)} chars")
            print(f"   Has ANSI codes: {bool('\x1b[' in output)}")
            print(f"   Preview: {repr(output[:100])}")

            await client.delete(f"/sessions/{session_id}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        print()

    print("=" * 60)
    print("  Tests Complete")
    print("=" * 60)


def main():
    """Main entry point."""
    print("Starting server...")
    server_proc = Process(target=run_server, daemon=True)
    server_proc.start()
    time.sleep(2)
    print("Server started\n")

    try:
        asyncio.run(test_real_apps())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nStopping server...")
        server_proc.terminate()
        server_proc.join()
        print("Server stopped")


if __name__ == "__main__":
    main()
