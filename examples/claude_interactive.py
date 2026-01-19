#!/usr/bin/env python3
"""Interactive Claude CLI via term-wrapper using new primitives.

This demonstrates using the new helper primitives for clean, readable code.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from term_wrapper.cli import TerminalClient


def interactive_claude_request(work_dir: str, request: str) -> tuple[str, list[str]]:
    """Send interactive request to Claude CLI and get results.

    Args:
        work_dir: Directory to run Claude in
        request: Request string to send to Claude

    Returns:
        Tuple of (final_text_output, created_files)
    """
    client = TerminalClient(base_url="http://localhost:8000")

    print(f"[1/5] Creating Claude CLI session in {work_dir}...")
    session_id = client.create_session(
        command=["bash", "-c", f"cd {work_dir} && claude"],
        rows=40,
        cols=120
    )

    # Step 1: Handle trust prompt
    print("[2/5] Waiting for trust prompt...")
    client.wait_for_text(session_id, "Do you trust", timeout=10)
    print("  ✓ Trust prompt appeared")

    client.write_input(session_id, "\r")
    client.wait_for_text(session_id, "Welcome", timeout=10)
    print("  ✓ Main UI loaded")

    # Step 2: Submit request
    print(f"[3/5] Submitting request: '{request}'...")
    client.write_input(session_id, request)
    client.write_input(session_id, "\r")

    # Step 3: Wait for code generation
    print("[4/5] Waiting for Claude to generate code...")
    client.wait_for_condition(
        session_id,
        lambda text: "esc to cancel" in text.lower() or "tab to add" in text.lower(),
        timeout=30
    )
    print("  ✓ Code approval UI appeared")

    # Step 4: Approve code
    print("[5/5] Approving code...")
    client.wait_for_quiet(session_id, duration=2, timeout=10)  # Wait for UI to stabilize
    client.write_input(session_id, "\r")

    # Wait for file creation
    print("  → Waiting for file creation...")
    client.wait_for_condition(
        session_id,
        lambda text: len([f for f in os.listdir(work_dir) if f.endswith('.py')]) > 0,
        timeout=15
    )
    print("  ✓ File created!")

    # Get results
    final_text = client.get_text(session_id)
    files = [f for f in os.listdir(work_dir) if not f.startswith('.')]

    # Cleanup
    client.delete_session(session_id)
    client.close()

    return final_text, files


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

    text, files = interactive_claude_request(work_dir, request)

    print(f"\n✓ Files created: {files}")

    for filename in files:
        filepath = os.path.join(work_dir, filename)
        print(f"\n{filename}:")
        print("-" * 40)
        with open(filepath) as f:
            print(f.read())
        print("-" * 40)
