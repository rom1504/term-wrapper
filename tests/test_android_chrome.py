#!/usr/bin/env python3
"""Test touch scrolling on Android emulator via Chrome remote debugging."""

import asyncio
import sys
import subprocess
import time
import os

# Set up Android environment
ANDROID_HOME = os.path.expanduser("~/Android/Sdk")
os.environ["ANDROID_HOME"] = ANDROID_HOME
os.environ["PATH"] = f"{ANDROID_HOME}/platform-tools:{ANDROID_HOME}/emulator:{os.environ['PATH']}"

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)

from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


def setup_chrome_debugging():
    """Setup Chrome remote debugging on Android."""
    print("Setting up Chrome remote debugging...")

    # Kill any existing Chrome instances
    subprocess.run(['adb', 'shell', 'am', 'force-stop', 'com.android.chrome'],
                   check=False, capture_output=True)
    time.sleep(1)

    # Forward debugging port
    subprocess.run(['adb', 'forward', 'tcp:9222', 'localabstract:chrome_devtools_remote'],
                   check=True, capture_output=True)

    print("✓ Chrome debugging port forwarded (9222)")


async def test_android_chrome_scrolling():
    """Test touch scrolling via Chrome DevTools Protocol."""
    # Check for ADB devices
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
    lines = result.stdout.strip().split('\n')[1:]
    devices = [line.split()[0] for line in lines if line.strip() and 'offline' not in line]

    if not devices:
        print("ERROR: No Android devices found via ADB")
        return False

    print(f"Found Android device: {devices[0]}")

    # Setup Chrome debugging
    setup_chrome_debugging()

    # Start terminal server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    client = TerminalClient(base_url=server_url)

    try:
        # Create bash session with output
        session_id = client.create_session(
            command=["bash", "-c", "seq 1 100; sleep 60"],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        await asyncio.sleep(1)
        web_url = f"{server_url}/?session={session_id}"
        print(f"Session URL: {web_url}")

        # Launch Chrome on Android
        print("Launching Chrome on Android...")
        subprocess.run([
            'adb', 'shell', 'am', 'start',
            '-a', 'android.intent.action.VIEW',
            '-d', web_url
        ], check=True, capture_output=True)

        await asyncio.sleep(5)  # Wait for Chrome to open

        # Connect Playwright to Chrome via DevTools Protocol
        async with async_playwright() as p:
            print("Connecting to Chrome via CDP...")
            try:
                # Connect to Chrome on Android via forwarded port
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                contexts = browser.contexts
                if not contexts:
                    print("ERROR: No browser contexts found")
                    return False

                # Get the page
                pages = contexts[0].pages
                if not pages:
                    print("ERROR: No pages found")
                    return False

                page = pages[0]
                print(f"✓ Connected to page: {await page.title()}")

                # Wait for terminal to load
                await asyncio.sleep(3)

                # Check if terminal loaded
                app_loaded = await page.evaluate("typeof window.app !== 'undefined'")
                if not app_loaded:
                    print("ERROR: Terminal app did not load")
                    screenshot = await page.screenshot()
                    with open('/tmp/android_chrome_error.png', 'wb') as f:
                        f.write(screenshot)
                    print("Screenshot saved to /tmp/android_chrome_error.png")
                    return False

                print("✓ Terminal loaded successfully!")

                # Get buffer type and initial position
                buffer_type = await page.evaluate("window.app.term.buffer.active.type")
                initial_viewport_y = await page.evaluate("window.app.term.buffer.active.viewportY")
                print(f"Buffer type: {buffer_type}")
                print(f"Initial viewportY: {initial_viewport_y}")

                # Enable console logging
                console_logs = []
                page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

                # Get viewport size
                viewport = await page.evaluate("""() => {
                    return { width: window.innerWidth, height: window.innerHeight };
                }""")
                print(f"Viewport: {viewport['width']}x{viewport['height']}")

                # Perform touch swipe (swipe down = scroll up to see earlier content)
                print("Performing touch swipe gesture...")
                center_x = viewport['width'] / 2
                start_y = viewport['height'] * 0.3
                end_y = viewport['height'] * 0.7

                print(f"Touch swipe: ({center_x}, {start_y}) -> ({center_x}, {end_y})")

                # Dispatch touch events
                await page.evaluate(f"""() => {{
                    const el = document.getElementById('terminal-container');
                    const startX = {center_x};
                    const startY = {start_y};
                    const endY = {end_y};

                    console.log('[TEST] Starting touch gesture');

                    // touchstart
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

                    // Multiple touchmove events
                    const steps = 15;
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

                    // touchend
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

                    console.log('[TEST] Touch gesture completed');
                }}""")

                await asyncio.sleep(1)

                # Get new viewport position
                new_viewport_y = await page.evaluate("window.app.term.buffer.active.viewportY")
                print(f"New viewportY: {new_viewport_y}")

                # Print console logs
                print("\n=== Console Logs ===")
                for log in console_logs[-20:]:
                    print(log)

                # Take screenshot
                screenshot = await page.screenshot()
                with open('/tmp/android_chrome_test.png', 'wb') as f:
                    f.write(screenshot)
                print("\nScreenshot saved to /tmp/android_chrome_test.png")

                # Check result
                if new_viewport_y != initial_viewport_y:
                    print(f"\n✅ SUCCESS: Touch scrolling worked! Viewport changed from {initial_viewport_y} to {new_viewport_y}")
                    return True
                else:
                    print(f"\n❌ FAILED: Touch scrolling did NOT work. Viewport stayed at {initial_viewport_y}")
                    return False

            finally:
                await browser.close()

    finally:
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    print("=== Testing Touch Scrolling on Android Chrome ===\n")

    try:
        success = asyncio.run(test_android_chrome_scrolling())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
