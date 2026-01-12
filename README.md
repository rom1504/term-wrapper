# Terminal Wrapper

A full-featured terminal emulator with web backend that can run any TUI (Text User Interface) application and control it via HTTP/WebSocket APIs.

## Features

- **PTY-based Terminal Emulation**: Full pseudo-terminal support for running terminal applications
- **FastAPI Backend**: RESTful API and WebSocket endpoints for terminal control
- **Session Management**: Create, manage, and control multiple terminal sessions
- **Python CLI Client**: Interactive CLI for connecting to remote terminal sessions
- **Comprehensive Tests**: Unit, integration, and end-to-end tests

## What Works Well

✅ **Simple commands**: `ls`, `cat`, `echo`, shell scripts
✅ **Interactive programs**: Python REPL, bash, simple TUI apps
✅ **Batch mode tools**: `top -b`, monitoring scripts
✅ **ANSI color output**: Colors are captured (but need client-side rendering)

## What Needs Client-Side Terminal Emulator

⚠️ **Complex TUI apps**: `vim`, `emacs`, `htop`, `tmux`
⚠️ **Full-screen apps**: These work but output raw escape sequences
⚠️ **Mouse support**: PTY captures events, client must handle them

**Note**: For complex TUI apps, pair this backend with a terminal emulator library like [xterm.js](https://xtermjs.org/) on the frontend.

## Architecture

```
┌─────────────────┐
│   CLI Client    │ ← Python client for interactive control
└────────┬────────┘
         │ HTTP/WebSocket
         ↓
┌─────────────────┐
│  FastAPI Server │ ← Web backend with REST + WebSocket
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Session Manager │ ← Manages multiple terminal sessions
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ PTY Terminal    │ ← Pseudo-terminal for running TUI apps
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   TUI App       │ ← Any terminal application (vim, htop, etc.)
└─────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Start the Server

```bash
uv run python main.py
```

Server will start on `http://localhost:8000`

### 3. Run a TUI App

#### Option A: Using the CLI Client

```bash
uv run python -m term_wrapper.cli python3 test_app/simple_tui.py
```

#### Option B: Using HTTP API

```bash
# Create a session
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"command": ["python3", "test_app/simple_tui.py"], "rows": 24, "cols": 80}'

# Returns: {"session_id": "xxx-xxx-xxx"}

# Get output
curl http://localhost:8000/sessions/{session_id}/output

# Send input
curl -X POST http://localhost:8000/sessions/{session_id}/input \
  -H "Content-Type: application/json" \
  -d '{"data": "+"}'

# Delete session
curl -X DELETE http://localhost:8000/sessions/{session_id}
```

## API Reference

### REST Endpoints

- `POST /sessions` - Create a new terminal session
- `GET /sessions` - List all active sessions
- `GET /sessions/{id}` - Get session information
- `DELETE /sessions/{id}` - Delete a session
- `POST /sessions/{id}/input` - Send input to terminal
- `POST /sessions/{id}/resize` - Resize terminal window
- `GET /sessions/{id}/output` - Get terminal output

### WebSocket Endpoint

- `WS /sessions/{id}/ws` - Real-time bidirectional terminal I/O

## Testing

Run all tests:

```bash
uv run pytest tests/ -v
```

Run specific test suites:

```bash
# Unit tests
uv run pytest tests/test_terminal.py tests/test_api.py -v

# End-to-end tests
uv run pytest tests/test_e2e.py -v

# Integration tests with TUI apps
uv run pytest tests/test_ink_integration.py -v

# Vim tests
uv run pytest tests/test_vim.py -v
```

## Application Reports

We've tested various TUI applications with detailed reports:

| Application | Status | Report | Tests |
|-------------|--------|--------|-------|
| vim | ✅ Fully Functional | [reports/vim_report.md](reports/vim_report.md) | [tests/test_vim.py](tests/test_vim.py) |

Each report includes:
- Test methodology and results
- Usage examples (HTTP & WebSocket)
- Technical details (escape sequences, commands)
- Performance metrics
- Best practices

See [reports/README.md](reports/README.md) for how to test and document new applications.

## Example TUI Apps

### Python TUI App (`test_app/simple_tui.py`)

A simple counter application demonstrating:
- Terminal control codes
- Raw mode input handling
- Interactive key bindings

Controls:
- `+` : Increment counter
- `-` : Decrement counter
- `r` : Reset counter
- `q` : Quit

## Project Structure

```
term_wrapper/
├── term_wrapper/           # Main package
│   ├── terminal.py        # PTY-based terminal emulator
│   ├── session_manager.py # Session management
│   ├── api.py            # FastAPI backend
│   └── cli.py            # CLI client
├── tests/                 # Test suite
│   ├── test_terminal.py   # Terminal emulator tests
│   ├── test_api.py        # API tests
│   ├── test_e2e.py       # End-to-end tests
│   └── test_ink_integration.py # TUI app tests
├── test_app/             # Example TUI applications
│   └── simple_tui.py     # Python TUI demo
├── main.py              # Server entry point
└── pyproject.toml       # Project configuration
```

## Development

Built with:
- **uv** - Fast Python package manager
- **FastAPI** - Modern web framework
- **uvicorn** - ASGI server
- **pytest** - Testing framework
- **websockets** - WebSocket support

## License

ISC
