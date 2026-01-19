#!/usr/bin/env python3
"""Debug mobile keyboard input in web terminal.

This script tests keyboard input on mobile viewport to identify why
Enter key might not work.
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
        # Test both mobile and desktop
        devices = [
            {
                'name': 'iPhone 12',
                'viewport': {'width': 390, 'height': 844},
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            },
            {
                'name': 'Desktop',
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': None
            }
        ]

        for device in devices:
            print(f"\n{'='*60}")
            print(f"Testing on: {device['name']}")
            print(f"Viewport: {device['viewport']}")
            print('='*60)

            browser = await p.chromium.launch(headless=True)

            context_options = {'viewport': device['viewport']}
            if device['user_agent']:
                context_options['user_agent'] = device['user_agent']

            context = await browser.new_context(**context_options)
            page = await context.new_page()

            # Navigate
            await page.goto(web_url)
            await page.wait_for_selector('#terminal', timeout=10000)
            await asyncio.sleep(2)

            # Screenshot initial state
            screenshot_name = f"/home/ai/term_wrapper/mobile_debug_{device['name'].replace(' ', '_')}_01_initial.png"
            await page.screenshot(path=screenshot_name, full_page=True)
            print(f"📸 Screenshot: {screenshot_name}")

            # Check if terminal is focused
            is_focused = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                return document.activeElement && document.activeElement.className.includes('xterm');
            }""")
            print(f"Terminal focused: {is_focused}")

            # Type a simple command
            print("\n>>> Typing: 'echo hello'")
            await page.keyboard.type('echo hello', delay=100)
            await asyncio.sleep(0.5)

            screenshot_name = f"/home/ai/term_wrapper/mobile_debug_{device['name'].replace(' ', '_')}_02_typed.png"
            await page.screenshot(path=screenshot_name, full_page=True)
            print(f"📸 Screenshot: {screenshot_name}")

            # Get terminal content before Enter
            content_before = await page.evaluate("""() => {
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
            print(f"\nContent before Enter:\n{content_before}")

            # Press Enter
            print("\n>>> Pressing Enter")
            await page.keyboard.press('Enter')
            await asyncio.sleep(1)

            screenshot_name = f"/home/ai/term_wrapper/mobile_debug_{device['name'].replace(' ', '_')}_03_after_enter.png"
            await page.screenshot(path=screenshot_name, full_page=True)
            print(f"📸 Screenshot: {screenshot_name}")

            # Get terminal content after Enter
            content_after = await page.evaluate("""() => {
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
            print(f"\nContent after Enter:\n{content_after}")

            # Check if "hello" appeared (command executed)
            if 'hello' in content_after and content_before != content_after:
                print("✅ Enter key worked - command executed")
            else:
                print("❌ Enter key did NOT work - command not executed")

            # Check keyboard event listeners
            print("\n=== Checking Event Listeners ===")
            event_info = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                if (!term || !term.element) return null;

                // Check if textarea exists
                const textarea = term.textarea;

                return {
                    has_textarea: !!textarea,
                    textarea_visible: textarea ? getComputedStyle(textarea).opacity !== '0' : false,
                    textarea_position: textarea ? getComputedStyle(textarea).position : null,
                    terminal_has_focus: document.activeElement === textarea,
                };
            }""")
            print(f"Event info: {event_info}")

            # Try sending raw input
            print("\n>>> Testing raw WebSocket input (\\r)")
            await page.evaluate("""() => {
                if (window.app && window.app.ws && window.app.ws.readyState === 1) {
                    window.app.ws.send('\\r');
                }
            }""")
            await asyncio.sleep(0.5)

            screenshot_name = f"/home/ai/term_wrapper/mobile_debug_{device['name'].replace(' ', '_')}_04_raw_enter.png"
            await page.screenshot(path=screenshot_name, full_page=True)
            print(f"📸 Screenshot: {screenshot_name}")

            content_raw = await page.evaluate("""() => {
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
            print(f"\nContent after raw \\r:\n{content_raw}")

            await browser.close()
            print()

    # Cleanup
    print("\n=== Cleanup ===")
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n✅ Mobile keyboard debugging complete!")


if __name__ == "__main__":
    asyncio.run(main())
