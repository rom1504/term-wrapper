#!/usr/bin/env python3
"""Test mobile Enter button functionality.

This script tests that the mobile Enter button works correctly.
"""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


async def main():
    # Start server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    # Start client
    client = TerminalClient(base_url=server_url)

    # Create bash session
    print("\n=== Creating bash session ===")
    session_id = client.create_session(
        command=["bash"],
        rows=40,
        cols=80
    )
    print(f"Session ID: {session_id}")

    # Wait for bash to start
    await asyncio.sleep(1)

    # Launch browser with mobile viewport
    web_url = f"{server_url}/?session={session_id}"
    print(f"\nOpening: {web_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Mobile viewport
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        page = await context.new_page()

        # Navigate
        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(2)

        # Screenshot initial state
        await page.screenshot(path='/home/ai/term_wrapper/mobile_enter_01_initial.png', full_page=True)
        print("📸 Screenshot: mobile_enter_01_initial.png")

        # Type a command using keyboard
        print("\n>>> Typing: 'echo hello world'")
        await page.keyboard.type('echo hello world', delay=100)
        await asyncio.sleep(0.5)

        await page.screenshot(path='/home/ai/term_wrapper/mobile_enter_02_typed.png', full_page=True)
        print("📸 Screenshot: mobile_enter_02_typed.png")

        # Get content before Enter
        content_before = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;

            let lines = [];
            for (let i = Math.max(0, term.buffer.active.length - 3); i < term.buffer.active.length; i++) {
                const line = term.buffer.active.getLine(i);
                if (line) {
                    lines.push(line.translateToString(true));
                }
            }
            return lines.join('\\n');
        }""")
        print(f"\nContent before clicking Enter:\n{content_before}")

        # Check if Enter button exists
        enter_button = await page.query_selector('button[data-key="enter"]')
        if not enter_button:
            print("❌ ERROR: Enter button not found in mobile controls!")
            return False

        print("\n✓ Enter button found")

        # Click the Enter button
        print(">>> Clicking mobile Enter button")
        await enter_button.click()
        await asyncio.sleep(1)

        await page.screenshot(path='/home/ai/term_wrapper/mobile_enter_03_after_click.png', full_page=True)
        print("📸 Screenshot: mobile_enter_03_after_click.png")

        # Get content after Enter
        content_after = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;

            let lines = [];
            for (let i = Math.max(0, term.buffer.active.length - 3); i < term.buffer.active.length; i++) {
                const line = term.buffer.active.getLine(i);
                if (line) {
                    lines.push(line.translateToString(true));
                }
            }
            return lines.join('\\n');
        }""")
        print(f"\nContent after clicking Enter:\n{content_after}")

        # Check if command executed
        if 'hello world' in content_after and content_before != content_after:
            print("\n✅ SUCCESS: Enter button works - command executed!")
            print("   Output contains 'hello world'")
            success = True
        else:
            print("\n❌ FAIL: Enter button did not work - command not executed")
            success = False

        # Test 2: Type and execute another command
        print("\n=== Test 2: Second command ===")
        await page.keyboard.type('pwd', delay=100)
        await asyncio.sleep(0.3)
        await enter_button.click()
        await asyncio.sleep(1)

        await page.screenshot(path='/home/ai/term_wrapper/mobile_enter_04_second_command.png', full_page=True)
        print("📸 Screenshot: mobile_enter_04_second_command.png")

        content_final = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;

            let lines = [];
            for (let i = Math.max(0, term.buffer.active.length - 5); i < term.buffer.active.length; i++) {
                const line = term.buffer.active.getLine(i);
                if (line) {
                    lines.push(line.translateToString(true));
                }
            }
            return lines.join('\\n');
        }""")
        print(f"\nFinal content:\n{content_final}")

        if '/term_wrapper' in content_final or '/tmp' in content_final:
            print("✅ Second command also worked!")
        else:
            print("⚠️  Second command may not have executed")

        await browser.close()

    # Cleanup
    print("\n=== Cleanup ===")
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    if success:
        print("\n✅ Mobile Enter button test PASSED!")
    else:
        print("\n❌ Mobile Enter button test FAILED!")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
