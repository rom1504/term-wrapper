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

## Claude Code Example

### `claude_interactive.py` ⭐
**Full interactive Claude Code session** with proper UI handling:
- Handles trust prompt
- Submits requests interactively
- Waits for code generation
- Approves code changes
- Verifies file creation

Uses the new primitives (`wait_for_text`, `wait_for_condition`, `wait_for_quiet`)
for clean, readable code with proper output polling.

```bash
python examples/claude_interactive.py
```

## CLI Alternative

These examples use the Python client library. You can also use the `term-wrapper` CLI commands directly:

```bash
# Create a session
SESSION=$(uv run term-wrapper create htop | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

# Send input
uv run term-wrapper send $SESSION "q"

# Get output
uv run term-wrapper get-text $SESSION

# Delete session
uv run term-wrapper delete $SESSION
```

See the [CLI documentation](../README.md#cli-subcommands) for all available commands.

## Tips

- Use `claude_interactive.py` to see the new helper primitives in action
- Check the skill documentation: `skill/SKILL.md`
- All examples use the new primitives: `wait_for_text()`, `wait_for_quiet()`, `get_text()`
- For shell scripting, prefer CLI commands over Python for simplicity
