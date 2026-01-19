"""
Interactive htop demonstration using term-wrapper API.

This example shows how to:
1. Start the term-wrapper server
2. Launch htop through the API
3. Send commands to navigate htop
4. Display live system monitoring output
"""

import asyncio
import httpx
import time
import sys


async def run_htop_demo():
    """Run an interactive htop session through term-wrapper."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create htop session
        print("🚀 Launching htop...")
        response = await client.post("/sessions", json={
            "command": ["htop"],
            "rows": 24,
            "cols": 80,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            }
        })

        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"✓ Session created: {session_id}")

        # Wait for htop to initialize
        await asyncio.sleep(1)

        # Get initial output
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json().get("output", "")
        print("\n" + "="*80)
        print("HTOP OUTPUT:")
        print("="*80)
        print(output)
        print("="*80)

        # Demonstrate navigation
        print("\n📊 htop is running! Here's what you can do:")
        print("  - Arrow keys to navigate processes")
        print("  - F6 to change sort column")
        print("  - F10 or 'q' to quit")
        print("  - Space to tag processes")
        print("  - 't' for tree view")

        # Demo: Send arrow down a few times
        print("\n⬇️  Sending DOWN arrow 5 times to scroll through processes...")
        for i in range(5):
            await client.post(f"/sessions/{session_id}/input", json={
                "data": "\x1b[B"  # Down arrow escape sequence
            })
            await asyncio.sleep(0.2)

        # Get updated output
        await asyncio.sleep(0.5)
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json().get("output", "")
        print("\n" + "="*80)
        print("AFTER SCROLLING:")
        print("="*80)
        print(output[-2000:])  # Show last 2000 chars
        print("="*80)

        # Demo: Press 't' for tree view
        print("\n🌳 Pressing 't' to toggle tree view...")
        await client.post(f"/sessions/{session_id}/input", json={
            "data": "t"
        })
        await asyncio.sleep(0.5)

        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json().get("output", "")
        print("\n" + "="*80)
        print("TREE VIEW:")
        print("="*80)
        print(output[-2000:])
        print("="*80)

        # Demo: Press F6 to change sort
        print("\n📈 Pressing F6 to change sort order...")
        await client.post(f"/sessions/{session_id}/input", json={
            "data": "\x1bOP\x1b[B\n"  # F6 + Down + Enter
        })
        await asyncio.sleep(0.5)

        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json().get("output", "")
        print("\n" + "="*80)
        print("AFTER SORT CHANGE:")
        print("="*80)
        print(output[-2000:])
        print("="*80)

        # Interactive mode
        print("\n🎮 Interactive mode - you can send commands:")
        print("  Type 'refresh' to see current output")
        print("  Type 'quit' to exit and clean up")
        print("  Or any key to send to htop (down, up, t, F6, etc.)")

        while True:
            try:
                user_input = input("\n> ").strip().lower()

                if user_input == "quit":
                    break
                elif user_input == "refresh":
                    response = await client.get(f"/sessions/{session_id}/output")
                    output = response.json().get("output", "")
                    print("\n" + "="*80)
                    print(output[-2000:])
                    print("="*80)
                elif user_input == "down":
                    await client.post(f"/sessions/{session_id}/input", json={"data": "\x1b[B"})
                    print("✓ Sent DOWN arrow")
                elif user_input == "up":
                    await client.post(f"/sessions/{session_id}/input", json={"data": "\x1b[A"})
                    print("✓ Sent UP arrow")
                elif user_input == "t":
                    await client.post(f"/sessions/{session_id}/input", json={"data": "t"})
                    print("✓ Toggled tree view")
                elif user_input == "f6":
                    await client.post(f"/sessions/{session_id}/input", json={"data": "\x1bOP"})
                    print("✓ Sent F6 (sort menu)")
                else:
                    await client.post(f"/sessions/{session_id}/input", json={"data": user_input})
                    print(f"✓ Sent: {user_input}")

                # Auto-refresh after each command
                await asyncio.sleep(0.3)
                response = await client.get(f"/sessions/{session_id}/output")
                output = response.json().get("output", "")
                print("\n" + "="*80)
                print(output[-2000:])
                print("="*80)

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break

        # Quit htop
        print("\n👋 Quitting htop...")
        await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
        await asyncio.sleep(0.5)

        # Clean up
        await client.delete(f"/sessions/{session_id}")
        print(f"✓ Session {session_id} cleaned up")


async def main():
    """Main entry point."""
    print("="*80)
    print("HTOP DEMO - Interactive System Monitor via term-wrapper")
    print("="*80)
    print("\nMake sure the term-wrapper server is running:")
    print("  uv run python main.py")
    print("\nOr visit the web frontend:")
    print("  http://localhost:8000/static/index.html?cmd=htop")
    print("="*80)

    # Check if server is running
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code != 200:
                print("\n❌ Server not responding. Please start it with: uv run python main.py")
                sys.exit(1)
    except Exception as e:
        print(f"\n❌ Cannot connect to server: {e}")
        print("Please start it with: uv run python main.py")
        sys.exit(1)

    print("\n✓ Server is running!\n")

    await run_htop_demo()

    print("\n" + "="*80)
    print("Demo complete! 🎉")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
