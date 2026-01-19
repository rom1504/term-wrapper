#!/usr/bin/env python3
"""Re-run screencast with 1fps screenshots to analyze duplication."""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


async def main():
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    client = TerminalClient(base_url=server_url)

    # Create Claude session
    print("\n=== Creating Claude session ===")
    session_id = client.create_session(
        command=["bash", "-c", "cd /tmp && claude"],
        rows=32,
        cols=80
    )
    print(f"Session ID: {session_id}")

    await asyncio.sleep(3)

    web_url = f"{server_url}/?session={session_id}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Xiaomi 13 specs
        context = await browser.new_context(
            viewport={'width': 414, 'height': 896},
            user_agent='Mozilla/5.0 (Linux; Android 13; 2211133C) AppleWebKit/537.36',
            has_touch=True,
            is_mobile=True
        )
        page = await context.new_page()

        print(f"\n=== Opening browser ===")
        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)

        frame_num = 0

        async def capture_frame(label=""):
            nonlocal frame_num
            await page.screenshot(path=f'analysis_frame_{frame_num:04d}.png')

            # Get visible text
            visible_text = await page.evaluate("""() => {
                const term = window.app ? window.app.term : null;
                if (!term) return "";

                const buffer = term.buffer.active;
                const viewport_y = buffer.viewportY;
                const rows = term.rows;

                let text_lines = [];
                for (let i = 0; i < rows; i++) {
                    const line = buffer.getLine(viewport_y + i);
                    if (line) {
                        text_lines.push(line.translateToString(true).trim());
                    }
                }

                return text_lines.join('\\n');
            }""")

            # Check for "Herding" in visible text
            herding_count = visible_text.count('Herding')

            print(f"Frame {frame_num:04d} @ {label:20s} - 'Herding' visible: {herding_count} times")

            if herding_count > 1:
                print(f"  ⚠️  DUPLICATE DETECTED!")
                # Save visible text
                with open(f'analysis_frame_{frame_num:04d}_text.txt', 'w') as f:
                    f.write(f"=== Frame {frame_num} @ {label} ===\n")
                    f.write(f"'Herding' count: {herding_count}\n\n")
                    f.write(visible_text)

            frame_num += 1

        # Capture initial state
        await capture_frame("0s - initial")
        await asyncio.sleep(1)

        # Type command slowly, capture every second
        print("\n=== Typing command (capturing frames) ===")
        command_text = 'write a detailed 50 line explanation of how terminal emulators work'

        for i, char in enumerate(command_text):
            await page.keyboard.type(char)
            await asyncio.sleep(0.05)

            # Capture every 10 characters
            if i % 10 == 0:
                await capture_frame(f"{i//10}s - typing")

        await capture_frame("typing done")

        # Press Enter
        print("\n=== Pressing Enter ===")
        enter_button = await page.query_selector('[data-key="enter"]')
        if enter_button:
            await enter_button.click()
        await capture_frame("after enter")

        # Capture frames during Claude generation (every 1 second for 30 seconds)
        print("\n=== Waiting for Claude (capturing every 1s) ===")
        for i in range(30):
            await asyncio.sleep(1)
            await capture_frame(f"{i+1}s - generating")

        # Scroll and capture
        print("\n=== Scrolling test ===")

        bounds = await page.evaluate("""() => {
            const container = document.getElementById('terminal-container');
            const rect = container.getBoundingClientRect();
            return {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            };
        }""")

        center_x = bounds['x'] + bounds['width'] / 2

        # Scroll UP (5 swipes)
        for i in range(5):
            start_y = bounds['y'] + bounds['height'] * 0.7
            end_y = bounds['y'] + bounds['height'] * 0.2

            await page.evaluate("""(coords) => {
                const container = document.getElementById('terminal-container');
                const { startX, startY, endX, endY } = coords;

                const touchStart = new Touch({
                    identifier: 0,
                    target: container,
                    clientX: startX,
                    clientY: startY,
                    pageX: startX,
                    pageY: startY
                });

                container.dispatchEvent(new TouchEvent('touchstart', {
                    touches: [touchStart],
                    targetTouches: [touchStart],
                    changedTouches: [touchStart],
                    bubbles: true,
                    cancelable: true
                }));

                const steps = 10;
                for (let i = 1; i <= steps; i++) {
                    const progress = i / steps;
                    const currentY = startY + (endY - startY) * progress;

                    const touchMove = new Touch({
                        identifier: 0,
                        target: container,
                        clientX: startX,
                        clientY: currentY,
                        pageX: startX,
                        pageY: currentY
                    });

                    container.dispatchEvent(new TouchEvent('touchmove', {
                        touches: [touchMove],
                        targetTouches: [touchMove],
                        changedTouches: [touchMove],
                        bubbles: true,
                        cancelable: true
                    }));
                }

                const touchEnd = new Touch({
                    identifier: 0,
                    target: container,
                    clientX: endX,
                    clientY: endY,
                    pageX: endX,
                    pageY: endY
                });

                container.dispatchEvent(new TouchEvent('touchend', {
                    touches: [],
                    targetTouches: [],
                    changedTouches: [touchEnd],
                    bubbles: true,
                    cancelable: true
                }));
            }""", {
                "startX": center_x,
                "startY": start_y,
                "endX": center_x,
                "endY": end_y
            })

            await asyncio.sleep(0.3)
            await capture_frame(f"scroll_up_{i+1}")

        await browser.close()

    # Cleanup
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n" + "="*60)
    print("FRAME ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nExtracted {frame_num} frames")
    print("\nCheck analysis_frame_*_text.txt for frames with duplicate 'Herding'")


if __name__ == "__main__":
    asyncio.run(main())
