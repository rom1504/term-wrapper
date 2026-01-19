# Testing Guide: Adding New TUI Applications

This guide explains how to test and document new TUI applications with the terminal wrapper, using our proven methodology from vim, htop, and Claude CLI.

## Overview

When adding a new TUI application, follow these steps:

1. **Create test file** (`tests/test_<app>.py`)
2. **Write comprehensive tests** (5-10 tests covering key features)
3. **Run tests and verify** (100% pass rate)
4. **Create report** (`reports/<app>_report.md`)
5. **Update main README** (add to application table)
6. **Commit and document** (git commit with clear message)

## Step-by-Step Process

### Step 1: Research the Application

Before writing tests, understand the application:

**Questions to answer:**
- What does the app do?
- How do you launch it? (`app`, `app --help`, `app file.txt`)
- What are the key features to test?
- How do you exit? (`q`, `:q`, `Ctrl+C`)
- Does it use full-screen TUI or simple output?
- What special keys does it use? (arrows, function keys, ESC)

**Example research for `less`:**
```bash
# Test manually first
less /etc/hosts

# Try various commands
# j/k - scroll down/up
# / - search
# q - quit
# h - help
```

### Step 2: Create Test File

Create `tests/test_<app>.py` with this template:

```python
"""E2E tests for <app> running in the terminal wrapper."""

import asyncio
import pytest
import httpx
import time
from multiprocessing import Process
import uvicorn


BASE_URL = "http://localhost:800X"  # Use unique port (8005, 8006, etc.)


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=800X,  # Match BASE_URL
        log_level="error",
    )


@pytest.fixture(scope="module")
def server():
    """Start server for tests."""
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(2)
    yield
    proc.terminate()
    proc.join(timeout=5)


@pytest.mark.asyncio
async def test_app_basic_launch(server):
    """Test launching <app>."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Your test here
        pass
```

**Key points:**
- Use unique port for each test file (avoid conflicts)
- Use module-scoped server fixture (faster)
- All tests should be `async def` with `@pytest.mark.asyncio`
- Always clean up sessions with `DELETE /sessions/{id}`

### Step 3: Write Core Tests

Write 5-10 tests covering these categories:

#### Test Categories

**1. Basic Launch Test**
- Verify app starts successfully
- Check for expected initial output
- Test with `--version` or `--help` if available

**Example (vim):**
```python
async def test_vim_basic_launch(server):
    response = await client.post("/sessions", json={
        "command": ["vim", "--version"],
        "rows": 24,
        "cols": 80,
        "env": {"TERM": "xterm-256color"}
    })
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    await asyncio.sleep(1.0)

    response = await client.get(f"/sessions/{session_id}/output")
    output = response.json()["output"]
    assert "VIM" in output or "Vi IMproved" in output

    await client.delete(f"/sessions/{session_id}")
```

**2. Interactive Mode Test**
- Launch app in full interactive mode
- Verify TUI renders (ANSI escape sequences)
- Check for expected UI elements

**Example (htop):**
```python
async def test_htop_interactive_mode(server):
    response = await client.post("/sessions", json={
        "command": ["htop"],
        "rows": 24,
        "cols": 80,
        "env": {
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor"
        }
    })
    session_id = response.json()["session_id"]

    await asyncio.sleep(1.0)

    response = await client.get(f"/sessions/{session_id}/output")
    output = response.json()["output"]

    # Check for ANSI codes and expected text
    assert "\x1b[" in output or "CPU" in output

    # Quit
    await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
    await asyncio.sleep(0.5)

    await client.delete(f"/sessions/{session_id}")
```

**3. Navigation/Input Test**
- Send keyboard input (arrow keys, letters)
- Verify app responds
- Test key bindings

**Example (less):**
```python
async def test_less_navigation(server):
    # Create file to view
    test_file = "/tmp/less_test.txt"
    with open(test_file, "w") as f:
        for i in range(100):
            f.write(f"Line {i}\n")

    response = await client.post("/sessions", json={
        "command": ["less", test_file],
        "rows": 24,
        "cols": 80,
        "env": {"TERM": "xterm-256color"}
    })
    session_id = response.json()["session_id"]

    await asyncio.sleep(0.5)

    # Press 'j' to scroll down
    await client.post(f"/sessions/{session_id}/input", json={"data": "j"})
    await asyncio.sleep(0.2)

    # Press 'k' to scroll up
    await client.post(f"/sessions/{session_id}/input", json={"data": "k"})
    await asyncio.sleep(0.2)

    # Verify output
    response = await client.get(f"/sessions/{session_id}/output")
    assert len(response.json()["output"]) > 0

    # Quit
    await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
    await asyncio.sleep(0.5)

    await client.delete(f"/sessions/{session_id}")
```

**4. File/Content Manipulation Test** (if applicable)
- Test editing, searching, or processing
- Verify changes are saved
- Check output files

**Example (vim):**
```python
async def test_vim_edit_file(server):
    test_file = "/tmp/vim_test.txt"
    with open(test_file, "w") as f:
        f.write("Hello World\n")

    response = await client.post("/sessions", json={
        "command": ["vim", test_file],
        "rows": 24,
        "cols": 80,
        "env": {"TERM": "xterm-256color"}
    })
    session_id = response.json()["session_id"]

    await asyncio.sleep(0.5)

    # Go to insert mode
    await client.post(f"/sessions/{session_id}/input", json={"data": "i"})
    await asyncio.sleep(0.2)

    # Type text
    await client.post(f"/sessions/{session_id}/input",
                     json={"data": " edited"})
    await asyncio.sleep(0.2)

    # Save and quit
    await client.post(f"/sessions/{session_id}/input",
                     json={"data": "\x1b:wq\n"})
    await asyncio.sleep(0.5)

    # Verify file was edited
    with open(test_file, "r") as f:
        content = f.read()
    assert "Hello World edited" in content

    await client.delete(f"/sessions/{session_id}")
```

**5. Resize Test**
- Test terminal resize (SIGWINCH)
- Verify app adapts to new size

```python
async def test_app_resize(server):
    response = await client.post("/sessions", json={
        "command": ["htop"],
        "rows": 24,
        "cols": 80,
        "env": {"TERM": "xterm-256color"}
    })
    session_id = response.json()["session_id"]

    await asyncio.sleep(1.0)

    # Resize
    response = await client.post(f"/sessions/{session_id}/resize", json={
        "rows": 40,
        "cols": 120
    })
    assert response.status_code == 200

    await asyncio.sleep(0.5)

    # Should have updates
    response = await client.get(f"/sessions/{session_id}/output")
    assert len(response.json()["output"]) > 0

    # Quit
    await client.post(f"/sessions/{session_id}/input", json={"data": "q"})
    await asyncio.sleep(0.5)

    await client.delete(f"/sessions/{session_id}")
```

**6. Exit/Cleanup Test**
- Test graceful exit
- Verify session cleanup

```python
async def test_app_exit(server):
    response = await client.post("/sessions", json={
        "command": ["vim"],
        "rows": 24,
        "cols": 80,
        "env": {"TERM": "xterm-256color"}
    })
    session_id = response.json()["session_id"]

    await asyncio.sleep(0.5)

    # Exit vim
    await client.post(f"/sessions/{session_id}/input",
                     json={"data": ":q!\n"})
    await asyncio.sleep(0.5)

    # Session might be gone or still cleaning up
    response = await client.get(f"/sessions/{session_id}")
    assert response.status_code in [200, 404]

    # Cleanup
    await client.delete(f"/sessions/{session_id}")
```

### Step 4: Run Tests

```bash
# Run your new tests
uv run pytest tests/test_<app>.py -v

# Run with more detail if failures
uv run pytest tests/test_<app>.py -v -s --tb=long

# Run all tests to ensure no regressions
uv run pytest tests/ -v
```

**Target**: 100% pass rate before proceeding.

### Step 5: Create Report

Create `reports/<app>_report.md` using this template:

```markdown
# <App Name> Terminal Wrapper Testing Report

## Executive Summary

[Summary of test results and success rate]

**Test Results**: ✅ X/X tests passed (100% success rate)

## Test Methodology

### Test Suite Overview

[List of tests with descriptions]

## Test Results

### Test 1: <Name> ✅

**Purpose**: [What this test validates]

**Method**:
```python
[Code snippet]
```

**Result**: **PASSED**

**Key Findings**:
- [Finding 1]
- [Finding 2]

[Repeat for each test]

## Usage Examples

### Example 1: <Use Case>

[Code example]

[Repeat for 4-6 examples]

## Technical Details

### <App> Integration Points

1. **Command Execution**: [Details]
2. **Input/Output**: [Details]
3. **Terminal Features**: [Details]
4. **Special Keys**: [List]

### Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Launch | Xs | [Note] |
| [Operation] | Xs | [Note] |

## Comparison with Other Apps

| Feature | vim | htop | <app> |
|---------|-----|------|-------|
| [Feature] | ✅ | ✅ | ✅ |

## Conclusion

[Summary of support level and readiness]

---

**Report Generated**: 2026-XX-XX
**Test Suite Version**: 1.0
**<App> Version**: X.Y.Z
**Terminal Wrapper Version**: 1.0
```

### Step 6: Update Main README

Add your app to the applications table in `README.md`:

```markdown
| Application | Status | Report | Tests |
|-------------|--------|--------|-------|
| vim | ✅ Fully Functional | [reports/vim_report.md](reports/vim_report.md) | [tests/test_vim.py](tests/test_vim.py) |
| htop | ✅ Fully Functional | [reports/htop_report.md](reports/htop_report.md) | [tests/test_htop.py](tests/test_htop.py) |
| <your-app> | ✅ Fully Functional | [reports/<app>_report.md](reports/<app>_report.md) | [tests/test_<app>.py](tests/test_<app>.py) |
```

### Step 7: Commit Changes

```bash
# Add all files
git add tests/test_<app>.py reports/<app>_report.md README.md

# Commit with descriptive message
git commit -m "Add <app> e2e tests and report

- Created tests/test_<app>.py with X comprehensive tests
- All tests pass (100% success rate)
- Tests cover: [list key test categories]
- Created reports/<app>_report.md with detailed documentation
- Includes usage examples and technical details
- Updated README.md application table"

# Push
git push
```

## Common Patterns and Tips

### ANSI Escape Sequences

**Common sequences to test for:**
```python
# Check if output contains ANSI codes
assert "\x1b[" in output

# Specific sequences
"\x1b[H"           # Cursor home
"\x1b[2J"          # Clear screen
"\x1b[?1049h"      # Alternate screen buffer (enter)
"\x1b[?1049l"      # Alternate screen buffer (exit)
"\x1b[1m"          # Bold
"\x1b[0m"          # Reset
```

### Special Key Codes

```python
# Arrow keys
UP_ARROW = "\x1b[A"
DOWN_ARROW = "\x1b[B"
RIGHT_ARROW = "\x1b[C"
LEFT_ARROW = "\x1b[D"

# Function keys
F1 = "\x1bOP"
F2 = "\x1bOQ"
F3 = "\x1bOR"
F4 = "\x1bOS"

# Other
ESC = "\x1b"
ENTER = "\r" or "\n"
CTRL_C = "\x03"
CTRL_D = "\x04"
TAB = "\t"
```

### Timing Guidelines

```python
# After launching
await asyncio.sleep(1.0)       # Most apps

# After sending input
await asyncio.sleep(0.2)       # Most keys

# After resize
await asyncio.sleep(0.5)       # SIGWINCH processing

# Before cleanup
await asyncio.sleep(0.5)       # Let app exit
```

### Environment Variables

```python
# Standard terminal environment
{
    "TERM": "xterm-256color",
    "COLORTERM": "truecolor"
}

# App-specific (example for vim)
{
    "TERM": "xterm-256color",
    "COLORTERM": "truecolor",
    "VIMRUNTIME": "/usr/share/vim/vim82"
}
```

### Error Handling

```python
# Always cleanup, even on errors
try:
    # Your test logic
    response = await client.post(...)
    session_id = response.json()["session_id"]

    # ... test operations ...

finally:
    # Always cleanup
    await client.delete(f"/sessions/{session_id}")
```

## Examples by Application Type

### Text Editors (vim, nano, emacs)

**Key tests:**
1. Launch and version
2. Open file
3. Edit text
4. Save file
5. Quit without saving
6. Search/replace

### System Monitors (htop, top, iotop)

**Key tests:**
1. Launch and display
2. Navigation (arrow keys)
3. Sort options
4. Filter/search
5. Resize
6. Quit

### File Viewers (less, more, cat)

**Key tests:**
1. View file
2. Navigation
3. Search
4. Follow mode (if applicable)
5. Quit

### Interactive Shells (bash, zsh, python)

**Key tests:**
1. Launch shell
2. Execute command
3. View output
4. Exit shell

### CLI Tools (claude, git, npm)

**Key tests:**
1. Help/version
2. Basic command
3. Interactive mode
4. Streaming output
5. Exit

## Troubleshooting

### Test Fails: "No such file or directory"

**Problem**: App not installed on test system.

**Solution**: Add installation to CI workflow or test locally first.

```yaml
# .github/workflows/ci.yml
- name: Install <app> for integration tests
  run: |
    sudo apt-get update
    sudo apt-get install -y <app>
```

### Test Fails: Output is empty

**Problem**: Not waiting long enough for app to start or render.

**Solution**: Increase sleep delays.

```python
# Before
await asyncio.sleep(0.1)

# After
await asyncio.sleep(1.0)
```

### Test Fails: "Connection refused"

**Problem**: Port conflict with another test.

**Solution**: Use unique port for each test file.

```python
# tests/test_vim.py uses port 8003
# tests/test_htop.py uses port 8005
# tests/test_<newapp>.py should use port 8006
```

### Test Intermittently Fails

**Problem**: Timing-dependent tests.

**Solution**: Use longer delays or poll for expected output.

```python
# Polling approach
for _ in range(10):
    response = await client.get(f"/sessions/{session_id}/output")
    output = response.json()["output"]
    if "expected text" in output:
        break
    await asyncio.sleep(0.5)
else:
    assert False, "Expected output not found"
```

## Checklist

Before submitting your new application tests:

- [ ] Tests created in `tests/test_<app>.py`
- [ ] All tests pass (100%)
- [ ] Report created in `reports/<app>_report.md`
- [ ] README.md updated with app in table
- [ ] At least 5 tests covering key features
- [ ] Examples provided (4-6 usage examples)
- [ ] Technical details documented
- [ ] Committed with descriptive message
- [ ] CI passes (if app is available on Ubuntu)

## Questions?

See existing test files for reference:
- `tests/test_vim.py` - Complex TUI editor
- `tests/test_htop.py` - Real-time system monitor
- `tests/test_claude.py` - AI CLI tool with interactive and print modes

Corresponding reports:
- `reports/vim_report.md`
- `reports/htop_report.md`
- `reports/claude_report.md`

Follow the established patterns and you'll have comprehensive application testing in no time!
