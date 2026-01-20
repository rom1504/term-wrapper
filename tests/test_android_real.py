#!/usr/bin/env python3
"""Test touch scrolling on REAL Android emulator via ADB and Chrome."""

import asyncio
import sys
import subprocess
import time
import os

# Set up Android environment
ANDROID_HOME = os.path.expanduser("~/Android/Sdk")
os.environ["ANDROID_HOME"] = ANDROID_HOME
os.environ["PATH"] = f"{ANDROID_HOME}/platform-tools:{ANDROID_HOME}/emulator:{os.environ['PATH']}"

# Only run if playwright is available
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed. Run: pip install playwright")
    sys.exit(1)

from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


def check_adb_devices():
    """Check if any Android devices are connected via ADB."""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        devices = [line.split()[0] for line in lines if line.strip() and 'offline' not in line]
        return devices
    except FileNotFoundError:
        print("ERROR: adb command not found. Please install Android SDK platform-tools.")
        print("Run: ./setup_android_emulator.sh")
        return []
    except Exception as e:
        print(f"ERROR checking ADB devices: {e}")
        return []


def wait_for_emulator(timeout=60):
    """Wait for Android emulator to be ready."""
    print("Waiting for emulator to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = subprocess.run(['adb', 'shell', 'getprop', 'sys.boot_completed'],
                                    capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == '1':
                print("✓ Emulator is ready!")
                return True
        except:
            pass
        time.sleep(2)
    return False


async def test_android_touch_scrolling_bash():
    """Test touch scrolling on real Android device/emulator with bash (normal buffer)."""
    # Check for ADB devices
    devices = check_adb_devices()
    if not devices:
        print("ERROR: No Android devices found via ADB.")
        print("\nTo start the emulator, run:")
        print("  emulator -avd Pixel_5_API_33 -no-window -no-audio &")
        print("\nThen wait for it to boot (30-60 seconds) and run this test again.")
        sys.exit(1)

    print(f"Found Android device(s): {devices}")

    # Wait for emulator to be fully booted
    if not wait_for_emulator():
        print("ERROR: Emulator did not finish booting in time")
        sys.exit(1)

    # Start server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    # Start client
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

        # Connect to Android device via Playwright
        async with async_playwright() as p:
            print("Connecting to Android device via ADB...")
            # Access android through playwright object
            android = p.android if hasattr(p, 'android') else p._android if hasattr(p, '_android') else None

            if android is None:
                print("ERROR: Playwright Android support not available")
                print("Make sure you have playwright installed with Android support")
                sys.exit(1)

            devices_list = await android.devices()

            if not devices_list:
                print("ERROR: Playwright could not find any Android devices")
                print("Make sure Chrome is installed on the emulator")
                sys.exit(1)

            device = devices_list[0]
            print(f"Connected to: {device.model()} (Serial: {device.serial()})")

            # Launch Chrome on the Android device
            print("Launching Chrome...")
            await device.shell('am force-stop com.android.chrome')
            await asyncio.sleep(1)

            context = await device.launchBrowser()
            page = await context.newPage()

            # Navigate to our terminal web UI
            print(f"Navigating to {web_url}...")
            await page.goto(web_url, wait_until='networkidle')
            await asyncio.sleep(3)  # Wait for terminal to initialize

            # Check if page loaded
            print("Checking if terminal loaded...")
            app_loaded = await page.evaluate("typeof window.app !== 'undefined'")
            if not app_loaded:
                print("ERROR: Terminal app did not load")
                screenshot = await page.screenshot()
                with open('/tmp/android_error.png', 'wb') as f:
                    f.write(screenshot)
                print("Screenshot saved to /tmp/android_error.png")
                await context.close()
                sys.exit(1)

            print("✓ Terminal loaded successfully!")

            # Check buffer type
            buffer_type = await page.evaluate("""() => {
                const term = window.app.term;
                return term.buffer.active.type;
            }""")
            print(f"Buffer type: {buffer_type}")

            # Get initial viewport position
            initial_viewport_y = await page.evaluate("""() => {
                return window.app.term.buffer.active.viewportY;
            }""")
            print(f"Initial viewportY: {initial_viewport_y}")

            # Enable console logging
            console_logs = []
            page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

            # Get viewport dimensions
            viewport = await page.evaluate("""() => {
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                };
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
            new_viewport_y = await page.evaluate("""() => {
                return window.app.term.buffer.active.viewportY;
            }""")
            print(f"New viewportY: {new_viewport_y}")

            # Print console logs
            print("\n=== Console Logs ===")
            for log in console_logs[-20:]:  # Last 20 logs
                print(log)

            # Filter touch/scroll logs
            touch_logs = [log for log in console_logs if 'TouchDebug' in log or 'ScrollDebug' in log or 'TEST' in log]
            print("\n=== Touch/Scroll Debug Logs ===")
            for log in touch_logs:
                print(log)

            # Take screenshot
            screenshot = await page.screenshot()
            with open('/tmp/android_test.png', 'wb') as f:
                f.write(screenshot)
            print("\nScreenshot saved to /tmp/android_test.png")

            # Verify scrolling worked
            if new_viewport_y != initial_viewport_y:
                print(f"\n✅ SUCCESS: Touch scrolling worked! Viewport changed from {initial_viewport_y} to {new_viewport_y}")
                result = "PASS"
            else:
                print(f"\n❌ FAILED: Touch scrolling did NOT work. Viewport stayed at {initial_viewport_y}")
                result = "FAIL"

            await context.close()

            # Return result
            return result == "PASS"

    finally:
        # Cleanup
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    print("=== Testing Touch Scrolling on Real Android Emulator ===\n")

    try:
        success = asyncio.run(test_android_touch_scrolling_bash())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
