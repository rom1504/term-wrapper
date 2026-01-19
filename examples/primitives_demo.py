#!/usr/bin/env python3
"""Demonstration: Old approach vs New primitives.

This shows how the new primitives make code cleaner and more readable.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from term_wrapper.cli import TerminalClient

print("=" * 70)
print("BEFORE: Old approach (messy polling loops)")
print("=" * 70)
print("""
# Old way - manual polling with sleeps and ANSI stripping
import time
import re

def strip_ansi(text):
    return re.compile(r'\\x1b[@-_][0-?]*[ -/]*[@-~]').sub('', text)

client = TerminalClient()
session_id = client.create_session([\"echo\", \"hello\"])

# Manual polling
for i in range(30):
    raw = client.get_output(session_id, clear=False)
    clean = strip_ansi(raw)
    if \"hello\" in clean:
        break
    time.sleep(0.5)
else:
    raise TimeoutError(\"Text not found\")

# Get new content - have to track manually
current = client.get_output(session_id, clear=False)
# ... complex diffing logic ...
""")

print("\n" + "=" * 70)
print("AFTER: New primitives (clean and readable)")
print("=" * 70)
print("""
# New way - built-in helpers!
client = TerminalClient()
session_id = client.create_session([\"echo\", \"hello\"])

# Simple waiting
client.wait_for_text(session_id, \"hello\", timeout=15)

# Clean text extraction
text = client.get_text(session_id)  # ANSI stripped automatically!

# Incremental updates
new_lines = client.get_new_lines(session_id)  # Only what changed!

# Wait for stability
client.wait_for_quiet(session_id, duration=2)
""")

print("\n" + "=" * 70)
print("LIVE DEMO: Using new primitives with echo command")
print("=" * 70)

client = TerminalClient()

# Demo 1: wait_for_text
print("\n[Demo 1] wait_for_text()")
session_id = client.create_session(
    command=["bash", "-c", "echo 'Starting...'; sleep 1; echo 'Ready!'; sleep 2"],
    rows=24, cols=80
)
print("  Waiting for 'Ready!'...")
client.wait_for_text(session_id, "Ready!", timeout=5)
print("  ✓ Found it!")
client.delete_session(session_id)

# Demo 2: get_text with ANSI stripping
print("\n[Demo 2] get_text() with ANSI stripping")
session_id = client.create_session(
    command=["bash", "-c", "echo -e '\\033[31mRed Text\\033[0m Normal'"],
    rows=24, cols=80
)
import time
time.sleep(0.5)
clean_text = client.get_text(session_id, strip_ansi_codes=True)
print(f"  Clean text: {clean_text.strip()}")
client.delete_session(session_id)

# Demo 3: get_new_lines
print("\n[Demo 3] get_new_lines() - incremental updates")
session_id = client.create_session(
    command=["bash", "-c", "echo 'Line 1'; sleep 0.5; echo 'Line 2'; sleep 0.5; echo 'Line 3'; sleep 2"],
    rows=24, cols=80
)
time.sleep(0.3)
first_lines = client.get_new_lines(session_id)
print(f"  First read: {len(first_lines)} lines")

time.sleep(1)
new_lines = client.get_new_lines(session_id)
print(f"  Second read (only new): {len(new_lines)} new lines")
print(f"  New content: {[l for l in new_lines if l.strip()]}")
client.delete_session(session_id)

# Demo 4: wait_for_quiet
print("\n[Demo 4] wait_for_quiet()")
session_id = client.create_session(
    command=["bash", "-c", "for i in 1 2 3; do echo $i; sleep 0.3; done; sleep 5"],
    rows=24, cols=80
)
print("  Waiting for output to stabilize...")
client.wait_for_quiet(session_id, duration=1, timeout=10)
print("  ✓ Output is quiet!")
final_text = client.get_text(session_id)
print(f"  Final output: {final_text.strip()}")
client.delete_session(session_id)

client.close()

print("\n" + "=" * 70)
print("SUMMARY: New primitives available")
print("=" * 70)
print("""
✓ get_text(strip_ansi_codes=True) - Clean text extraction
✓ wait_for_text(text, timeout) - Wait for specific text
✓ wait_for_condition(func, timeout) - Custom conditions
✓ wait_for_quiet(duration) - Wait for stability
✓ get_new_lines() - Incremental updates only
✓ mark_read() - Mark current position

All available in TerminalClient!
""")
