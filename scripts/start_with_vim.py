#!/usr/bin/env python3
"""Start server and automatically create vim session."""

import asyncio
import httpx
import subprocess
import time
import sys

async def create_vim_session(port=6489, filename="/tmp/mytest"):
    """Create a vim session via API."""
    # Wait for server to start
    await asyncio.sleep(2)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create vim session
            response = await client.post(
                f"http://localhost:{port}/sessions",
                json={
                    "command": ["vim", filename],
                    "rows": 24,
                    "cols": 80,
                    "env": {
                        "TERM": "xterm-256color",
                        "COLORTERM": "truecolor",
                    }
                }
            )

            if response.status_code == 200:
                session_id = response.json()["session_id"]
                print(f"\n✓ Vim session created: {session_id}")
                print(f"✓ Editing file: {filename}")
                print(f"\nOpen in browser: http://0.0.0.0:{port}/?session={session_id}")
                print(f"Or just: http://0.0.0.0:{port}/ (then enter 'vim {filename}' and click Connect)")
            else:
                print(f"Failed to create session: {response.status_code}")
        except Exception as e:
            print(f"Error creating session: {e}")

async def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6489
    filename = sys.argv[2] if len(sys.argv) > 2 else "/tmp/mytest"

    print(f"Starting terminal wrapper server on 0.0.0.0:{port}...")
    print(f"Target file: {filename}")
    print(f"Access at: http://0.0.0.0:{port}/")
    print()

    # Start server in background
    server_proc = subprocess.Popen(
        [sys.executable, "main.py", "--host", "0.0.0.0", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Create vim session
        await create_vim_session(port, filename)

        # Keep running
        print("\nServer is running. Press Ctrl+C to stop.")
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        server_proc.terminate()
        server_proc.wait()
        print("Server stopped.")

if __name__ == "__main__":
    asyncio.run(main())
