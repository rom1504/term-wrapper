# Examples

This directory contains example scripts demonstrating term-wrapper usage.

## Basic Examples

### `simple_example.py`
Basic session creation and output reading. Good starting point.

```bash
python examples/simple_example.py
```

### `simple_tui.py`
Launching a simple TUI application (interactive shell).

```bash
python examples/simple_tui.py
```

### `primitives_demo.py` ⭐ NEW
Demonstrates all the new helper primitives for easier interactive control:
- `get_text()` - Clean text extraction with ANSI stripping
- `wait_for_text()` - Wait for specific text
- `wait_for_quiet()` - Wait for output to stabilize
- `get_new_lines()` - Incremental updates

```bash
python examples/primitives_demo.py
```

## Application-Specific Examples

### `vim_example.py`
Creating and editing files with vim through term-wrapper.

```bash
python examples/vim_example.py
```

### `htop_demo.py`
Parsing htop output to get top memory-using processes.

```bash
python examples/htop_demo.py
```

## Claude Code Examples

### `claude_interactive.py` ⭐ RECOMMENDED
**Full interactive Claude Code session** with proper UI handling:
- Handles trust prompt
- Submits requests interactively
- Waits for code generation
- Approves code changes
- Verifies file creation

Uses output polling and proper timing. This is the complete working example.

```bash
python examples/claude_interactive.py
```

### `claude_piped.py`
**Alternative non-interactive approach** using piped stdin:
- Faster for simple tasks
- No interactive UI handling needed
- Good for automation scripts

```bash
python examples/claude_piped.py
```

## Key Differences

| Feature | Interactive (`claude_interactive.py`) | Piped (`claude_piped.py`) |
|---------|--------------------------------------|---------------------------|
| **Approach** | Full TUI interaction with keyboard input | Pipe request to stdin, bypass TUI |
| **Speed** | Slower (waits for UI) | Faster (no UI) |
| **Control** | Full control, see progress | Fire and forget |
| **Complexity** | Higher (state detection) | Lower (simple command) |
| **Use case** | When you need to interact mid-task | Simple one-shot requests |

## Tips

- Use `primitives_demo.py` to learn the new helper methods
- Use `claude_interactive.py` as template for interactive workflows
- Use `claude_piped.py` for simple automation
- Check the skill documentation: `skills/term-wrapper.md`
