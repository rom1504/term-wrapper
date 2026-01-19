#!/usr/bin/env python3
"""Debug Claude Code vertical alignment by interacting with it."""

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

    # Create Claude session
    print("Creating Claude session...")
    session_id = client.create_session(
        command=["bash", "-c", "cd /tmp && claude"],
        rows=40,
        cols=120
    )
    print(f"Session ID: {session_id}")

    # Wait for Claude to start
    print("Waiting for Claude to start...")
    await asyncio.sleep(3)

    # Get web URL
    web_url = f"{server_url}/?session={session_id}"
    print(f"Opening: {web_url}")

    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

        # Navigate
        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(4)  # Wait for Claude to fully render

        # Screenshot 1: Initial state
        await page.screenshot(path='/home/ai/term_wrapper/debug_01_initial.png', full_page=True)
        print("📸 Screenshot 1: Initial state")

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
        print(f"\n=== Terminal State ===")
        print(f"Dimensions: {dims['rows']}x{dims['cols']}")
        print(f"Viewport: {dims['viewport_width']}x{dims['viewport_height']}px")
        print(f"Buffer length: {dims['buffer_length']}")
        print(f"Cursor: ({dims['cursor_x']}, {dims['cursor_y']})")

        # Type a simple question
        print("\n>>> Typing: 'create hello.py'")
        await page.keyboard.type('create hello.py', delay=100)
        await asyncio.sleep(0.5)

        # Screenshot 2: After typing
        await page.screenshot(path='/home/ai/term_wrapper/debug_02_after_typing.png', full_page=True)
        print("📸 Screenshot 2: After typing")

        # Press Enter
        print(">>> Pressing Enter")
        await page.keyboard.press('Enter')
        await asyncio.sleep(2)  # Wait for response

        # Screenshot 3: After enter
        await page.screenshot(path='/home/ai/term_wrapper/debug_03_after_enter.png', full_page=True)
        print("📸 Screenshot 3: After pressing Enter")

        # Wait a bit more for Claude to respond
        await asyncio.sleep(3)

        # Screenshot 4: After response
        await page.screenshot(path='/home/ai/term_wrapper/debug_04_response.png', full_page=True)
        print("📸 Screenshot 4: After response")

        # Get final state
        final_state = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (term) {
                // Get visible content
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

        print(f"\n=== Final State ===")
        print(f"Cursor: ({final_state['cursor_x']}, {final_state['cursor_y']})")
        print(f"Buffer length: {final_state['buffer_length']}")
        print(f"Viewport Y: {final_state['viewport_y']}")
        print(f"\n=== Terminal Content (first 50 lines) ===")
        print(final_state['content'][:2000])  # First 2000 chars

        # Check for approval UI if it appeared
        if 'esc to cancel' in final_state['content'].lower() or 'enter to confirm' in final_state['content'].lower():
            print("\n>>> Found approval UI, pressing Enter to approve")
            await page.keyboard.press('Enter')
            await asyncio.sleep(2)

            # Screenshot 5: After approval
            await page.screenshot(path='/home/ai/term_wrapper/debug_05_after_approval.png', full_page=True)
            print("📸 Screenshot 5: After approval")

        # Final screenshot with longer content
        await asyncio.sleep(2)
        await page.screenshot(path='/home/ai/term_wrapper/debug_06_final.png', full_page=True)
        print("📸 Screenshot 6: Final state")

        await browser.close()

    # Cleanup
    print("\nCleaning up...")
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n✅ Done! Check screenshots in /home/ai/term_wrapper/")
    print("   - debug_01_initial.png")
    print("   - debug_02_after_typing.png")
    print("   - debug_03_after_enter.png")
    print("   - debug_04_response.png")
    print("   - debug_05_after_approval.png (if approval UI appeared)")
    print("   - debug_06_final.png")

if __name__ == "__main__":
    asyncio.run(main())
