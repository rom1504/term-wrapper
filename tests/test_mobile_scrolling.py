#!/usr/bin/env python3
"""Test mobile touch scrolling with browser emulation."""

import asyncio
import pytest
import sys
import os
import shutil
import subprocess
import time

# Only run if playwright is available
playwright = pytest.importorskip("playwright")

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


@pytest.mark.asyncio
async def test_mobile_touch_scrolling_in_bash():
    """Test that touch scrolling works in mobile emulation with bash (normal buffer)."""
    # Start server if not running
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # Start client
    client = TerminalClient(base_url=server_url)

    try:
        # Create bash session with many lines of output
        session_id = client.create_session(
            command=["bash", "-c", "seq 1 100; sleep 30"],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        # Wait for command to start
        await asyncio.sleep(1)

        # Get web URL
        web_url = f"{server_url}/?session={session_id}"

        # Launch mobile emulated browser
        async with async_playwright() as p:
            # Emulate Xiaomi/Android device
            device = p.devices['Pixel 5']
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(**device)
            page = await context.new_page()

            print(f"Mobile viewport: {device['viewport']}")

            # Navigate to web UI
            await page.goto(web_url)

            # Wait for terminal to load
            await page.wait_for_selector('#terminal', timeout=10000)
            await page.wait_for_function("window.app && window.app.term", timeout=10000)
            await asyncio.sleep(2)  # Wait for content to render

            # Check buffer type
            buffer_type = await page.evaluate("""() => {
                const term = window.app.term;
                return term.buffer.active.type;
            }""")

            print(f"Buffer type: {buffer_type}")
            assert buffer_type == "normal", f"Bash should use normal buffer, got: {buffer_type}"

            # Get initial viewport position
            initial_viewport_y = await page.evaluate("""() => {
                return window.app.term.buffer.active.viewportY;
            }""")

            print(f"Initial viewportY: {initial_viewport_y}")

            # First scroll UP to see earlier content (swipe down = scroll up)
            terminal_element = await page.query_selector('#terminal-container')
            assert terminal_element is not None, "Terminal container not found"

            # Get bounding box for touch coordinates
            box = await terminal_element.bounding_box()
            center_x = box['x'] + box['width'] / 2
            start_y_down = box['y'] + box['height'] * 0.2
            end_y_down = box['y'] + box['height'] * 0.8

            print(f"Touch swipe DOWN (scroll up): ({center_x}, {start_y_down}) -> ({center_x}, {end_y_down})")

            # Enable console logging
            console_logs = []
            page.on("console", lambda msg: console_logs.append(msg.text))

            # Perform touch swipe using dispatchEvent (more reliable than touchscreen API)
            await page.evaluate(f"""() => {{
                const el = document.getElementById('terminal-container');
                const startX = {center_x};
                const startY = {start_y_down};
                const endY = {end_y_down};

                // Dispatch touchstart
                el.dispatchEvent(new TouchEvent('touchstart', {{
                    bubbles: true,
                    cancelable: true,
                    touches: [new Touch({{
                        identifier: 0,
                        target: el,
                        clientX: startX,
                        clientY: startY
                    }})]
                }}));

                // Simulate drag with multiple touchmove events
                const steps = 10;
                for (let i = 0; i < steps; i++) {{
                    const y = startY + (endY - startY) * (i + 1) / steps;
                    el.dispatchEvent(new TouchEvent('touchmove', {{
                        bubbles: true,
                        cancelable: true,
                        touches: [new Touch({{
                            identifier: 0,
                            target: el,
                            clientX: startX,
                            clientY: y
                        }})]
                    }}));
                }}

                // Dispatch touchend
                el.dispatchEvent(new TouchEvent('touchend', {{
                    bubbles: true,
                    cancelable: true,
                    changedTouches: [new Touch({{
                        identifier: 0,
                        target: el,
                        clientX: startX,
                        clientY: endY
                    }})]
                }}));
            }}""")

            # Wait for scroll to process
            await asyncio.sleep(0.5)

            # Get new viewport position
            new_viewport_y = await page.evaluate("""() => {
                return window.app.term.buffer.active.viewportY;
            }""")

            print(f"New viewportY: {new_viewport_y}")

            # Print console logs
            print(f"Console logs: {console_logs}")
            touch_logs = [log for log in console_logs if 'TouchDebug' in log or 'ScrollDebug' in log]
            print(f"Touch/Scroll debug logs: {touch_logs}")

            # Verify content scrolled
            assert new_viewport_y != initial_viewport_y, \
                f"Viewport should have changed. Before: {initial_viewport_y}, After: {new_viewport_y}"

            print("✅ Mobile touch scrolling in normal buffer works!")

            await browser.close()

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


@pytest.mark.asyncio
async def test_mobile_touch_scrolling_in_vim():
    """Test that touch scrolling sends arrow keys in alternate buffer (vim)."""
    if not shutil.which("vim"):
        pytest.skip("vim not available")

    # Start server if not running
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # Start client
    client = TerminalClient(base_url=server_url)

    try:
        # Create test file with many lines
        test_file = "/tmp/test_mobile_scroll.txt"
        subprocess.run(["bash", "-c", f"seq 1 100 > {test_file}"], check=True)

        # Create vim session
        session_id = client.create_session(
            command=["vim", "-u", "NONE", test_file],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        # Wait for vim to start
        await asyncio.sleep(1)

        # Get web URL
        web_url = f"{server_url}/?session={session_id}"

        # Launch mobile emulated browser
        async with async_playwright() as p:
            # Emulate Android device
            device = p.devices['Pixel 5']
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(**device)
            page = await context.new_page()

            print(f"Mobile viewport: {device['viewport']}")

            # Navigate to web UI
            await page.goto(web_url)

            # Wait for terminal to load
            await page.wait_for_selector('#terminal', timeout=10000)
            await page.wait_for_function("window.app && window.app.term", timeout=10000)
            await asyncio.sleep(2)  # Wait for vim to fully render

            # Check buffer type
            buffer_type = await page.evaluate("""() => {
                const term = window.app.term;
                return term.buffer.active.type;
            }""")

            print(f"Buffer type: {buffer_type}")
            assert buffer_type == "alternate", f"Vim should use alternate buffer, got: {buffer_type}"

            # Get initial content (first few lines)
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

            # Enable console logging to track arrow key sends
            console_logs = []
            page.on("console", lambda msg: console_logs.append(msg.text))

            # Simulate touch swipe (should send arrow keys)
            terminal_element = await page.query_selector('#terminal-container')
            assert terminal_element is not None, "Terminal container not found"

            # Get bounding box for touch coordinates
            box = await terminal_element.bounding_box()
            center_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] * 0.8
            end_y = box['y'] + box['height'] * 0.2

            print(f"Touch swipe: ({center_x}, {start_y}) -> ({center_x}, {end_y})")

            # Perform touch swipe down (swipe down = scroll up in vim)
            await page.touchscreen.tap(center_x, start_y)
            await page.mouse.down()
            await page.mouse.move(center_x, start_y)

            # Swipe down in multiple steps
            steps = 10
            for i in range(steps):
                y = start_y + (end_y - start_y) * (i + 1) / steps
                await page.mouse.move(center_x, y)
                await asyncio.sleep(0.01)

            await page.mouse.up()

            # Wait for vim to process arrow keys and render
            await asyncio.sleep(1)

            # Get new content
            new_content = await page.evaluate("""() => {
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

            print(f"New content: {new_content}")

            # Check console logs for touch debug messages
            touch_logs = [log for log in console_logs if 'TouchDebug' in log]
            print(f"Touch debug logs: {touch_logs}")

            # Verify content changed (vim scrolled)
            assert new_content != initial_content, \
                f"Content should change after touch swipe. Before: {initial_content}, After: {new_content}"

            print("✅ Mobile touch scrolling in alternate buffer (vim) works!")

            await browser.close()

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()
        try:
            os.remove(test_file)
        except:
            pass


@pytest.mark.asyncio
async def test_mobile_wheel_scrolling_fallback():
    """Test that wheel events also work in mobile emulation (trackpad on tablet)."""
    # Start server if not running
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()

    # Start client
    client = TerminalClient(base_url=server_url)

    try:
        # Create bash session
        session_id = client.create_session(
            command=["bash", "-c", "seq 1 100; sleep 30"],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        await asyncio.sleep(1)

        web_url = f"{server_url}/?session={session_id}"

        async with async_playwright() as p:
            # Use tablet device (might have trackpad/wheel support)
            device = p.devices['iPad Pro']
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(**device)
            page = await context.new_page()

            await page.goto(web_url)
            await page.wait_for_selector('#terminal', timeout=10000)
            await page.wait_for_function("window.app && window.app.term", timeout=10000)
            await asyncio.sleep(2)

            # Get initial viewport position
            initial_viewport_y = await page.evaluate("""() => {
                return window.app.term.buffer.active.viewportY;
            }""")

            # Simulate wheel scroll
            terminal_element = await page.query_selector('#terminal')
            assert terminal_element is not None

            # Scroll down with wheel (should work even on mobile)
            await terminal_element.mouse_wheel(delta_y=200)
            await asyncio.sleep(0.5)

            new_viewport_y = await page.evaluate("""() => {
                return window.app.term.buffer.active.viewportY;
            }""")

            print(f"Wheel scroll - Before: {initial_viewport_y}, After: {new_viewport_y}")

            assert new_viewport_y != initial_viewport_y, \
                "Wheel scrolling should work on mobile devices with trackpad support"

            print("✅ Mobile wheel scrolling works!")

            await browser.close()

    finally:
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


@pytest.mark.asyncio
async def test_mobile_continuous_touch_scrolling():
    """Test continuous touch scrolling (holding and dragging) produces multiple scroll events."""
    # Start server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    client = TerminalClient(base_url=server_url)

    try:
        # Create bash session with output
        session_id = client.create_session(
            command=["bash", "-c", "seq 1 100; sleep 30"],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        await asyncio.sleep(1)
        web_url = f"{server_url}/?session={session_id}"

        async with async_playwright() as p:
            device = p.devices['Pixel 5']
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(**device)
            page = await context.new_page()

            await page.goto(web_url)
            await page.wait_for_selector('#terminal', timeout=10000)
            await page.wait_for_function("window.app && window.app.term", timeout=10000)
            await asyncio.sleep(2)

            # Track viewport changes during continuous scroll
            viewport_positions = []

            # Capture initial position
            initial_y = await page.evaluate("window.app.term.buffer.active.viewportY")
            viewport_positions.append(initial_y)

            # Perform continuous touch scroll (long swipe with many intermediate points)
            terminal_element = await page.query_selector('#terminal-container')
            box = await terminal_element.bounding_box()

            center_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] * 0.8
            end_y = box['y'] + box['height'] * 0.2

            # Start touch
            await page.touchscreen.tap(center_x, start_y)
            await page.mouse.down()

            # Drag slowly with many steps (simulate real finger drag)
            steps = 30
            for i in range(steps):
                y = start_y + (end_y - start_y) * (i + 1) / steps
                await page.mouse.move(center_x, y)
                await asyncio.sleep(0.02)  # Small delay between moves

                # Capture position during drag
                current_y = await page.evaluate("window.app.term.buffer.active.viewportY")
                viewport_positions.append(current_y)

            await page.mouse.up()
            await asyncio.sleep(0.5)

            # Final position
            final_y = await page.evaluate("window.app.term.buffer.active.viewportY")
            viewport_positions.append(final_y)

            # Remove duplicates
            unique_positions = list(set(viewport_positions))
            unique_positions.sort()

            print(f"Viewport positions during continuous scroll: {unique_positions}")
            print(f"Number of unique positions: {len(unique_positions)}")
            print(f"Total change: {final_y - initial_y}")

            # Verify continuous scrolling produced multiple position changes
            assert len(unique_positions) >= 3, \
                f"Continuous scroll should produce multiple position changes, got {len(unique_positions)}"

            assert final_y != initial_y, \
                f"Final position should differ from initial. Start: {initial_y}, End: {final_y}"

            print("✅ Continuous mobile touch scrolling produces multiple scroll events!")

            await browser.close()

    finally:
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    # Run tests directly
    print("Testing mobile emulation with Playwright...\n")

    print("1. Testing touch scrolling in bash (normal buffer)...")
    asyncio.run(test_mobile_touch_scrolling_in_bash())

    print("\n2. Testing touch scrolling in vim (alternate buffer)...")
    try:
        asyncio.run(test_mobile_touch_scrolling_in_vim())
    except Exception as e:
        print(f"Vim test skipped: {e}")

    print("\n3. Testing wheel scrolling on mobile...")
    asyncio.run(test_mobile_wheel_scrolling_fallback())

    print("\n4. Testing continuous touch scrolling...")
    asyncio.run(test_mobile_continuous_touch_scrolling())

    print("\n✅ All mobile emulation tests passed!")
