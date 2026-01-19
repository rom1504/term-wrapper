# Debugging TUI Apps with Playwright

This guide shows how to debug terminal applications using Playwright for visual inspection and automated testing.

## Overview

Playwright is a browser automation tool that can interact with the web terminal UI, take screenshots, and extract terminal state. This is invaluable for debugging layout issues, rendering problems, and verifying TUI application behavior.

## Setup

### Install Playwright

```bash
# Add to dev dependencies (already in pyproject.toml)
uv add --dev playwright

# Install Playwright browsers
uv run playwright install chromium

# Install system dependencies (Linux)
sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1
```

### Basic Structure

A typical debugging script:

```python
#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager

async def main():
    # 1. Start server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # 2. Start client
    client = TerminalClient(base_url=server_url)

    # 3. Create session
    session_id = client.create_session(
        command=["bash", "-c", "cd /tmp && your-tui-app"],
        rows=40,
        cols=120
    )

    # 4. Wait for app to start
    await asyncio.sleep(3)

    # 5. Launch browser
    web_url = f"{server_url}/?session={session_id}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)

        # Your debugging code here...

        await browser.close()

    # Cleanup
    client.delete_session(session_id)
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Debugging Patterns

### 1. Taking Screenshots

Screenshots are the most useful debugging tool for visual issues:

```python
# Take screenshot at specific point
await page.screenshot(path='screenshot_01.png', full_page=True)

# Take multiple screenshots to show progression
await page.screenshot(path='before_input.png', full_page=True)
await page.keyboard.type('some text')
await page.screenshot(path='after_input.png', full_page=True)
```

### 2. Extracting Terminal State

Get terminal dimensions, cursor position, and buffer info:

```python
state = await page.evaluate("""() => {
    const term = window.app ? window.app.term : null;
    if (term) {
        return {
            rows: term.rows,
            cols: term.cols,
            viewport_height: term.element.offsetHeight,
            viewport_width: term.element.offsetWidth,
            buffer_length: term.buffer.active.length,
            cursor_y: term.buffer.active.cursorY,
            cursor_x: term.buffer.active.cursorX,
            viewport_y: term.buffer.active.viewportY,
        };
    }
    return null;
}""")

print(f"Dimensions: {state['rows']}x{state['cols']}")
print(f"Cursor: ({state['cursor_x']}, {state['cursor_y']})")
print(f"Viewport Y: {state['viewport_y']}")
```

### 3. Reading Terminal Content

Extract text from the terminal buffer:

```python
content = await page.evaluate("""() => {
    const term = window.app ? window.app.term : null;
    if (term) {
        let lines = [];
        // Read first 50 lines
        for (let i = 0; i < Math.min(50, term.buffer.active.length); i++) {
            const line = term.buffer.active.getLine(i);
            if (line) {
                lines.push(line.translateToString(true));
            }
        }
        return lines.join('\\n');
    }
    return null;
}""")

print(content)
```

### 4. Simulating User Input

Type text and press keys:

```python
# Type text with delay
await page.keyboard.type('create hello.py', delay=100)

# Press special keys
await page.keyboard.press('Enter')
await page.keyboard.press('Escape')
await page.keyboard.press('Tab')

# Press multiple keys
await page.keyboard.down('Control')
await page.keyboard.press('c')
await page.keyboard.up('Control')
```

### 5. Waiting for Changes

Wait for specific content or state:

```python
# Wait for specific text to appear
await page.wait_for_function("""() => {
    const term = window.app ? window.app.term : null;
    if (!term) return false;

    let content = '';
    for (let i = 0; i < term.buffer.active.length; i++) {
        const line = term.buffer.active.getLine(i);
        if (line) content += line.translateToString(true);
    }
    return content.includes('Expected Text');
}""", timeout=10000)

# Wait for terminal to be ready
await page.wait_for_selector('#terminal', timeout=10000)
await asyncio.sleep(1)  # Additional time for rendering
```

## Examples

### Comprehensive Claude Rendering Test

See [`docs/examples/test_claude_rendering.py`](examples/test_claude_rendering.py) for a comprehensive test that verifies perfect Claude Code rendering:
- Initial state verification
- Query submission and response handling
- Scrolling behavior testing
- File creation with approval flow
- Duplication detection
- Buffer analysis

This test takes 8 screenshots and validates that:
- No content is duplicated vertically
- Layout remains consistent across interactions
- Scrolling works correctly
- Approval UI appears and functions properly

### Interactive Debugging

See [`docs/examples/debug_claude_vertical.py`](examples/debug_claude_vertical.py) for a simpler interactive debugging example that:

1. Creates a Claude Code session
2. Takes screenshot of initial state
3. Types a command
4. Takes screenshot after typing
5. Presses Enter
6. Takes screenshots at different response stages
7. Extracts and prints terminal state
8. Checks for approval UI and interacts with it

Key features demonstrated:

```python
# Wait for Claude to start
await asyncio.sleep(3)

# Screenshot progression
await page.screenshot(path='debug_01_initial.png', full_page=True)

# Get dimensions
dims = await page.evaluate("""() => {
    const term = window.app ? window.app.term : null;
    if (term) {
        return {
            rows: term.rows,
            cols: term.cols,
            viewport_height: term.element.offsetHeight,
            viewport_width: term.element.offsetWidth,
            buffer_length: term.buffer.active.length,
            cursor_y: term.buffer.active.cursorY,
            cursor_x: term.buffer.active.cursorX,
        };
    }
    return null;
}""")
print(f"Dimensions: {dims['rows']}x{dims['cols']}")

# Type and interact
await page.keyboard.type('create hello.py', delay=100)
await page.keyboard.press('Enter')
await asyncio.sleep(2)

# Check for UI elements
final_state = await page.evaluate("""() => {
    const term = window.app ? window.app.term : null;
    if (term) {
        let lines = [];
        for (let i = 0; i < Math.min(50, term.buffer.active.length); i++) {
            const line = term.buffer.active.getLine(i);
            if (line) {
                lines.push(line.translateToString(true));
            }
        }
        return {
            rows: term.rows,
            cols: term.cols,
            cursor_y: term.buffer.active.cursorY,
            cursor_x: term.buffer.active.cursorX,
            buffer_length: term.buffer.active.length,
            viewport_y: term.buffer.active.viewportY,
            content: lines.join('\\n')
        };
    }
    return null;
}""")

if 'esc to cancel' in final_state['content'].lower():
    print("Found approval UI, pressing Enter")
    await page.keyboard.press('Enter')
```

## Common Issues and Solutions

### Issue: Screenshots are blank

**Solution**: Wait for terminal to fully render:

```python
await page.wait_for_selector('#terminal', timeout=10000)
await asyncio.sleep(1)  # Give it a moment to render
```

### Issue: Content not appearing

**Solution**: Increase wait times for TUI apps that take time to start:

```python
# For Claude Code
await asyncio.sleep(3)

# For other slow apps
await asyncio.sleep(5)
```

### Issue: Dimensions don't match

**Solution**: Check that frontend has capped columns correctly:

```python
dims = await page.evaluate("""() => {
    const term = window.app ? window.app.term : null;
    return term ? { rows: term.rows, cols: term.cols } : null;
}""")

# Should be capped at 120
assert dims['cols'] <= 120
```

### Issue: Can't find window.app

**Solution**: Terminal app may not be initialized yet:

```python
# Wait for app to be available
await page.wait_for_function("window.app && window.app.term", timeout=10000)
```

## Running in CI

The Playwright tests run automatically in CI. **Screenshots are uploaded as GitHub artifacts** so you can visually inspect the rendering:

```yaml
- name: Run Playwright web tests
  run: |
    uv run pytest tests/test_web_playwright.py -v

- name: Upload Playwright screenshots
  if: always()  # Upload even if tests fail
  uses: actions/upload-artifact@v4
  with:
    name: playwright-screenshots
    path: test_screenshots/
    if-no-files-found: ignore
```

**Viewing CI Screenshots:**

1. Go to the GitHub Actions run page
2. Scroll to the bottom to find "Artifacts"
3. Download `playwright-screenshots.zip`
4. Unzip to see screenshots like `web_terminal_htop.png`

This is super useful for:
- Debugging CI-specific rendering issues
- Verifying layout changes across environments
- Visual regression testing

**Example: htop in CI**

The htop test runs in CI and generates a screenshot showing htop rendering in the web terminal. You can download this from any CI run to verify TUI rendering works correctly.

Tests that require Claude CLI are automatically skipped:

```python
import shutil
if not shutil.which("claude"):
    pytest.skip("Claude CLI not available")
```

## Tips

1. **Use full_page=True** for screenshots to capture entire terminal content
2. **Add delays** between actions to let TUI apps render (100-500ms)
3. **Take screenshots liberally** - they're the best debugging tool
4. **Extract state at each step** to understand what changed
5. **Check viewport_y** to see if content is scrolled
6. **Verify dimensions** match expectations (120 cols max)
7. **Use translateToString(true)** to preserve whitespace in content
8. **Test in headless mode** first, then use `headless=False` if you need to see it

## References

- [Playwright Python Documentation](https://playwright.dev/python/)
- [xterm.js API](https://xtermjs.org/docs/api/terminal/)
- Example: [`docs/examples/debug_claude_vertical.py`](examples/debug_claude_vertical.py)
- Tests: [`tests/test_web_playwright.py`](../tests/test_web_playwright.py)
