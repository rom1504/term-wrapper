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

### Example 1: Get Top Memory Processes

**Problem**: htop output has complex ANSI codes that are hard to parse.
**Solution**: Use `ps` with specific formatting for easier parsing.

```python
import requests, re

# Create session running ps
resp = requests.post("http://localhost:8000/sessions", json={
    "command": ["bash", "-c", "ps aux --sort=-%mem | head -10; sleep 5"],
    "rows": 50,
    "cols": 200
})
session_id = resp.json()['session_id']

# Wait for command to complete
import time
time.sleep(2)

# Get output
resp = requests.get(f"http://localhost:8000/sessions/{session_id}/output")
output = resp.json().get('output', '')

# Strip ANSI codes
ansi = re.compile(r'\x1b[@-_][0-?]*[ -/]*[@-~]')
clean = ansi.sub('', output)

# Parse ps output (already sorted by memory)
lines = clean.strip().split('\n')
for line in lines[1:6]:  # Top 5 processes
    print(line)

# Cleanup
requests.delete(f"http://localhost:8000/sessions/{session_id}")
```

### Example 2: Interactive vim Session

```python
import requests, time

# Create vim session
resp = requests.post("http://localhost:8000/sessions", json={
    "command": ["vim", "/tmp/test.txt"],
    "rows": 30,
    "cols": 100,
    "env": {"TERM": "xterm-256color"}
})
session_id = resp.json()['session_id']
time.sleep(1)

# Enter insert mode
requests.post(f"http://localhost:8000/sessions/{session_id}/input",
              json={"data": "i"})

# Type some text
requests.post(f"http://localhost:8000/sessions/{session_id}/input",
              json={"data": "Hello from term-wrapper!\n"})

# Exit insert mode (ESC)
requests.post(f"http://localhost:8000/sessions/{session_id}/input",
              json={"data": "\x1b"})

# Save and quit (:wq)
requests.post(f"http://localhost:8000/sessions/{session_id}/input",
              json={"data": ":wq\n"})
time.sleep(1)

# Cleanup
requests.delete(f"http://localhost:8000/sessions/{session_id}")
```

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
