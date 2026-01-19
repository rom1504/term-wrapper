#!/usr/bin/env python3
"""Example: Send requests to Claude CLI via stdin using term-wrapper.

This demonstrates programmatically controlling Claude CLI by piping
input to its stdin, which avoids the complexities of interactive TUI mode.
"""

import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from term_wrapper.cli import TerminalClient


def claude_request(work_dir: str, request: str, wait_time: int = 15) -> tuple[str, list[str]]:
    """Send a request to Claude CLI and get results.

    Args:
        work_dir: Directory to run Claude in
        request: Request string to send to Claude
        wait_time: Seconds to wait for completion

    Returns:
        Tuple of (screen_output, created_files)
    """
    client = TerminalClient(base_url="http://localhost:8000")

    # Run Claude with request piped to stdin
    cmd = (
        f'cd {work_dir} && '
        f'echo "{request}" | claude --dangerously-skip-permissions && '
        f'sleep {wait_time//2}'  # Keep session alive to capture output
    )

    session_id = client.create_session(
        command=["bash", "-c", cmd],
        rows=40,
        cols=120
    )

    # Wait for Claude to complete
    time.sleep(wait_time)

    # Get screen output
    screen_data = client.get_screen(session_id)
    screen_text = '\n'.join(screen_data['lines'])

    # Get created files
    files = [f for f in os.listdir(work_dir) if not f.startswith('.')]

    # Cleanup
    client.delete_session(session_id)
    client.close()

    return screen_text, files


if __name__ == "__main__":
    # Example usage
    work_dir = "/tmp/claude_test"
    os.makedirs(work_dir, exist_ok=True)

    # Clean previous files
    for f in os.listdir(work_dir):
        if not f.startswith('.'):
            os.remove(os.path.join(work_dir, f))

    print("Sending request to Claude via stdin...")
    request = "Create a Python file that prints the first 10 Fibonacci numbers"

    screen, files = claude_request(work_dir, request, wait_time=20)

    print(f"\n✓ Created files: {files}")

    # Show created files
    for filename in files:
        filepath = os.path.join(work_dir, filename)
        print(f"\n{'='*60}")
        print(f"File: {filename}")
        print('='*60)
        with open(filepath) as f:
            print(f.read())

    # Show Claude's response from screen
    print(f"\n{'='*60}")
    print("Claude's screen output (excerpts):")
    print('='*60)
    for line in screen.split('\n'):
        if any(keyword in line for keyword in ['Created', 'Writing', 'fibonacci', 'Done']):
            print(line)
