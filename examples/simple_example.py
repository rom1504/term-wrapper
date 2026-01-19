"""Simple example of using the terminal wrapper programmatically."""

import asyncio
import httpx


async def main():
    """Run a simple command and get its output."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create a terminal session running 'ls -la'
        print("Creating session...")
        response = await client.post("/sessions", json={
            "command": ["ls", "-la"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
            }
        })

        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Session created: {session_id}")

        # Wait for command to complete
        await asyncio.sleep(1)

        # Get output
        response = await client.get(f"/sessions/{session_id}/output")
        output_data = response.json()
        output = output_data.get("output", "")

        print("\nCommand output:")
        print(output)

        # Clean up
        await client.delete(f"/sessions/{session_id}")
        print("\nSession deleted")


if __name__ == "__main__":
    print("Make sure the server is running: python main.py")
    print("-" * 50)
    asyncio.run(main())
