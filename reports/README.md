# Application Test Reports

This directory contains detailed test reports for various TUI (Text User Interface) applications running in the terminal wrapper.

## Purpose

Each report documents:
- ✅ Whether the application works
- 🔬 How we tested it
- 📝 Usage examples
- ⚙️ Technical details
- 📊 Performance metrics
- 💡 Lessons learned

## Report Structure

Each report should include:

### 1. Executive Summary
- Application name and version
- Test date
- Overall status (✅ works / ⚠️ partial / ❌ broken)
- Confidence level

### 2. Test Methodology
- What we tested
- How we built the tests
- Test cases and results

### 3. Usage Examples
- Code samples showing how to use the wrapper with this app
- Both HTTP and WebSocket examples
- Real-world use cases

### 4. Technical Details
- Escape sequences observed
- Commands tested
- Special considerations

### 5. Lessons Learned
- What worked well
- Challenges encountered
- Best practices

## Reports

| Application | Status | Report | Tests |
|-------------|--------|--------|-------|
| vim | ✅ Fully Functional | [vim_report.md](vim_report.md) | [test_vim.py](../tests/test_vim.py) |
| htop | ✅ Fully Functional | [htop_report.md](htop_report.md) | [test_htop.py](../tests/test_htop.py) |
| Claude CLI | ✅ Fully Functional | [claude_report.md](claude_report.md) | [test_claude.py](../tests/test_claude.py) |

## How to Add a New Report

### Step 1: Create Test File

```bash
# Create test file
touch tests/test_<appname>.py
```

Example structure:
```python
"""Test <app> integration."""

import asyncio
import pytest
import httpx
from multiprocessing import Process
import uvicorn

def run_server():
    uvicorn.run("term_wrapper.api:app", host="127.0.0.1", port=8XXX, log_level="error")

@pytest.fixture(scope="module")
def server():
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(2)
    yield
    proc.terminate()

@pytest.mark.asyncio
async def test_basic_functionality(server):
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8XXX") as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={"command": ["<appname>", "args..."]}
        )
        session_id = response.json()["session_id"]

        # Test functionality
        await client.post(f"/sessions/{session_id}/input", json={"data": "..."})

        # Verify
        response = await client.get(f"/sessions/{session_id}/output")
        output = response.json()["output"]
        assert "expected" in output
```

### Step 2: Run Tests

```bash
# Run tests
uv run pytest tests/test_<appname>.py -v -s

# Check results
# - All pass ✅
# - Some pass ⚠️
# - All fail ❌
```

### Step 3: Write Report

```bash
# Create report
touch reports/<appname>_report.md
```

Use the vim report as a template:
- Copy the structure
- Fill in your findings
- Include code examples
- Document escape sequences
- Note any issues or limitations

### Step 4: Update This README

Add your app to the table above.

## Testing Checklist

For each application, test:

- [ ] Basic launch and quit
- [ ] Input/output functionality
- [ ] Core features (editing, viewing, etc.)
- [ ] Special keys (arrows, ESC, etc.)
- [ ] File I/O (if applicable)
- [ ] Both HTTP and WebSocket APIs
- [ ] Escape sequence handling
- [ ] Performance (response time)
- [ ] Edge cases (empty input, large files, etc.)

## Example Test Patterns

### Pattern 1: Simple Command Test
```python
async def test_simple(server):
    async with httpx.AsyncClient(...) as client:
        resp = await client.post("/sessions", json={"command": ["app"]})
        sid = resp.json()["session_id"]

        # Send input
        await client.post(f"/sessions/{sid}/input", json={"data": "input"})
        await asyncio.sleep(0.2)

        # Check output
        resp = await client.get(f"/sessions/{sid}/output")
        assert "expected" in resp.json()["output"]
```

### Pattern 2: File Operation Test
```python
async def test_file_ops(server):
    # Create test file
    test_file = "/tmp/test.txt"
    with open(test_file, "w") as f:
        f.write("original")

    # Run app with file
    async with httpx.AsyncClient(...) as client:
        resp = await client.post("/sessions", json={"command": ["app", test_file]})
        sid = resp.json()["session_id"]

        # Modify via app
        await client.post(f"/sessions/{sid}/input", json={"data": "modify"})

        # Verify file changed
        with open(test_file, "r") as f:
            assert "modified" in f.read()
```

### Pattern 3: WebSocket Test
```python
async def test_websocket(server):
    # Create session
    async with httpx.AsyncClient(...) as client:
        resp = await client.post("/sessions", json={...})
        sid = resp.json()["session_id"]

    # Connect WebSocket
    ws_url = f"ws://localhost:8XXX/sessions/{sid}/ws"
    async with websockets.connect(ws_url) as ws:
        # Collect output
        received = []
        async with asyncio.timeout(1.0):
            while True:
                msg = await ws.recv()
                if isinstance(msg, bytes):
                    received.append(msg)

        # Send input
        await ws.send(b"command")

        # Verify
        output = b"".join(received).decode()
        assert "expected" in output
```

## Tips for Testing

### 1. Timing Matters
```python
# Give apps time to start
await asyncio.sleep(0.5)

# Give commands time to process
await asyncio.sleep(0.2)

# Wait for output to accumulate
await asyncio.sleep(0.3)
```

### 2. Inspect Raw Output
```python
# Print for debugging
print(f"\nOutput: {repr(output[:200])}")
print(f"Length: {len(output)} bytes")
print(f"Hex: {output[:50].encode().hex()}")
```

### 3. Test Incrementally
1. First: Can it launch?
2. Then: Can it receive input?
3. Then: Can it produce expected output?
4. Then: Can it do its main job?
5. Finally: Edge cases

### 4. Document Everything
- What worked
- What didn't work
- What's unclear
- Workarounds needed
- Performance observations

## Common Issues & Solutions

### Issue: Output is empty
**Solution**: Increase sleep delay after sending input

### Issue: Escape sequences not recognized
**Solution**: Check TERM environment variable
```python
json={"command": ["app"], "env": {"TERM": "xterm-256color"}}
```

### Issue: Application hangs
**Solution**: Send Ctrl+C or Ctrl+D to terminate
```python
await client.post(f"/sessions/{sid}/input", json={"data": "\x03"})  # Ctrl+C
```

### Issue: File not modified
**Solution**: Ensure save command was sent and processed
```python
# Add explicit save step
await client.post(f"/sessions/{sid}/input", json={"data": ":w\n"})
await asyncio.sleep(0.3)  # Wait for save
```

## Future Applications to Test

Suggestions for next reports:

- [ ] **nano** - Simple text editor
- [ ] **tmux** - Terminal multiplexer
- [ ] **less** - File pager
- [ ] **man** - Manual pages
- [ ] **python REPL** - Interactive Python
- [ ] **node REPL** - Interactive Node.js
- [ ] **mc** - Midnight Commander file manager
- [ ] **emacs** - Another text editor
- [ ] **weechat** - IRC client

## Contributing

When adding a report:
1. Run tests and ensure they pass
2. Write clear, detailed documentation
3. Include practical examples
4. Note any limitations or issues
5. Update this README
6. Commit with message: `Add <app> test report`

## Questions?

If you're unsure about:
- How to test an app
- What to include in a report
- Whether something is a bug

Look at `vim_report.md` as the gold standard example!
