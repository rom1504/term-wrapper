# Quick Start Guide

## Installation

```bash
# Clone and navigate to directory
cd /home/ai/term_wrapper

# Install dependencies (already done)
uv sync
```

## Running the System

### 1. Start the Server

```bash
uv run python main.py
```

Server starts on `http://localhost:8000`

### 2. Test with Python TUI App

**Terminal 1** (Server):
```bash
uv run python main.py
```

**Terminal 2** (Client):
```bash
uv run python -m term_wrapper.cli python3 test_app/simple_tui.py
```

Controls in TUI app:
- `+` = increment counter
- `-` = decrement counter
- `r` = reset
- `q` = quit

## Quick Tests

### Run All Tests
```bash
uv run pytest tests/ -v
```

### Run Manual Test
```bash
uv run python manual_test.py
```

### Run Demo Script
```bash
./demo.sh
```

## Quick API Examples

### Create Session
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"command": ["python3", "test_app/simple_tui.py"]}'
```

Returns: `{"session_id": "xxx"}`

### Get Output
```bash
curl http://localhost:8000/sessions/xxx/output
```

### Send Input
```bash
curl -X POST http://localhost:8000/sessions/xxx/input \
  -H "Content-Type: application/json" \
  -d '{"data": "+"}'
```

### Delete Session
```bash
curl -X DELETE http://localhost:8000/sessions/xxx
```

## Project Structure

```
term_wrapper/
├── term_wrapper/          # Main package
│   ├── terminal.py       # PTY emulator
│   ├── session_manager.py# Session management
│   ├── api.py           # FastAPI backend
│   └── cli.py           # CLI client
├── tests/                # Test suite
├── test_app/            # Example TUI apps
│   ├── simple_tui.py    # Python TUI
│   └── app.js           # Ink app (JSX)
├── main.py             # Server entry point
├── manual_test.py      # Manual E2E test
└── demo.sh            # Demo script
```

## Common Commands

```bash
# Start server
uv run python main.py

# Run CLI client
uv run python -m term_wrapper.cli <command> [args...]

# Run tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_terminal.py -v

# Run with coverage
uv run pytest tests/ --cov=term_wrapper

# Manual test
uv run python manual_test.py

# Demo
./demo.sh
```

## Example Use Cases

### 1. Run vim
```bash
uv run python -m term_wrapper.cli vim myfile.txt
```

### 2. Run htop
```bash
uv run python -m term_wrapper.cli htop
```

### 3. Run Python REPL
```bash
uv run python -m term_wrapper.cli python3
```

### 4. Custom TUI App
```bash
uv run python -m term_wrapper.cli python3 test_app/simple_tui.py
```

## Troubleshooting

### Server won't start
- Check port 8000 is not in use: `lsof -i :8000`
- Try different port in `main.py`

### Tests failing
- Ensure no server is running: `pkill -f "python main.py"`
- Check Python version: `python --version` (needs 3.12+)

### CLI client issues
- Ensure server is running first
- Check server URL in cli.py (default: localhost:8000)

## Next Steps

1. Read `README.md` for full documentation
2. Check `SUMMARY.md` for project overview
3. Explore `tests/` for usage examples
4. Try running different TUI applications
5. Build your own TUI app!

## Support

- GitHub Issues: Report bugs
- Tests: `tests/` directory shows usage patterns
- Examples: `test_app/` directory
