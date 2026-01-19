#!/usr/bin/env python3
"""Capture raw ANSI sequences from Claude to understand status line updates."""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


async def main():
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    client = TerminalClient(base_url=server_url)

    # Create Claude session
    print("\n=== Creating Claude session ===")
    session_id = client.create_session(
        command=["bash", "-c", "cd /tmp && claude"],
        rows=24,
        cols=80
    )
    print(f"Session ID: {session_id}")

    await asyncio.sleep(2)

    # Send command to generate output
    print("\n=== Sending command ===")
    client.write_input(session_id, "write a 20 line poem\n")

    # Capture raw output with ANSI codes for 30 seconds
    print("\n=== Capturing output for 30 seconds ===\n")

    with open('claude_ansi_output.txt', 'wb') as f:
        for i in range(60):  # 60 iterations, 0.5s each = 30s total
            output = client.get_output(session_id, clear=False)
            if output:
                f.write(output.encode('utf-8'))
                f.write(b'\n--- CAPTURE AT ' + str(i*0.5).encode() + b's ---\n')

            await asyncio.sleep(0.5)

    print("\n✓ Captured output to claude_ansi_output.txt")

    # Also get clean screen output
    screen = client.get_screen(session_id)
    with open('claude_screen_output.txt', 'w') as f:
        for i, line in enumerate(screen):
            f.write(f"{i:3d}: {line}\n")

    print("✓ Captured screen to claude_screen_output.txt")

    # Search for "Grooving" or "Herding" in output
    with open('claude_ansi_output.txt', 'rb') as f:
        content = f.read()

    # Count occurrences
    grooving_count = content.count(b'Grooving')
    herding_count = content.count(b'Herding')
    mulling_count = content.count(b'Mulling')

    print(f"\n=== Status Indicator Counts ===")
    print(f"Grooving: {grooving_count}")
    print(f"Herding: {herding_count}")
    print(f"Mulling: {mulling_count}")

    # Check for cursor movement sequences
    cursor_up = content.count(b'\x1b[A')  # ESC[A
    cursor_down = content.count(b'\x1b[B')  # ESC[B
    cursor_forward = content.count(b'\x1b[C')  # ESC[C
    cursor_back = content.count(b'\x1b[D')  # ESC[D
    cursor_pos = content.count(b'\x1b[H')  # ESC[H
    carriage_return = content.count(b'\r')  # CR

    print(f"\n=== ANSI Cursor Movement Counts ===")
    print(f"Cursor Up (ESC[A): {cursor_up}")
    print(f"Cursor Down (ESC[B): {cursor_down}")
    print(f"Cursor Forward (ESC[C): {cursor_forward}")
    print(f"Cursor Back (ESC[D): {cursor_back}")
    print(f"Cursor Position (ESC[H): {cursor_pos}")
    print(f"Carriage Return (\\r): {carriage_return}")

    # Check for line clearing sequences
    clear_line = content.count(b'\x1b[K')  # ESC[K - clear to end of line
    clear_screen = content.count(b'\x1b[2J')  # ESC[2J - clear screen

    print(f"\n=== ANSI Clear Sequences ===")
    print(f"Clear Line (ESC[K): {clear_line}")
    print(f"Clear Screen (ESC[2J): {clear_screen}")

    # Cleanup
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n" + "="*60)
    print("ANSI SEQUENCE ANALYSIS COMPLETE")
    print("="*60)
    print("\nCheck files:")
    print("  - claude_ansi_output.txt (raw ANSI output)")
    print("  - claude_screen_output.txt (parsed screen buffer)")


if __name__ == "__main__":
    asyncio.run(main())
