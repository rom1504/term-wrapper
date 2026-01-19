#!/usr/bin/env python3
"""Debug actual touch events on mobile - what's really happening?"""

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

    # Create bash session with some content
    session_id = client.create_session(
        command=["bash", "-c", "for i in {1..50}; do echo Line $i; done; bash"],
        rows=30,
        cols=80
    )
    print(f"Session ID: {session_id}")

    await asyncio.sleep(2)

    web_url = f"{server_url}/?session={session_id}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Xiaomi 13 specs: 6.36" 1080x2400, ~414 CSS pixels width
        context = await browser.new_context(
            viewport={'width': 414, 'height': 896},
            user_agent='Mozilla/5.0 (Linux; Android 13; 2211133C) AppleWebKit/537.36',
            has_touch=True,
            is_mobile=True
        )
        page = await context.new_page()

        # Enable console logging from browser
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))

        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(2)

        # Inject touch event logging
        await page.evaluate("""() => {
            console.log('=== Injecting touch event debugger ===');

            const termContainer = document.getElementById('terminal-container');
            const terminal = document.getElementById('terminal');

            console.log('Terminal container:', termContainer ? 'found' : 'NOT FOUND');
            console.log('Terminal element:', terminal ? 'found' : 'NOT FOUND');

            if (window.app) {
                console.log('App found, touch handlers:', {
                    handleTouchStart: typeof window.app.handleTouchStart,
                    handleTouchMove: typeof window.app.handleTouchMove,
                    handleTouchEnd: typeof window.app.handleTouchEnd
                });
            }

            // Log all touch events
            ['touchstart', 'touchmove', 'touchend', 'touchcancel'].forEach(eventType => {
                document.addEventListener(eventType, (e) => {
                    console.log(eventType + ':', {
                        target: e.target.id || e.target.className,
                        touches: e.touches.length,
                        clientY: e.touches[0]?.clientY
                    });
                }, { passive: false });
            });
        }""")

        await page.screenshot(path='/home/ai/term_wrapper/touch_debug_01_initial.png', full_page=True)
        print("\n📸 Initial state")

        # Check initial scroll state
        scroll_info = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;
            return {
                viewport_y: term.buffer.active.viewportY,
                buffer_length: term.buffer.active.length,
                rows: term.rows
            };
        }""")
        print(f"Initial scroll: viewport_y={scroll_info['viewport_y']}, buffer={scroll_info['buffer_length']}, rows={scroll_info['rows']}")

        # Get terminal container bounds
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
        print(f"\nTerminal container bounds: {bounds}")

        # Perform REAL touch event using Playwright touchscreen API
        print("\n=== Test 1: Touch swipe UP (show earlier content) ===")

        center_x = bounds['x'] + bounds['width'] / 2
        start_y = bounds['y'] + bounds['height'] * 0.7
        end_y = bounds['y'] + bounds['height'] * 0.3

        print(f"Touch coordinates: ({center_x:.0f}, {start_y:.0f}) -> ({center_x:.0f}, {end_y:.0f})")

        # Swipe up (finger moves up, content scrolls down to show earlier lines)
        await page.touchscreen.tap(center_x, start_y)
        await asyncio.sleep(0.1)

        # This simulates a real swipe gesture
        await page.evaluate("""(coords) => {
            const container = document.getElementById('terminal-container');
            const { startX, startY, endX, endY } = coords;

            // Create touch events
            const touchStart = new Touch({
                identifier: 0,
                target: container,
                clientX: startX,
                clientY: startY,
                pageX: startX,
                pageY: startY
            });

            const touchEnd = new Touch({
                identifier: 0,
                target: container,
                clientX: endX,
                clientY: endY,
                pageX: endX,
                pageY: endY
            });

            // Dispatch touchstart
            container.dispatchEvent(new TouchEvent('touchstart', {
                touches: [touchStart],
                targetTouches: [touchStart],
                changedTouches: [touchStart],
                bubbles: true,
                cancelable: true
            }));

            console.log('Dispatched touchstart');

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

            console.log('Dispatched ' + steps + ' touchmove events');

            // Dispatch touchend
            container.dispatchEvent(new TouchEvent('touchend', {
                touches: [],
                targetTouches: [],
                changedTouches: [touchEnd],
                bubbles: true,
                cancelable: true
            }));

            console.log('Dispatched touchend');
        }""", {
            "startX": center_x,
            "startY": start_y,
            "endX": center_x,
            "endY": end_y
        })

        await asyncio.sleep(0.5)

        await page.screenshot(path='/home/ai/term_wrapper/touch_debug_02_after_swipe.png', full_page=True)
        print("📸 After swipe")

        scroll_info_after = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;
            return {
                viewport_y: term.buffer.active.viewportY,
                buffer_length: term.buffer.active.length
            };
        }""")
        print(f"After swipe: viewport_y={scroll_info_after['viewport_y']}")

        # Check if viewport changed
        if scroll_info_after['viewport_y'] != scroll_info['viewport_y']:
            print(f"✅ SCROLL WORKED! Changed from {scroll_info['viewport_y']} to {scroll_info_after['viewport_y']}")
        else:
            print(f"❌ SCROLL DID NOT WORK! Still at viewport_y={scroll_info_after['viewport_y']}")

            # Debug why it didn't work
            debug_info = await page.evaluate("""() => {
                return {
                    app_exists: !!window.app,
                    term_exists: !!(window.app && window.app.term),
                    handlers: window.app ? {
                        touchStartY: window.app.touchStartY,
                        lastTouchY: window.app.lastTouchY,
                        isScrolling: window.app.isScrolling,
                        scrollVelocity: window.app.scrollVelocity
                    } : null
                };
            }""")
            print(f"\nDebug info: {debug_info}")

        await browser.close()

    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()

    print("\n" + "="*60)
    print("TESTING STRATEGY ANALYSIS:")
    print("="*60)
    print("1. Using Playwright touchscreen with has_touch=True")
    print("2. Creating actual TouchEvent objects with proper coordinates")
    print("3. Dispatching to terminal-container element")
    print("4. Checking if viewport_y changes")
    print("5. Logging all events to see what fires")
    print("\nCheck browser console logs above for event firing details")


if __name__ == "__main__":
    asyncio.run(main())
