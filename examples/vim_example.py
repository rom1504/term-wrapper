"""Example of running vim through the terminal wrapper."""

import asyncio
import httpx


async def main():
    """Open vim, edit a file, and save it."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create vim session
        print("Creating vim session...")
        response = await client.post("/sessions", json={
            "command": ["vim", "/tmp/test_file.txt"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        session_id = response.json()["session_id"]
        print(f"Session: {session_id}")

        # Wait for vim to start
        await asyncio.sleep(1)

        # Enter insert mode and type text
        print("Writing text...")
        await client.post(f"/sessions/{session_id}/input", json={"data": "i"})
        await asyncio.sleep(0.1)
        await client.post(f"/sessions/{session_id}/input", json={
            "data": "Hello from terminal wrapper!\nThis was written via API."
        })
        await asyncio.sleep(0.1)

        # Save and quit
        print("Saving and quitting...")
        await client.post(f"/sessions/{session_id}/input", json={"data": "\x1b"})  # ESC
        await asyncio.sleep(0.1)
        await client.post(f"/sessions/{session_id}/input", json={"data": ":wq\n"})
        await asyncio.sleep(0.5)

        # Clean up
        await client.delete(f"/sessions/{session_id}")
        print("Session deleted")

        # Read the file to verify
        with open("/tmp/test_file.txt", "r") as f:
            content = f.read()
            print(f"\nFile content:\n{content}")


if __name__ == "__main__":
    print("Make sure the server is running: python main.py")
    print("-" * 50)
    asyncio.run(main())
