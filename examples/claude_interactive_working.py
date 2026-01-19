#!/usr/bin/env python3
"""Working example: Interactive Claude CLI via term-wrapper.

This demonstrates the WORKING approach for using Claude CLI interactively
through term-wrapper's PTY with raw mode support.

Key requirements:
1. Wait for UI elements to fully render before sending input
2. Poll output to detect state changes instead of using fixed sleeps
3. Handle multiple UI stages: trust prompt, code generation, approval
"""

import time
import os
from term_wrapper.cli import TerminalClient


def wait_for_condition(client, session_id, check_func, timeout=60, poll_interval=1):
    """Poll screen output until condition is met or timeout.

    Args:
        client: TerminalClient instance
        session_id: Session ID to poll
        check_func: Function that takes screen dict and returns bool
        timeout: Maximum seconds to wait
        poll_interval: Seconds between polls

    Returns:
        (screen_dict, found_bool) tuple
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        screen = client.get_screen(session_id)
        if check_func(screen):
            return screen, True
        time.sleep(poll_interval)
    return screen, False


def interactive_claude_request(work_dir: str, request: str) -> tuple[str, list[str]]:
    """Send interactive request to Claude CLI and get results.

    Args:
        work_dir: Directory to run Claude in
        request: Request string to send to Claude

    Returns:
        Tuple of (final_screen_output, created_files)
    """
    client = TerminalClient(base_url="http://localhost:8000")

    print(f"[1/6] Creating Claude CLI session in {work_dir}...")
    session_id = client.create_session(
        command=["bash", "-c", f"cd {work_dir} && claude"],
        rows=40,
        cols=120
    )

    # Step 1: Handle trust prompt
    print("[2/6] Waiting for trust prompt...")
    screen, found = wait_for_condition(
        client, session_id,
        lambda s: any("Do you trust" in line for line in s['lines']),
        timeout=10
    )

    if found:
        print("  ✓ Trust prompt detected")
        time.sleep(1)  # Brief stabilization pause
        client.write_input(session_id, "\r")

        # Wait for main UI
        print("  ✓ Waiting for main UI...")
        screen, found = wait_for_condition(
            client, session_id,
            lambda s: any("Welcome" in line for line in s['lines']),
            timeout=10
        )

    # Step 2: Submit request
    print(f"[3/6] Typing request: '{request}'...")
    client.write_input(session_id, request)
    time.sleep(0.5)

    print("  ✓ Pressing Enter to submit...")
    client.write_input(session_id, "\r")

    # Step 3: Wait for code generation
    print("[4/6] Waiting for Claude to generate code...")
    screen, found = wait_for_condition(
        client, session_id,
        lambda s: any("esc to cancel" in line.lower() or "tab to add" in line.lower() for line in s['lines']),
        timeout=30,
        poll_interval=2
    )

    if found:
        print("  ✓ Code approval UI appeared")

        # Step 4: Approve code
        print("[5/6] Waiting for UI to stabilize before approval...")
        time.sleep(3)  # Critical: let UI fully render

        print("  ✓ Pressing Enter to approve...")
        client.write_input(session_id, "\r")

        # Step 5: Wait for file creation
        print("[6/6] Waiting for file creation...")
        screen, found = wait_for_condition(
            client, session_id,
            lambda s: len([f for f in os.listdir(work_dir) if f.endswith('.py')]) > 0,
            timeout=15,
            poll_interval=1
        )

    # Get results
    screen = client.get_screen(session_id)
    screen_text = '\n'.join(screen['lines'])
    files = [f for f in os.listdir(work_dir) if not f.startswith('.')]

    # Cleanup
    client.delete_session(session_id)
    client.close()

    return screen_text, files


if __name__ == "__main__":
    # Example usage
    work_dir = "/tmp/claude_interactive_example"
    os.makedirs(work_dir, exist_ok=True)

    # Clean previous files
    for f in os.listdir(work_dir):
        if not f.startswith('.'):
            os.remove(os.path.join(work_dir, f))

    request = "create hello.py that prints hello world"

    print("=" * 60)
    print("Interactive Claude CLI Example")
    print("=" * 60)

    screen, files = interactive_claude_request(work_dir, request)

    print(f"\n✓ Files created: {files}")

    for filename in files:
        filepath = os.path.join(work_dir, filename)
        print(f"\n{filename}:")
        print("-" * 40)
        with open(filepath) as f:
            print(f.read())
        print("-" * 40)
