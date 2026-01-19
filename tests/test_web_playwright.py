#!/usr/bin/env python3
"""Test web terminal alignment with Playwright."""

import asyncio
import pytest
import sys
import os

# Only run if playwright is available
playwright = pytest.importorskip("playwright")

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


@pytest.mark.asyncio
async def test_web_terminal_dimensions_sync():
    """Test that web terminal dimensions sync with backend session."""
    # Start server if not running
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # Start client
    client = TerminalClient(base_url=server_url)

    try:
        # Create session with 120 cols (use sleep to keep it alive)
        session_id = client.create_session(
            command=["bash", "-c", "echo 'Test alignment' && sleep 10"],
            rows=40,
            cols=120
        )

        # Wait for command to start
        await asyncio.sleep(0.5)

        # Get web URL
        web_url = f"{server_url}/?session={session_id}"

        # Launch browser and check dimensions
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate to web UI
            await page.goto(web_url)

            # Wait for terminal to load
            await page.wait_for_selector('#terminal', timeout=10000)
            await asyncio.sleep(1)

            # Get frontend terminal dimensions
            dims = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                if (term) {
                    return {
                        rows: term.rows,
                        cols: term.cols,
                    };
                }
                return null;
            }""")

            await browser.close()

        # Get backend session info
        session_info = client.get_session_info(session_id)

        # Verify dimensions
        assert dims is not None, "Could not get frontend terminal dimensions"
        assert dims['cols'] <= 120, f"Frontend cols {dims['cols']} should be capped at 120"

        # After WebSocket connection, backend should match frontend
        # Give it a moment for the resize to propagate
        await asyncio.sleep(0.5)
        session_info = client.get_session_info(session_id)

        assert session_info['cols'] == dims['cols'], \
            f"Backend cols {session_info['cols']} should match frontend {dims['cols']}"
        assert session_info['rows'] == dims['rows'], \
            f"Backend rows {session_info['rows']} should match frontend {dims['rows']}"

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


@pytest.mark.asyncio
async def test_web_terminal_htop_rendering():
    """Test that htop renders properly in web terminal."""
    # Start server if not running
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # Start client
    client = TerminalClient(base_url=server_url)

    try:
        # Create htop session
        session_id = client.create_session(
            command=["htop"],
            rows=40,
            cols=120,
            env={"TERM": "xterm-256color"}
        )

        # Wait for htop to start and render
        await asyncio.sleep(2)

        # Get web URL
        web_url = f"{server_url}/?session={session_id}"

        # Launch browser and check rendering
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate to web UI
            await page.goto(web_url)

            # Wait for terminal to load
            await page.wait_for_selector('#terminal', timeout=10000)
            await asyncio.sleep(2)  # Wait for htop to render

            # Get terminal dimensions
            dims = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                if (term) {
                    return {
                        rows: term.rows,
                        cols: term.cols,
                    };
                }
                return null;
            }""")

            # Take screenshot for visual inspection (saved in test artifacts)
            screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "test_screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, "web_terminal_htop.png")
            await page.screenshot(path=screenshot_path, full_page=True)

            # Get text content to verify rendering
            text_content = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                if (term) {
                    // Get visible buffer
                    let lines = [];
                    for (let i = 0; i < Math.min(20, term.buffer.active.length); i++) {
                        const line = term.buffer.active.getLine(i);
                        if (line) {
                            lines.push(line.translateToString(true));
                        }
                    }
                    return lines.join('\\n');
                }
                return null;
            }""")

            await browser.close()

        # Get backend session info
        session_info = client.get_session_info(session_id)

        # Verify dimensions match
        assert dims is not None, "Could not get frontend terminal dimensions"
        assert dims['cols'] == session_info['cols'], \
            f"Frontend cols {dims['cols']} != backend cols {session_info['cols']}"
        assert dims['cols'] <= 120, f"Terminal should be capped at 120 cols, got {dims['cols']}"

        # Verify htop rendered something (htop shows CPU, Memory, etc.)
        assert text_content is not None, "Could not get terminal text content"
        # htop typically shows CPU, Mem, or PID in its interface
        htop_indicators = ["CPU", "Mem", "PID", "htop"]
        has_htop_content = any(indicator in text_content for indicator in htop_indicators)
        assert has_htop_content, \
            f"htop UI should be visible in terminal output. Got: {text_content[:500]}"

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


@pytest.mark.asyncio
async def test_web_terminal_claude_rendering():
    """Test that Claude Code renders properly in web terminal."""
    # Skip in CI environment (Claude CLI shouldn't run in CI)
    import os
    if os.getenv("CI"):
        pytest.skip("Claude test skipped in CI environment")

    # Skip if Claude CLI is not available
    import shutil
    if not shutil.which("claude"):
        pytest.skip("Claude CLI not available")

    # Start server if not running
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # Start client
    client = TerminalClient(base_url=server_url)

    try:
        # Create Claude session
        session_id = client.create_session(
            command=["bash", "-c", "cd /tmp && claude"],
            rows=40,
            cols=120
        )

        # Wait for Claude to start
        await asyncio.sleep(3)

        # Get web URL
        web_url = f"{server_url}/?session={session_id}"

        # Launch browser and check rendering
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate to web UI
            await page.goto(web_url)

            # Wait for terminal to load
            await page.wait_for_selector('#terminal', timeout=10000)
            await asyncio.sleep(4)  # Wait for Claude to render

            # Get terminal dimensions
            dims = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                if (term) {
                    return {
                        rows: term.rows,
                        cols: term.cols,
                    };
                }
                return null;
            }""")

            # Take screenshot for visual inspection (saved in test artifacts)
            screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "test_screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, "web_terminal_claude.png")
            await page.screenshot(path=screenshot_path, full_page=True)

            # Get some text content to verify rendering
            text_content = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                if (term) {
                    // Get visible buffer
                    let lines = [];
                    for (let i = 0; i < Math.min(20, term.buffer.active.length); i++) {
                        const line = term.buffer.active.getLine(i);
                        if (line) {
                            lines.push(line.translateToString(true));
                        }
                    }
                    return lines.join('\\n');
                }
                return null;
            }""")

            await browser.close()

        # Get backend session info
        session_info = client.get_session_info(session_id)

        # Verify dimensions match
        assert dims is not None, "Could not get frontend terminal dimensions"
        assert dims['cols'] == session_info['cols'], \
            f"Frontend cols {dims['cols']} != backend cols {session_info['cols']}"
        assert dims['cols'] <= 120, f"Terminal should be capped at 120 cols, got {dims['cols']}"

        # Verify Claude rendered something
        assert text_content is not None, "Could not get terminal text content"
        assert "Claude" in text_content or "Welcome" in text_content, \
            "Claude UI should be visible in terminal output"

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_web_terminal_dimensions_sync())
    print("✅ test_web_terminal_dimensions_sync passed")

    asyncio.run(test_web_terminal_claude_rendering())
    print("✅ test_web_terminal_claude_rendering passed")
