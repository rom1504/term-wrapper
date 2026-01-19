---
name: Term Wrapper
description: Control any terminal application (TUI, CLI, or interactive program) programmatically through HTTP API or CLI commands. Use when you need to: (1) Run terminal applications like vim, htop, nano, or less, (2) Automate CLI tools programmatically, (3) Send keyboard input to running applications, (4) Retrieve and parse terminal output, or (5) Control interactive programs like Claude CLI, Python REPL, or bash shells.
---

# Term Wrapper

Run any terminal application through the term-wrapper HTTP API or CLI commands. This enables programmatic control of TUI applications, automated CLI workflows, and interactive terminal sessions.

## ⚠️ IMPORTANT: Approach Priority

**ALWAYS use this priority order:**

1. **CLI Subcommands (FIRST CHOICE)** - Use `term-wrapper` commands
   - Simplest approach, works directly from bash
   - All examples below show CLI commands
   - **Use this unless it truly doesn't work**

2. **Python Client Library (SECOND CHOICE)** - Only if CLI fails or is insufficient
   - Use `from term_wrapper.cli import TerminalClient`
   - See "Alternative: Python Client Library" section below
   - Only use if CLI commands don't meet your needs

3. **Direct HTTP API (LAST RESORT)** - Only if both CLI and Python fail
   - Use curl with REST endpoints
   - See "Core API Operations (Low-Level HTTP)" section below
   - Most complex approach, avoid unless necessary

**Default to CLI commands. Only escalate to Python or HTTP if you encounter errors.**

## Recommended Approach: CLI Subcommands

**The easiest way to use term-wrapper is via CLI subcommands.** This requires no Python code and works directly from bash/shell scripts.

**Auto-Start**: The backend server starts automatically when you run any `term-wrapper` command. No need to manually start a server! The server picks an available port and saves it to `~/.term-wrapper/port`.

**Note**: In development environments using uv, prefix all commands with `uv run`, e.g., `uv run term-wrapper --help`. After pip install, use `term-wrapper` directly.

### Quick Example: Automate Claude Code

```bash
#!/bin/bash
# Create Claude session and make it create a file

# Create session
SESSION=$(term-wrapper create bash -c "cd /tmp && claude" | \
          python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

# Wait for and accept trust prompt
term-wrapper wait-text $SESSION "Do you trust" --timeout 10
term-wrapper send $SESSION "\r"

# Wait for main UI
term-wrapper wait-text $SESSION "Welcome" --timeout 10

# Submit request
term-wrapper send $SESSION "create hello.py\r"

# Wait a bit and check for approval UI
sleep 5
TEXT=$(term-wrapper get-text $SESSION)
if echo "$TEXT" | grep -qi "esc to cancel"; then
    sleep 2
    term-wrapper send $SESSION "\r"  # Approve
fi

# Cleanup
term-wrapper delete $SESSION
```

### Available CLI Subcommands

```bash
# Session Management
term-wrapper create [--rows N] [--cols N] COMMAND...
term-wrapper list
term-wrapper info SESSION_ID
term-wrapper delete SESSION_ID

# Input/Output
term-wrapper send SESSION_ID TEXT           # Supports \n, \r, \t, \x1b
term-wrapper get-text SESSION_ID            # Clean text (ANSI stripped)
term-wrapper get-output SESSION_ID          # Raw output with ANSI
term-wrapper get-screen SESSION_ID          # 2D screen buffer (JSON)

# Waiting Primitives
term-wrapper wait-text SESSION_ID TEXT [--timeout SECS]
term-wrapper wait-quiet SESSION_ID [--duration SECS]

# Interactive
term-wrapper attach SESSION_ID              # WebSocket interactive mode
term-wrapper web SESSION_ID                 # Open session in browser

# Server Management
term-wrapper stop                           # Stop the background server
```

**When to use CLI vs Python:**
- Use **CLI subcommands** for simple automation, bash scripts, one-off tasks
- Use **Python client** for complex logic, conditional flows, error handling

## Alternative: Python Client Library

For more complex interactions, use the Python client with high-level primitives:

```python
from term_wrapper.cli import TerminalClient

client = TerminalClient()
session_id = client.create_session(command=["bash"], rows=40, cols=120)

# High-level primitives
client.wait_for_text(session_id, "Welcome", timeout=10)
client.write_input(session_id, "ls -la\r")
text = client.get_text(session_id)  # Clean text
client.wait_for_quiet(session_id, duration=2)  # Wait for stability

client.delete_session(session_id)
client.close()
```

## Core API Operations (Low-Level HTTP)

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
**Solution**: Use the CLI with `get-screen` to get parsed 2D screen buffer, then parse it.

```bash
#!/bin/bash
# Get top memory processes from htop using CLI

# Create htop session sorted by memory
SESSION=$(term-wrapper create --rows 40 --cols 150 htop -C --sort-key=PERCENT_MEM | \
          python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

# Wait for htop to render
sleep 2.5

# Get parsed screen buffer (clean 2D text array, no ANSI codes)
term-wrapper get-screen $SESSION

# The output is JSON with 'lines' array - parse it to extract process info
# Look for the header line containing "PID" and "MEM%", then parse subsequent lines

# Cleanup when done
term-wrapper delete $SESSION
```

### Example 2: Create and Edit File with vim

**Use case**: Create a Python file with vim, then edit it to add more code.

```bash
#!/bin/bash
# Create and edit a Python file with vim using CLI

# Step 1: Create /tmp/thepi.py with vim
SESSION=$(term-wrapper create vim /tmp/thepi.py | \
          python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
sleep 1

# Enter insert mode and write code
term-wrapper send $SESSION "i"
sleep 0.3

# Type the code (note: \n for newlines)
term-wrapper send $SESSION "import math\\n\\n# Compute pi\\npi = math.pi\\nprint(f\\\"Pi = {pi}\\\")\\n"
sleep 0.5

# Exit insert mode (ESC), save and quit
term-wrapper send $SESSION "\x1b"
sleep 0.3
term-wrapper send $SESSION ":wq\r"
sleep 0.5
term-wrapper delete $SESSION

# Step 2: Edit the file to add exp(1)
SESSION=$(term-wrapper create vim /tmp/thepi.py | \
          python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
sleep 1

# Go to end of file (G), open new line (o)
term-wrapper send $SESSION "G"
sleep 0.3
term-wrapper send $SESSION "o"
sleep 0.3

# Add exp(1) code
term-wrapper send $SESSION "\\n# Compute e (Euler's number)\\ne = math.exp(1)\\nprint(f\\\"e = {e}\\\")\\n"
sleep 0.5

# Exit insert mode, save and quit
term-wrapper send $SESSION "\x1b"
sleep 0.3
term-wrapper send $SESSION ":wq\r"
sleep 0.5
term-wrapper delete $SESSION

# Result: /tmp/thepi.py now computes both pi and e
cat /tmp/thepi.py
```

### Example 3: Interactive Claude CLI

**Use case**: Use Claude CLI interactively through term-wrapper to write and execute code.

This is the same example shown at the top of this document. See "Quick Example: Automate Claude Code" above for the complete CLI implementation.

**Key Requirements for Interactive Mode:**

1. **Use output polling** - Use `wait-text` or `wait-quiet` CLI commands instead of fixed sleeps.
2. **Wait for UI stability** - After detecting UI elements with `wait-text`, add 1-3 second sleep before sending input.
3. **Handle multiple prompts** - Trust prompt → Request submission → Code approval.
4. **Poll for completion** - Use `wait-quiet` to detect when output stabilizes, or check filesystem.

**Why Interactive Mode Works:**

Term-wrapper's PTY implementation provides:
- `isTTY: true` for all streams
- Working `setRawMode()` function
- Proper terminal attributes for Ink's `useInput` hook

The raw mode support added to `terminal.py` enables Ink-based applications like Claude Code to receive keyboard input properly.

**Full Example:** See `examples/claude_interactive.py` for a complete, production-ready Python implementation, or use the CLI commands shown in "Quick Example: Automate Claude Code" above for shell scripts.

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

This skill enables full programmatic control of any terminal application through CLI commands or HTTP APIs. Key points:

- **Prefer CLI subcommands** for simplicity and shell scripting
- Use `get-screen` for complex TUI apps to get clean parsed text
- Use `wait-text` and `wait-quiet` instead of fixed sleeps
- Always cleanup sessions with `delete` when done
- CLI handles escape sequences: `\n`, `\r`, `\t`, `\x1b`

The term-wrapper API bridges the gap between modern HTTP/REST interfaces and traditional terminal applications, making them accessible to AI assistants and automation tools.
