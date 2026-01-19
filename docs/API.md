# API Documentation

## Overview

The Terminal Wrapper API provides HTTP REST endpoints and WebSocket connections for controlling remote terminal sessions.

## Base URL

```
http://localhost:8000
```

## REST API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Create Terminal Session

```http
POST /sessions
```

**Request Body:**
```json
{
  "command": ["python3", "-i"],  // Command and arguments
  "rows": 24,                     // Terminal rows (default: 24)
  "cols": 80,                     // Terminal columns (default: 80)
  "env": {                        // Optional environment variables
    "TERM": "xterm-256color"
  }
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "command": ["python3"],
    "rows": 24,
    "cols": 80
  }'
```

---

### List All Sessions

```http
GET /sessions
```

**Response:**
```json
{
  "sessions": [
    "550e8400-e29b-41d4-a716-446655440000",
    "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  ]
}
```

---

### Get Session Info

```http
GET /sessions/{session_id}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "alive": true,
  "rows": 24,
  "cols": 80
}
```

**Status Codes:**
- `200` - Success
- `404` - Session not found

---

### Delete Session

```http
DELETE /sessions/{session_id}
```

**Response:**
```json
{
  "status": "deleted"
}
```

**Status Codes:**
- `200` - Success
- `404` - Session not found

---

### Send Input to Terminal

```http
POST /sessions/{session_id}/input
```

**Request Body:**
```json
{
  "data": "ls -la\n"  // Input string to send to terminal
}
```

**Response:**
```json
{
  "status": "ok"
}
```

**Examples:**

Send a command:
```bash
curl -X POST http://localhost:8000/sessions/{id}/input \
  -H "Content-Type: application/json" \
  -d '{"data": "2 + 2\n"}'
```

Send arrow keys (ANSI escape sequences):
```bash
# Up arrow: \x1b[A
curl -X POST http://localhost:8000/sessions/{id}/input \
  -H "Content-Type: application/json" \
  -d '{"data": "\u001b[A"}'
```

---

### Get Terminal Output

```http
GET /sessions/{session_id}/output?clear=true
```

**Query Parameters:**
- `clear` (boolean, default: true) - Clear output buffer after reading

**Response:**
```json
{
  "output": "Hello World\nLine 2\n"
}
```

**Note:** Output includes ANSI escape sequences. You'll need a terminal emulator to render them properly.

---

### Resize Terminal

```http
POST /sessions/{session_id}/resize
```

**Request Body:**
```json
{
  "rows": 40,
  "cols": 120
}
```

**Response:**
```json
{
  "status": "ok"
}
```

This sends SIGWINCH to the terminal process to notify it of the size change.

---

## WebSocket API

### Real-Time Terminal I/O

```
ws://localhost:8000/sessions/{session_id}/ws
```

**Protocol:**
- **Receive** - Binary messages containing terminal output
- **Send** - Binary messages containing terminal input

**Special Messages:**
- `__TERMINAL_CLOSED__` (text) - Sent when terminal process exits

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/sessions/xxx/ws');

// Receive terminal output
ws.onmessage = (event) => {
  if (event.data === '__TERMINAL_CLOSED__') {
    console.log('Terminal closed');
    return;
  }

  // event.data is binary - render in terminal emulator
  const output = new TextDecoder().decode(event.data);
  terminalElement.write(output);
};

// Send input
ws.send(new TextEncoder().encode('ls\n'));

// Send Ctrl+C
ws.send(new Uint8Array([3]));
```

**Python Example:**
```python
import asyncio
import websockets

async def connect():
    async with websockets.connect('ws://localhost:8000/sessions/xxx/ws') as ws:
        # Send input
        await ws.send(b'echo hello\n')

        # Receive output
        while True:
            output = await ws.recv()
            if isinstance(output, bytes):
                print(output.decode('utf-8', errors='replace'))
            elif output == '__TERMINAL_CLOSED__':
                break

asyncio.run(connect())
```

---

## Error Responses

All endpoints may return error responses:

**404 Not Found:**
```json
{
  "detail": "Session not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Error message"
}
```

---

## Terminal Features

### Supported
- ✅ Basic terminal I/O
- ✅ ANSI escape sequences (captured, not interpreted)
- ✅ Terminal resizing (SIGWINCH)
- ✅ Process signals
- ✅ Multiple concurrent sessions
- ✅ Raw terminal mode
- ✅ Interactive applications

### Client Needs to Handle
- ⚠️ ANSI escape sequence rendering (colors, cursor movement, etc.)
- ⚠️ Alternative screen buffer
- ⚠️ Mouse events
- ⚠️ Terminal queries (response to escape sequences)

### Known Limitations
- Complex TUI apps like `vim` work but require a proper terminal emulator on the client side
- No built-in terminal emulation (you get raw PTY output)
- No session persistence across server restarts

---

## Rate Limits

None currently implemented.

---

## Authentication

None currently implemented. **Do not expose to the internet without adding authentication!**

---

## Usage Recommendations

1. **For Simple Commands**: Use REST API
2. **For Interactive Apps**: Use WebSocket
3. **For TUI Apps**: Use WebSocket + terminal emulator library (xterm.js, etc.)
4. **Client Libraries**: Use the included Python CLI or build your own

---

## Example Use Cases

### 1. Run a Command and Get Output
```bash
# Create session
SESSION=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"command": ["ls", "-la"]}' | jq -r .session_id)

# Wait for completion
sleep 1

# Get output
curl -s http://localhost:8000/sessions/$SESSION/output | jq -r .output

# Cleanup
curl -s -X DELETE http://localhost:8000/sessions/$SESSION
```

### 2. Interactive Python REPL
```bash
# Create session
SESSION=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"command": ["python3"]}' | jq -r .session_id)

# Send commands
curl -s -X POST http://localhost:8000/sessions/$SESSION/input \
  -H "Content-Type: application/json" \
  -d '{"data": "print(\"Hello\")\n"}'

sleep 0.5

# Get output
curl -s http://localhost:8000/sessions/$SESSION/output | jq -r .output
```

### 3. Using the CLI Client
```bash
# Easiest way for interactive use - CLI subcommands
uv run term-wrapper create python3

# Or attach to existing session interactively
uv run term-wrapper attach <session_id>

# See all available commands
uv run term-wrapper --help
```
