# Term-Wrapper Skill

**COMPLETE, SELF-CONTAINED INSTRUCTIONS FOR RUNNING TERMINAL APPLICATIONS VIA TERM-WRAPPER API**

Run any terminal application (TUI, CLI, or interactive program) through the term-wrapper HTTP API. This skill provides complete instructions for Claude to interact with terminal applications programmatically.

## What This Skill Does

Enables Claude to:
- Launch terminal applications via HTTP API
- Send keyboard input to running applications
- Retrieve and parse terminal output
- Interact with TUI applications like htop, vim, or any command-line tool

## Core API Operations

### 1. Check Server Health
```bash
curl -s http://localhost:8000/health
```
Returns: `{"status":"healthy"}` if running

### 2. Create Terminal Session
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "command": ["COMMAND", "arg1", "arg2"],
    "rows": 40,
    "cols": 150,
    "env": {
      "TERM": "xterm-256color",
      "COLORTERM": "truecolor"
    }
  }'
```
Returns: `{"session_id": "uuid-here"}`

### 3. Get Terminal Output
```bash
curl http://localhost:8000/sessions/{session_id}/output
```
Returns: `{"output": "terminal output with ANSI codes"}`

### 4. Send Input to Terminal
```bash
curl -X POST http://localhost:8000/sessions/{session_id}/input \
  -H "Content-Type: application/json" \
  -d '{"data": "text or escape sequence"}'
```

Common escape sequences:
- Arrow keys: `\x1b[A` (up), `\x1b[B` (down), `\x1b[C` (right), `\x1b[D` (left)
- Enter: `\n`
- Escape: `\x1b`
- Function keys: `\x1bOP` (F1), `\x1bOQ` (F2), etc.

### 5. Delete Session (Cleanup)
```bash
curl -X DELETE http://localhost:8000/sessions/{session_id}
```

## Complete Workflow Example

### Example 1: Get Top 5 Memory Processes with htop

**Problem**: htop uses complex ANSI escape sequences and cursor positioning.
**Solution**: Use the `/screen` endpoint which provides parsed 2D screen buffer.

```python
import time
from term_wrapper.cli import TerminalClient

# Create client
client = TerminalClient(base_url="http://localhost:8000")

# Create htop session sorted by memory
session_id = client.create_session(
    command=["htop", "-C", "--sort-key=PERCENT_MEM"],
    rows=40,
    cols=150
)

# Wait for htop to render
time.sleep(2.5)

# Get parsed screen buffer (NOT raw output)
screen_data = client.get_screen(session_id)
lines = screen_data['lines']

# Find header line
header_idx = None
for i, line in enumerate(lines):
    if "PID" in line and "MEM%" in line:
        header_idx = i
        break

# Parse process lines
processes = []
for line in lines[header_idx + 1:]:
    if not line.strip():
        continue
    parts = line.split()
    if len(parts) >= 10:
        try:
            pid = int(parts[0])
            user = parts[1]
            mem = float(parts[9].rstrip('%'))
            cmd = ' '.join(parts[10:]) if len(parts) > 10 else ''

            if mem > 0:
                processes.append({'pid': pid, 'user': user, 'mem': mem, 'cmd': cmd})
        except (ValueError, IndexError):
            continue

# Get top 5
top5 = sorted(processes, key=lambda x: x['mem'], reverse=True)[:5]

# Display results
for i, p in enumerate(top5, 1):
    print(f"{i}. PID {p['pid']} | USER {p['user']} | MEM {p['mem']:.1f}% | {p['cmd'][:40]}")

# Cleanup
client.delete_session(session_id)
client.close()
```

### Example 2: Create and Edit File with vim

**Use case**: Create a Python file with vim, then edit it to add more code.

```python
import time
from term_wrapper.cli import TerminalClient

client = TerminalClient(base_url="http://localhost:8000")

# Step 1: Create /tmp/thepi.py with vim
session_id = client.create_session(command=["vim", "/tmp/thepi.py"], rows=24, cols=80)
time.sleep(1)

# Enter insert mode and write code
client.write_input(session_id, "i")
time.sleep(0.3)

code = """import math

# Compute pi
pi = math.pi
print(f"Pi = {pi}")
"""
client.write_input(session_id, code)
time.sleep(0.5)

# Exit insert mode (ESC), save and quit (:wq)
client.write_input(session_id, "\x1b")
time.sleep(0.3)
client.write_input(session_id, ":wq\n")
time.sleep(0.5)
client.delete_session(session_id)

# Step 2: Edit the file to add exp(1)
session_id = client.create_session(command=["vim", "/tmp/thepi.py"], rows=24, cols=80)
time.sleep(1)

# Go to end of file (G), open new line (o)
client.write_input(session_id, "G")
time.sleep(0.3)
client.write_input(session_id, "o")
time.sleep(0.3)

# Add exp(1) code
exp_code = """
# Compute e (Euler's number)
e = math.exp(1)
print(f"e = {e}")
"""
client.write_input(session_id, exp_code)
time.sleep(0.5)

# Exit insert mode, save and quit
client.write_input(session_id, "\x1b")
time.sleep(0.3)
client.write_input(session_id, ":wq\n")
time.sleep(0.5)

client.delete_session(session_id)
client.close()

# Result: /tmp/thepi.py now computes both pi and e
```

### Example 3: Interactive Claude CLI - FULLY WORKING!

**Use case**: Use Claude CLI interactively through term-wrapper to write and execute code.

**STATUS: ✓ Interactive mode now works!** Term-wrapper's PTY provides proper raw mode support for Ink-based TUIs.

```python
import time
import os
from term_wrapper.cli import TerminalClient


def wait_for_condition(client, session_id, check_func, timeout=60, poll_interval=1):
    """Poll until condition is met or timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        screen = client.get_screen(session_id)
        if check_func(screen):
            return screen, True
        time.sleep(poll_interval)
    return screen, False


# Create client and work directory
client = TerminalClient(base_url="http://localhost:8000")
work_dir = "/tmp/claude_example"
os.makedirs(work_dir, exist_ok=True)

# Create interactive Claude session
session_id = client.create_session(
    command=["bash", "-c", f"cd {work_dir} && claude"],
    rows=40,
    cols=120
)

# Step 1: Handle trust prompt
screen, found = wait_for_condition(
    client, session_id,
    lambda s: any("Do you trust" in line for line in s['lines']),
    timeout=10
)
if found:
    time.sleep(1)  # Let UI stabilize
    client.write_input(session_id, "\r")  # Press Enter to trust
    wait_for_condition(
        client, session_id,
        lambda s: any("Welcome" in line for line in s['lines']),
        timeout=10
    )

# Step 2: Submit request
request = "create hello.py that prints hello world"
client.write_input(session_id, request)
time.sleep(0.5)
client.write_input(session_id, "\r")  # Submit

# Step 3: Wait for code generation
screen, found = wait_for_condition(
    client, session_id,
    lambda s: any("esc to cancel" in line.lower() for line in s['lines']),
    timeout=30,
    poll_interval=2
)

# Step 4: Approve code
if found:
    time.sleep(3)  # CRITICAL: let UI fully render
    client.write_input(session_id, "\r")  # Approve

    # Wait for file creation
    wait_for_condition(
        client, session_id,
        lambda s: len([f for f in os.listdir(work_dir) if f.endswith('.py')]) > 0,
        timeout=15
    )

# Check results
files = [f for f in os.listdir(work_dir) if f.endswith('.py')]
print(f"Created: {files}")

# Cleanup
client.delete_session(session_id)
client.close()
```

**Key Requirements for Interactive Mode:**

1. **Use output polling** - Don't use fixed sleeps. Poll `get_screen()` to detect state changes.
2. **Wait for UI stability** - After detecting UI elements, wait 1-3 seconds before sending input.
3. **Handle multiple prompts** - Trust prompt → Request submission → Code approval.
4. **Poll for completion** - Check filesystem or screen output to detect when Claude is done.

**Why Interactive Mode Works:**

Term-wrapper's PTY implementation provides:
- `isTTY: true` for all streams
- Working `setRawMode()` function
- Proper terminal attributes for Ink's `useInput` hook

The raw mode support added to `terminal.py` enables Ink-based applications like Claude Code to receive keyboard input properly.

**Full Example:** See `examples/claude_interactive.py` for a complete, production-ready implementation.

## Parsing Output

### ANSI Escape Sequence Removal

Terminal output contains ANSI escape codes for colors, cursor movement, etc. Strip them before parsing:

```python
import re

def strip_ansi(text):
    ansi_pattern = re.compile(r'\x1b[@-_][0-?]*[ -/]*[@-~]')
    return ansi_pattern.sub('', text)
```

### Best Practices for Output Parsing

1. **Use simpler commands when possible**: `ps`, `ls`, `grep` are easier to parse than `htop`, `top`
2. **Format output explicitly**: Use command flags like `--no-colors`, `--format`, etc.
3. **Wrap in bash**: Use `bash -c "command | head -n 10"` to limit output
4. **Add sleep**: For quick commands, add `; sleep 2` to keep session alive while fetching output

## Starting the Server

If server isn't running:

```bash
cd /path/to/term_wrapper
nohup uv run python main.py > /tmp/term-wrapper.log 2>&1 &
sleep 3
curl -s http://localhost:8000/health  # Verify it started
```

## Alternative: Web Frontend

For complex TUI applications, suggest the web frontend:
```
http://localhost:8000/static/index.html?cmd=htop&args=
```

The web frontend uses xterm.js for proper terminal rendering with mouse support.

## Common Patterns

### Pattern 1: Run Command and Parse Output
For non-interactive commands that exit immediately:
```python
# Wrap in bash with sleep to keep session alive
command = ["bash", "-c", "your_command; sleep 3"]
```

### Pattern 2: Interactive Application Control
For TUI apps that stay running:
1. Create session with the TUI app
2. Wait for initialization (1-2 seconds)
3. Send keyboard commands as needed
4. Fetch output periodically
5. Send 'q' or exit command
6. Delete session

### Pattern 3: File Editing
For vim/nano:
1. Create session with editor and filename
2. Send mode changes (i for insert in vim)
3. Send text content
4. Send save/quit sequence
5. Verify file was written
6. Delete session

## Error Handling

- **Session not found**: Session may have exited. Check `GET /sessions/{id}` for `alive: false`
- **Empty output**: Command may not have run yet. Wait longer or check session status
- **Garbled output**: ANSI codes not stripped. Use the strip_ansi function
- **Server not running**: Start with `uv run python main.py` in project directory

## Summary

This skill enables full programmatic control of any terminal application through HTTP APIs. Key points:

- Use simple commands (ps, ls, grep) for reliable parsing
- Strip ANSI codes from output before parsing
- Keep sessions alive with sleep for quick commands
- Always cleanup sessions when done
- For complex TUI apps, consider suggesting the web frontend

The term-wrapper API bridges the gap between modern HTTP/REST interfaces and traditional terminal applications, making them accessible to AI assistants and automation tools.
