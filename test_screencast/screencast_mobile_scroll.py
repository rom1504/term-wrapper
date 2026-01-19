#!/usr/bin/env python3
"""Record screencast of mobile scrolling to analyze repetition issues."""

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

    await asyncio.sleep(3)  # Wait for Claude to initialize

    web_url = f"{server_url}/?session={session_id}"

    async with async_playwright() as p:
        # Launch browser with video recording
        browser = await p.chromium.launch(headless=True)

        # Xiaomi 13 specs: 6.36" 1080x2400, ~414 CSS pixels width
        context = await browser.new_context(
            viewport={'width': 414, 'height': 896},
            user_agent='Mozilla/5.0 (Linux; Android 13; 2211133C) AppleWebKit/537.36',
            has_touch=True,
            is_mobile=True,
            record_video_dir='screencast_output/',
            record_video_size={'width': 414, 'height': 896}
        )
        page = await context.new_page()

        # Enable console logging
        page.on("console", lambda msg: print(f"[Browser] {msg.type}: {msg.text}"))

        print(f"\n=== Opening browser ===")
        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(2)

        print("\n=== Initial state ===")
        await page.screenshot(path='screencast_output/00_initial.png', full_page=True)

        # Get initial scroll position
        scroll_info = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;
            return {
                viewport_y: term.buffer.active.viewportY,
                buffer_length: term.buffer.active.length,
                rows: term.rows
            };
        }""")
        print(f"Initial: viewport_y={scroll_info['viewport_y']}, buffer={scroll_info['buffer_length']}, rows={scroll_info['rows']}")

        # Type command to generate long output
        print("\n=== Typing command ===")
        command_text = 'write a detailed 50 line explanation of how terminal emulators work, include technical details'

        for char in command_text:
            await page.keyboard.type(char)
            await asyncio.sleep(0.05)  # Natural typing speed

        await page.screenshot(path='screencast_output/01_typed_command.png', full_page=True)

        # Click Enter button (mobile)
        print("\n=== Clicking Enter ===")
        enter_button = await page.query_selector('[data-key="enter"]')
        if enter_button:
            await enter_button.click()
            print("✓ Enter button clicked")
        else:
            print("❌ Enter button not found")
            await page.keyboard.press('Enter')

        await page.screenshot(path='screencast_output/02_after_enter.png', full_page=True)

        # Wait for Claude to generate content
        print("\n=== Waiting for Claude response (25 seconds) ===")
        for i in range(5):
            await asyncio.sleep(5)
            scroll_info = await page.evaluate("""() => {
                return {
                    viewport_y: window.app.term.buffer.active.viewportY,
                    buffer_length: window.app.term.buffer.active.length
                };
            }""")
            print(f"  {(i+1)*5}s: viewport_y={scroll_info['viewport_y']}, buffer={scroll_info['buffer_length']}")

        await page.screenshot(path='screencast_output/03_full_response.png', full_page=True)

        # Get terminal container bounds for touch events
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

        print("\n=== SCROLLING TEST (with touch events) ===")

        # Scroll UP to see earlier content (swipe up = finger moves up)
        print("\n1. Scrolling UP (5 swipes) - should show earlier content")
        for i in range(5):
            start_y = bounds['y'] + bounds['height'] * 0.7
            end_y = bounds['y'] + bounds['height'] * 0.2

            # Dispatch touch swipe
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

                // Simulate move events
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

            scroll_info = await page.evaluate("""() => {
                return { viewport_y: window.app.term.buffer.active.viewportY };
            }""")
            print(f"  Swipe {i+1}: viewport_y={scroll_info['viewport_y']}")

        await page.screenshot(path='screencast_output/04_scrolled_up.png', full_page=True)

        # Scroll DOWN to see later content (swipe down = finger moves down)
        print("\n2. Scrolling DOWN (10 swipes) - should show later content")
        for i in range(10):
            start_y = bounds['y'] + bounds['height'] * 0.2
            end_y = bounds['y'] + bounds['height'] * 0.7

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

            scroll_info = await page.evaluate("""() => {
                return { viewport_y: window.app.term.buffer.active.viewportY };
            }""")
            print(f"  Swipe {i+1}: viewport_y={scroll_info['viewport_y']}")

        await page.screenshot(path='screencast_output/05_scrolled_down.png', full_page=True)

        # Scroll back UP again
        print("\n3. Scrolling UP again (5 swipes)")
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

            scroll_info = await page.evaluate("""() => {
                return { viewport_y: window.app.term.buffer.active.viewportY };
            }""")
            print(f"  Swipe {i+1}: viewport_y={scroll_info['viewport_y']}")

        await page.screenshot(path='screencast_output/06_final.png', full_page=True)

        # Extract all visible content for analysis
        print("\n=== Extracting content for analysis ===")
        content_analysis = await page.evaluate("""() => {
            const term = window.app.term;
            const buffer = term.buffer.active;
            const lines = [];

            // Get all lines in buffer
            for (let i = 0; i < buffer.length; i++) {
                const line = buffer.getLine(i);
                if (line) {
                    let text = line.translateToString(true);
                    lines.push({
                        line_num: i,
                        text: text,
                        length: text.length
                    });
                }
            }

            return {
                total_lines: buffer.length,
                viewport_y: buffer.viewportY,
                rows: term.rows,
                lines: lines
            };
        }""")

        print(f"Total buffer lines: {content_analysis['total_lines']}")
        print(f"Viewport position: {content_analysis['viewport_y']}")
        print(f"Terminal rows: {content_analysis['rows']}")

        # Save content to file for analysis
        with open('screencast_output/content_analysis.txt', 'w') as f:
            f.write(f"=== BUFFER CONTENT ANALYSIS ===\n")
            f.write(f"Total lines: {content_analysis['total_lines']}\n")
            f.write(f"Viewport Y: {content_analysis['viewport_y']}\n")
            f.write(f"Rows: {content_analysis['rows']}\n\n")

            f.write("=== ALL LINES ===\n")
            for line_info in content_analysis['lines']:
                f.write(f"L{line_info['line_num']:3d} [{line_info['length']:3d}]: {line_info['text']}\n")

            # Check for duplicated lines
            f.write("\n=== DUPLICATE DETECTION ===\n")
            seen = {}
            duplicates = []
            for line_info in content_analysis['lines']:
                text = line_info['text'].strip()
                if text and len(text) > 10:  # Ignore empty or very short lines
                    if text in seen:
                        duplicates.append({
                            'text': text,
                            'first_line': seen[text],
                            'duplicate_line': line_info['line_num']
                        })
                        f.write(f"DUPLICATE: '{text[:50]}...'\n")
                        f.write(f"  First at line {seen[text]}\n")
                        f.write(f"  Duplicate at line {line_info['line_num']}\n\n")
                    else:
                        seen[text] = line_info['line_num']

            if not duplicates:
                f.write("No duplicates found!\n")

        print(f"\n✓ Content saved to screencast_output/content_analysis.txt")
        if content_analysis['lines']:
            print(f"\nDuplicates found: {len([l for l in content_analysis['lines'] if 'DUPLICATE' in str(l)])}")

        # Close browser (this saves the video)
        await context.close()
        await browser.close()

        print("\n=== Video saved ===")
        print("Video location: screencast_output/")

        # Get video path
        import os
        video_files = [f for f in os.listdir('screencast_output') if f.endswith('.webm')]
        if video_files:
            print(f"Video file: screencast_output/{video_files[0]}")

    # Cleanup
    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n" + "="*60)
    print("SCREENCAST COMPLETE")
    print("="*60)
    print("\nFiles created:")
    print("  - screencast_output/*.webm (video recording)")
    print("  - screencast_output/00-06_*.png (screenshots)")
    print("  - screencast_output/content_analysis.txt (duplicate detection)")
    print("\nNext steps:")
    print("  1. Watch the video to see actual scrolling behavior")
    print("  2. Check content_analysis.txt for duplicate lines")
    print("  3. Review screenshots for visual artifacts")


if __name__ == "__main__":
    asyncio.run(main())
