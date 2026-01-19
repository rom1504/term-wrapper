# Term-Wrapper Skills for Claude Code

This directory contains skill definitions for using term-wrapper with Claude Code.

## Available Skills

### `/term-wrapper` - Run Terminal Applications via API

Launch and interact with any terminal application through the term-wrapper HTTP API.

**What it does:**
- Runs any CLI/TUI application via HTTP
- Sends keyboard input programmatically
- Retrieves and parses terminal output
- Enables AI control of terminal applications

See [term-wrapper.md](./term-wrapper.md) for complete self-contained instructions.

## How Skills Work

Skills are special instructions that help Claude understand how to use term-wrapper to run interactive TUI applications. When you invoke a skill like `/term-wrapper htop`, Claude will:

1. Start the term-wrapper server if needed
2. Create a terminal session with your command
3. Show you the TUI application output
4. Help you interact with it by sending keyboard commands
5. Clean up when you're done

## Examples

### Running htop

Try the automated demo:
```bash
uv run python examples/htop_demo.py
```

Or use Claude Code:
```
/term-wrapper htop
```

Claude will launch htop and help you navigate through:
- Process list (arrow keys)
- Tree view (press 't')
- Sort options (F6)
- Filtering and searching

### Editing Files with vim

```
/term-wrapper vim myfile.txt
```

Claude will help you:
- Enter insert mode ('i')
- Edit content
- Save and quit (':wq')
- Navigate the file

### Python REPL

```
/term-wrapper python
```

Interact with a Python interpreter through the terminal wrapper.

## Web Frontend Alternative

For complex interactions, you can also use the web frontend:

```bash
# Start server
uv run python main.py

# Open in browser
http://localhost:8000/static/index.html?cmd=htop
```

The web frontend provides a full xterm.js terminal emulator with mouse support and better rendering.

## API Reference

All skills use the term-wrapper REST API:

- `POST /sessions` - Create terminal session
- `GET /sessions/{id}/output` - Get output
- `POST /sessions/{id}/input` - Send input
- `DELETE /sessions/{id}` - Clean up

See [../docs/API.md](../docs/API.md) for full API documentation.
