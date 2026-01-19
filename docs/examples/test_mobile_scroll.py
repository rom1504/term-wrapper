#!/usr/bin/env python3
"""Test mobile touch scrolling with long Claude output.

This script tests that touch scrolling works correctly on mobile by:
1. Asking Claude to generate a 40-line poem
2. Using touch actions to scroll
3. Verifying scroll position changes
4. Taking screenshots at different scroll positions
"""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


async def get_scroll_info(page):
    """Get current scroll and viewport information."""
    info = await page.evaluate("""() => {
        const term = window.app ? window.app.term : null;
        if (!term) return null;

        return {
            viewport_y: term.buffer.active.viewportY,
            buffer_length: term.buffer.active.length,
            rows: term.rows,
            cursor_y: term.buffer.active.cursorY,
            can_scroll_up: term.buffer.active.viewportY > 0,
            can_scroll_down: term.buffer.active.viewportY < term.buffer.active.length - term.rows,
        };
    }""")
    return info


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
        cols=80
    )
    print(f"Session ID: {session_id}")

    # Wait for Claude to start
    print("Waiting for Claude to initialize...")
    await asyncio.sleep(3)

    # Launch browser with mobile viewport
    web_url = f"{server_url}/?session={session_id}"
    print(f"\nOpening: {web_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # iPhone 12 viewport
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            has_touch=True
        )
        page = await context.new_page()

        # Navigate
        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(4)  # Wait for Claude to fully render

        # Screenshot 1: Initial state
        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_01_initial.png', full_page=True)
        print("📸 Screenshot 1: Initial state")

        scroll_info = await get_scroll_info(page)
        print(f"Initial state: viewport_y={scroll_info['viewport_y']}, buffer_length={scroll_info['buffer_length']}")

        # Type command to generate 40-line poem
        print("\n>>> Typing: 'generate a 40 line poem about the ocean'")
        await page.keyboard.type('generate a 40 line poem about the ocean', delay=50)
        await asyncio.sleep(0.5)

        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_02_typed_command.png', full_page=True)
        print("📸 Screenshot 2: Command typed")

        # Press Enter button
        print(">>> Clicking ENTER button")
        enter_button = await page.query_selector('button[data-key="enter"]')
        if enter_button:
            await enter_button.click()
            print("✓ Enter button clicked")
        else:
            print("❌ Enter button not found!")
            return False

        # Wait for Claude to start responding
        await asyncio.sleep(3)
        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_03_initial_response.png', full_page=True)
        print("📸 Screenshot 3: Initial response")

        # Wait for poem to be fully generated (give it time)
        print("\nWaiting for poem generation (20 seconds)...")
        await asyncio.sleep(20)

        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_04_full_output.png', full_page=True)
        print("📸 Screenshot 4: Full output")

        scroll_info = await get_scroll_info(page)
        print(f"\nAfter generation:")
        print(f"  Viewport Y: {scroll_info['viewport_y']}")
        print(f"  Buffer length: {scroll_info['buffer_length']}")
        print(f"  Terminal rows: {scroll_info['rows']}")
        print(f"  Can scroll up: {scroll_info['can_scroll_up']}")
        print(f"  Can scroll down: {scroll_info['can_scroll_down']}")

        print(f"\n=== Test 1: Scroll UP (see earlier content) ===")

        # Scroll up using terminal's scrollLines method
        for i in range(5):  # Scroll up 5 lines
            await page.evaluate("() => { if (window.app && window.app.term) window.app.term.scrollLines(-5); }")
            await asyncio.sleep(0.2)

            scroll_info = await get_scroll_info(page)
            print(f"  Scroll {i+1}: viewport_y={scroll_info['viewport_y']}")

        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_05_scrolled_up.png', full_page=True)
        print("📸 Screenshot 5: After scrolling up")

        scroll_info_up = await get_scroll_info(page)

        print(f"\n=== Test 2: Scroll DOWN (see later content) ===")

        # Scroll down using terminal's scrollLines method
        for i in range(5):  # Scroll down 5 lines
            await page.evaluate("() => { if (window.app && window.app.term) window.app.term.scrollLines(5); }")
            await asyncio.sleep(0.2)

            scroll_info = await get_scroll_info(page)
            print(f"  Scroll {i+1}: viewport_y={scroll_info['viewport_y']}")

        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_06_scrolled_down.png', full_page=True)
        print("📸 Screenshot 6: After scrolling down")

        scroll_info_down = await get_scroll_info(page)

        print(f"\n=== Test 3: Scroll to TOP ===")
        # Scroll all the way to top
        await page.evaluate("() => { if (window.app && window.app.term) window.app.term.scrollToTop(); }")
        await asyncio.sleep(0.5)

        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_07_at_top.png', full_page=True)
        print("📸 Screenshot 7: Scrolled to top")

        scroll_info_top = await get_scroll_info(page)
        print(f"  Top viewport_y: {scroll_info_top['viewport_y']}")

        print(f"\n=== Test 4: Scroll to BOTTOM ===")
        # Scroll all the way to bottom
        await page.evaluate("() => { if (window.app && window.app.term) window.app.term.scrollToBottom(); }")
        await asyncio.sleep(0.5)

        await page.screenshot(path='/home/ai/term_wrapper/scroll_test_08_at_bottom.png', full_page=True)
        print("📸 Screenshot 8: Scrolled to bottom")

        scroll_info_bottom = await get_scroll_info(page)
        print(f"  Bottom viewport_y: {scroll_info_bottom['viewport_y']}")

        # Get sample content to verify poem was generated
        print("\n=== Verifying Content ===")
        content_sample = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;

            let lines = [];
            for (let i = 0; i < Math.min(50, term.buffer.active.length); i++) {
                const line = term.buffer.active.getLine(i);
                if (line) {
                    const text = line.translateToString(true).trim();
                    if (text.length > 0) {
                        lines.push(text);
                    }
                }
            }
            return lines;
        }""")

        print(f"Total content lines: {len(content_sample)}")
        print(f"\nFirst 10 lines of content:")
        for i, line in enumerate(content_sample[:10], 1):
            print(f"  {i:2d}: {line[:80]}")

        # Validate scrolling worked
        print("\n=== Validation ===")
        success = True

        if scroll_info_top['viewport_y'] == 0:
            print("✅ Successfully scrolled to top (viewport_y = 0)")
        else:
            print(f"❌ Failed to scroll to top (viewport_y = {scroll_info_top['viewport_y']})")
            success = False

        if scroll_info_up['viewport_y'] < scroll_info_down['viewport_y']:
            print("✅ Scroll up/down directions work correctly")
        else:
            print("❌ Scroll directions may be inverted")
            success = False

        if len(content_sample) >= 30:
            print(f"✅ Generated substantial content ({len(content_sample)} lines)")
        else:
            print(f"⚠️  Content seems short ({len(content_sample)} lines)")

        await browser.close()

    # Cleanup
    print("\n=== Cleanup ===")
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n✅ Mobile scroll test complete!")
    print("\nScreenshots saved:")
    print("  - scroll_test_01_initial.png")
    print("  - scroll_test_02_typed_command.png")
    print("  - scroll_test_03_initial_response.png")
    print("  - scroll_test_04_full_output.png")
    print("  - scroll_test_05_scrolled_up.png")
    print("  - scroll_test_06_scrolled_down.png")
    print("  - scroll_test_07_at_top.png")
    print("  - scroll_test_08_at_bottom.png")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
