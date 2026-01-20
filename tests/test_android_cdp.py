#!/usr/bin/env python3
"""Test touch scrolling using Chrome DevTools Protocol on Android emulator."""

import asyncio
import sys
import subprocess
import os

ANDROID_HOME = os.path.expanduser("~/Android/Sdk")
ADB = f"{ANDROID_HOME}/platform-tools/adb"

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)

from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


def run_adb(cmd):
    """Run adb command."""
    result = subprocess.run([ADB] + cmd, capture_output=True, text=True)
    return result.stdout.strip()


async def test_android_touch_via_cdp():
    """Test touch scrolling via Chrome DevTools Protocol."""

    print("=== Android Touch Scrolling Test (via CDP) ===\n")

    # Setup Chrome remote debugging
    print("Setting up Chrome remote debugging...")
    run_adb(["forward", "tcp:9222", "localabstract:chrome_devtools_remote"])
    print("✓ Port forwarding configured")

    # Start terminal server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    port = server_url.split(":")[-1].split("/")[0]
    print(f"✓ Server started on port {port}")

    client = TerminalClient(base_url=server_url)

    try:
        # Create session
        session_id = client.create_session(
            command=["bash", "-c", "seq 1 100; echo '=== END ==='; sleep 180"],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        android_url = f"http://10.0.2.2:{port}/?session={session_id}"
        print(f"✓ Session created: {session_id}")
        print(f"✓ Android URL: {android_url}\n")

        await asyncio.sleep(2)

        # Open URL in Chrome
        print("Opening terminal in Chrome...")
        run_adb([
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", android_url,
            "com.android.chrome"
        ])

        await asyncio.sleep(8)

        # Connect via CDP
        async with async_playwright() as p:
            print("Connecting to Chrome via CDP...")
            try:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                contexts = browser.contexts
                if not contexts:
                    print("ERROR: No browser contexts found")
                    return False

                pages = contexts[0].pages
                if not pages:
                    print("ERROR: No pages found")
                    return False

                page = pages[0]
                print(f"✓ Connected to page: {await page.title()}")

                # Wait for terminal to load
                await asyncio.sleep(3)

                # Check if app loaded
                app_loaded = await page.evaluate("typeof window.app !== 'undefined'")
                if not app_loaded:
                    print("ERROR: Terminal app did not load")
                    return False

                print("✓ Terminal loaded successfully!")

                # Capture console logs
                console_logs = []
                page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

                # Get initial viewport position
                initial_viewport_y = await page.evaluate("window.app.term.buffer.active.viewportY")
                buffer_type = await page.evaluate("window.app.term.buffer.active.type")
                print(f"Buffer type: {buffer_type}")
                print(f"Initial viewportY: {initial_viewport_y}")

                # Dispatch real TouchEvents via JavaScript
                print("\nDispatching touch swipe gestures...")
                await page.evaluate("""() => {
                    const container = document.getElementById('terminal-container');
                    const centerX = window.innerWidth / 2;
                    const startY = window.innerHeight * 0.4;
                    const endY = window.innerHeight * 0.8;

                    console.log('[TEST] Dispatching touchstart');
                    container.dispatchEvent(new TouchEvent('touchstart', {
                        bubbles: true,
                        cancelable: true,
                        touches: [new Touch({
                            identifier: 0,
                            target: container,
                            clientX: centerX,
                            clientY: startY
                        })]
                    }));

                    // Dispatch multiple touchmove events
                    const steps = 10;
                    for (let i = 0; i < steps; i++) {
                        const y = startY + (endY - startY) * (i + 1) / steps;
                        console.log('[TEST] Dispatching touchmove', i, 'y=', y);
                        container.dispatchEvent(new TouchEvent('touchmove', {
                            bubbles: true,
                            cancelable: true,
                            touches: [new Touch({
                                identifier: 0,
                                target: container,
                                clientX: centerX,
                                clientY: y
                            })]
                        }));
                    }

                    console.log('[TEST] Dispatching touchend');
                    container.dispatchEvent(new TouchEvent('touchend', {
                        bubbles: true,
                        cancelable: true,
                        changedTouches: [new Touch({
                            identifier: 0,
                            target: container,
                            clientX: centerX,
                            clientY: endY
                        })]
                    }));

                    console.log('[TEST] Touch gesture completed');
                }""")

                await asyncio.sleep(2)

                # Get new viewport position
                new_viewport_y = await page.evaluate("window.app.term.buffer.active.viewportY")
                print(f"\nNew viewportY: {new_viewport_y}")

                # Print console logs
                print("\n=== Console Logs ===")
                for log in console_logs:
                    print(log)

                # Check result
                print("\n" + "="*60)
                if new_viewport_y != initial_viewport_y:
                    print(f"✅ SUCCESS: Touch scrolling WORKS!")
                    print(f"Viewport changed from {initial_viewport_y} to {new_viewport_y}")
                    return True
                else:
                    print(f"❌ FAILED: Touch scrolling did NOT work")
                    print(f"Viewport stayed at {initial_viewport_y}")
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
    try:
        success = asyncio.run(test_android_touch_via_cdp())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
