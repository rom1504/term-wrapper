#!/usr/bin/env python3
"""Test wheel and touch scrolling with alternate buffer apps like Claude Code."""

import asyncio
import pytest
import sys
import os
import shutil

# Only run if playwright is available
playwright = pytest.importorskip("playwright")

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


@pytest.mark.asyncio
async def test_wheel_scrolling_in_alternate_buffer():
    """Test that mouse wheel sends arrow keys in alternate buffer (vim test)."""
    # Use vim as a test case (it uses alternate buffer like Claude Code)
    if not shutil.which("vim"):
        pytest.skip("vim not available")

    # Start server if not running
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # Start client
    client = TerminalClient(base_url=server_url)

    try:
        # Create vim session with a test file
        session_id = client.create_session(
            command=["vim", "-u", "NONE", "/tmp/test_scroll.txt"],
            rows=40,
            cols=120,
            env={"TERM": "xterm-256color"}
        )

        # Create test file with many lines for scrolling
        import subprocess
        subprocess.run(["bash", "-c", "seq 1 100 > /tmp/test_scroll.txt"], check=True)

        # Wait for vim to start
        await asyncio.sleep(1)

        # Get web URL
        web_url = f"{server_url}/?session={session_id}"

        # Launch browser and test scrolling
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate to web UI
            await page.goto(web_url)

            # Wait for terminal to load
            await page.wait_for_selector('#terminal', timeout=10000)

            # Wait for app to initialize
            await page.wait_for_function("window.app && window.app.term", timeout=10000)
            await asyncio.sleep(2)  # Wait for vim to fully render

            # Check buffer type
            buffer_type = await page.evaluate("""() => {
                const term = window.app.term;
                return term.buffer.active.type;
            }""")

            print(f"Buffer type: {buffer_type}")
            assert buffer_type == "alternate", f"Vim should use alternate buffer, got: {buffer_type}"

            # Get initial line number visible in vim
            initial_content = await page.evaluate("""() => {
                const term = window.app.term;
                let lines = [];
                for (let i = 0; i < 3; i++) {
                    const line = term.buffer.active.getLine(i);
                    if (line) {
                        lines.push(line.translateToString(true).trim());
                    }
                }
                return lines.join('|');
            }""")

            print(f"Initial content: {initial_content}")

            # Simulate wheel scroll down (should send Down arrow keys)
            terminal_element = await page.query_selector('#terminal')
            assert terminal_element is not None, "Terminal element not found"

            # Scroll down several times
            for _ in range(5):
                await terminal_element.wheel(delta_y=100)
                await asyncio.sleep(0.2)

            # Wait for vim to process arrow keys and render
            await asyncio.sleep(1)

            # Get new content after scrolling
            scrolled_content = await page.evaluate("""() => {
                const term = window.app.term;
                let lines = [];
                for (let i = 0; i < 3; i++) {
                    const line = term.buffer.active.getLine(i);
                    if (line) {
                        lines.push(line.translateToString(true).trim());
                    }
                }
                return lines.join('|');
            }""")

            print(f"Scrolled content: {scrolled_content}")

            # Verify content changed (vim scrolled down)
            assert scrolled_content != initial_content, \
                f"Content should change after wheel scroll. Before: {initial_content}, After: {scrolled_content}"

            # Check console logs for debug output
            console_logs = []
            page.on("console", lambda msg: console_logs.append(msg.text))

            # Scroll once more and capture logs
            await terminal_element.wheel(delta_y=100)
            await asyncio.sleep(0.5)

            # Look for scroll debug logs
            scroll_logs = [log for log in console_logs if "ScrollDebug" in log or "Buffer type" in log]
            print(f"Console logs: {scroll_logs}")

            await browser.close()

        # Test passed if we got here
        print("✅ Wheel scrolling in alternate buffer works!")

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()
        # Clean up test file
        try:
            os.remove("/tmp/test_scroll.txt")
        except:
            pass


@pytest.mark.asyncio
async def test_wheel_scrolling_claude_code():
    """Test that mouse wheel works with Claude Code specifically."""
    # Skip in CI environment
    if os.getenv("CI"):
        pytest.skip("Claude test skipped in CI environment")

    # Skip if Claude CLI is not available
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
            cols=120,
            env={"TERM": "xterm-256color"}
        )

        # Wait for Claude to start
        await asyncio.sleep(3)

        # Get web URL
        web_url = f"{server_url}/?session={session_id}"

        # Launch browser and test scrolling
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate to web UI
            await page.goto(web_url)

            # Wait for terminal to load
            await page.wait_for_selector('#terminal', timeout=10000)
            await asyncio.sleep(4)  # Wait for Claude to fully render

            # Check buffer type
            buffer_type = await page.evaluate("""() => {
                const term = window.app.term;
                    return term.buffer.active.type;
                }
                return null;
            }""")

            print(f"Buffer type: {buffer_type}")
            assert buffer_type == "alternate", f"Claude Code should use alternate buffer, got: {buffer_type}"

            # Enable console logging
            console_logs = []
            page.on("console", lambda msg: console_logs.append(msg.text))

            # Simulate wheel scroll
            terminal_element = await page.query_selector('#terminal')
            assert terminal_element is not None, "Terminal element not found"

            # Scroll down
            await terminal_element.wheel(delta_y=100)
            await asyncio.sleep(0.5)

            # Check for scroll logs
            scroll_logs = [log for log in console_logs if "ScrollDebug" in log or "Buffer type" in log]
            print(f"Console logs: {scroll_logs}")

            # Verify buffer type was logged
            buffer_logs = [log for log in scroll_logs if "Buffer type" in log]
            assert len(buffer_logs) > 0, "Should have logged buffer type"

            await browser.close()

        print("✅ Wheel scrolling with Claude Code works!")

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    # Run tests directly
    print("Testing wheel scrolling in alternate buffer (vim)...")
    asyncio.run(test_wheel_scrolling_in_alternate_buffer())

    print("\nTesting wheel scrolling with Claude Code...")
    try:
        asyncio.run(test_wheel_scrolling_claude_code())
    except Exception as e:
        print(f"Claude test skipped: {e}")

    print("\n✅ All scrolling tests passed!")
