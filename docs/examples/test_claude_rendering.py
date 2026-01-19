#!/usr/bin/env python3
"""Comprehensive test for Claude Code rendering in web terminal.

This script tests multiple interaction scenarios to verify perfect rendering:
- Initial state
- Typing and navigation
- Approval UI
- Response handling
- Vertical scrolling
"""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


async def check_for_duplication(page):
    """Check if content is duplicated by analyzing buffer."""
    content = await page.evaluate("""() => {
        const term = window.app ? window.app.term : null;
        if (!term) return null;

        let lines = [];
        for (let i = 0; i < Math.min(60, term.buffer.active.length); i++) {
            const line = term.buffer.active.getLine(i);
            if (line) {
                lines.push(line.translateToString(true));
            }
        }
        return lines;
    }""")

    if not content:
        return False

    # Look for duplicate "Tips for getting started" or other markers
    tips_count = sum(1 for line in content if 'Tips for getting started' in line)
    welcome_count = sum(1 for line in content if 'Welcome back' in line)

    return tips_count > 1 or welcome_count > 1


async def get_terminal_state(page, label=""):
    """Get comprehensive terminal state."""
    state = await page.evaluate("""() => {
        const term = window.app ? window.app.term : null;
        if (!term) return null;

        return {
            rows: term.rows,
            cols: term.cols,
            cursor_y: term.buffer.active.cursorY,
            cursor_x: term.buffer.active.cursorX,
            buffer_length: term.buffer.active.length,
            viewport_y: term.buffer.active.viewportY,
            viewport_height: term.element.offsetHeight,
            viewport_width: term.element.offsetWidth,
        };
    }""")

    if state:
        print(f"\n{label}Terminal State:")
        print(f"  Dimensions: {state['rows']}x{state['cols']}")
        print(f"  Cursor: ({state['cursor_x']}, {state['cursor_y']})")
        print(f"  Buffer length: {state['buffer_length']}")
        print(f"  Viewport Y: {state['viewport_y']}")
        print(f"  Viewport size: {state['viewport_width']}x{state['viewport_height']}px")

    return state


async def main():
    # Start server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    # Start client
    client = TerminalClient(base_url=server_url)

    # Create Claude session
    print("\n=== Creating Claude session ===")
    session_id = client.create_session(
        command=["bash", "-c", "cd /tmp && claude"],
        rows=40,
        cols=120
    )
    print(f"Session ID: {session_id}")

    # Wait for Claude to start
    print("Waiting for Claude to initialize...")
    await asyncio.sleep(3)

    # Launch browser
    web_url = f"{server_url}/?session={session_id}"
    print(f"\nOpening: {web_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

        # Navigate
        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(2)  # Wait for rendering

        # Test 1: Initial state
        print("\n=== Test 1: Initial State ===")
        await page.screenshot(path='/home/ai/term_wrapper/test_01_initial.png', full_page=True)
        print("📸 Screenshot: test_01_initial.png")

        state = await get_terminal_state(page, "[Initial] ")
        has_dup = await check_for_duplication(page)
        print(f"✓ Duplication check: {'FAILED - duplicates found!' if has_dup else 'PASSED'}")

        if has_dup:
            print("❌ FAIL: Initial state has duplicate content")
            return False

        # Test 2: Type a simple query
        print("\n=== Test 2: Type Simple Query ===")
        await page.keyboard.type('what files are in /tmp?', delay=50)
        await asyncio.sleep(0.5)

        await page.screenshot(path='/home/ai/term_wrapper/test_02_typed_query.png', full_page=True)
        print("📸 Screenshot: test_02_typed_query.png")
        await get_terminal_state(page, "[After typing] ")

        # Test 3: Press Enter and wait for response
        print("\n=== Test 3: Submit Query ===")
        await page.keyboard.press('Enter')
        await asyncio.sleep(3)  # Wait for Claude to respond

        await page.screenshot(path='/home/ai/term_wrapper/test_03_response.png', full_page=True)
        print("📸 Screenshot: test_03_response.png")
        state = await get_terminal_state(page, "[After response] ")

        has_dup = await check_for_duplication(page)
        print(f"✓ Duplication check: {'FAILED - duplicates found!' if has_dup else 'PASSED'}")

        if has_dup:
            print("❌ FAIL: Response has duplicate content")
            return False

        # Test 4: Scroll up to see if layout is consistent
        print("\n=== Test 4: Scroll Behavior ===")
        for _ in range(5):
            await page.keyboard.press('PageUp')
            await asyncio.sleep(0.2)

        await page.screenshot(path='/home/ai/term_wrapper/test_04_scrolled_up.png', full_page=True)
        print("📸 Screenshot: test_04_scrolled_up.png")
        await get_terminal_state(page, "[Scrolled up] ")

        # Scroll back down
        for _ in range(5):
            await page.keyboard.press('PageDown')
            await asyncio.sleep(0.2)

        await page.screenshot(path='/home/ai/term_wrapper/test_05_scrolled_down.png', full_page=True)
        print("📸 Screenshot: test_05_scrolled_down.png")
        await get_terminal_state(page, "[Scrolled down] ")

        # Test 5: Test approval UI (if it appears)
        print("\n=== Test 5: Check for Approval UI ===")
        content = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;

            let lines = [];
            for (let i = 0; i < Math.min(50, term.buffer.active.length); i++) {
                const line = term.buffer.active.getLine(i);
                if (line) {
                    lines.push(line.translateToString(true));
                }
            }
            return lines.join('\\n');
        }""")

        if content and ('do you want to' in content.lower() or 'esc to cancel' in content.lower()):
            print("Found approval UI, testing interaction...")
            await page.keyboard.press('Escape')  # Cancel
            await asyncio.sleep(1)

            await page.screenshot(path='/home/ai/term_wrapper/test_06_after_cancel.png', full_page=True)
            print("📸 Screenshot: test_06_after_cancel.png")

        # Test 6: Type a file creation command to test approval flow
        print("\n=== Test 6: File Creation with Approval ===")
        await page.keyboard.type('create test.py', delay=50)
        await asyncio.sleep(0.5)
        await page.keyboard.press('Enter')
        await asyncio.sleep(3)  # Wait for Claude to respond

        await page.screenshot(path='/home/ai/term_wrapper/test_07_create_file.png', full_page=True)
        print("📸 Screenshot: test_07_create_file.png")
        await get_terminal_state(page, "[Create file] ")

        has_dup = await check_for_duplication(page)
        print(f"✓ Duplication check: {'FAILED - duplicates found!' if has_dup else 'PASSED'}")

        if has_dup:
            print("❌ FAIL: After file creation has duplicate content")
            return False

        # Final screenshot
        await asyncio.sleep(2)
        await page.screenshot(path='/home/ai/term_wrapper/test_08_final.png', full_page=True)
        print("📸 Screenshot: test_08_final.png")

        # Get final buffer analysis
        print("\n=== Final Buffer Analysis ===")
        buffer_info = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;

            let lines = [];
            let emptyLines = 0;
            let contentLines = 0;

            for (let i = 0; i < term.buffer.active.length; i++) {
                const line = term.buffer.active.getLine(i);
                if (line) {
                    const text = line.translateToString(true).trim();
                    if (text.length === 0) {
                        emptyLines++;
                    } else {
                        contentLines++;
                        if (lines.length < 20) {  // First 20 content lines
                            lines.push(text);
                        }
                    }
                }
            }

            return {
                total_lines: term.buffer.active.length,
                content_lines: contentLines,
                empty_lines: emptyLines,
                sample_lines: lines
            };
        }""")

        if buffer_info:
            print(f"  Total buffer lines: {buffer_info['total_lines']}")
            print(f"  Content lines: {buffer_info['content_lines']}")
            print(f"  Empty lines: {buffer_info['empty_lines']}")
            print(f"\n  Sample content (first 20 lines):")
            for i, line in enumerate(buffer_info['sample_lines'][:10], 1):
                print(f"    {i:2d}: {line[:80]}")

        await browser.close()

    # Cleanup
    print("\n=== Cleanup ===")
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n✅ All tests completed successfully!")
    print("\nScreenshots saved:")
    print("  - test_01_initial.png")
    print("  - test_02_typed_query.png")
    print("  - test_03_response.png")
    print("  - test_04_scrolled_up.png")
    print("  - test_05_scrolled_down.png")
    print("  - test_07_create_file.png")
    print("  - test_08_final.png")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
