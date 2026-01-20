#!/usr/bin/env python3
"""Direct Android emulator test - simpler approach."""

import asyncio
import sys
import subprocess
import time
import os

# Set up Android environment
ANDROID_HOME = os.path.expanduser("~/Android/Sdk")
ADB = f"{ANDROID_HOME}/platform-tools/adb"

from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


def run_adb(cmd):
    """Run adb command and return output."""
    result = subprocess.run([ADB] + cmd, capture_output=True, text=True)
    return result.stdout.strip()


def get_server_ip():
    """Get the server IP that Android emulator can reach."""
    # Android emulator can reach host via 10.0.2.2
    return "10.0.2.2"


async def test_android_direct():
    """Test touch scrolling by having Android Chrome open our terminal."""

    print("=== Direct Android Emulator Test ===\n")

    # Check emulator is running
    devices = run_adb(["devices"])
    if "emulator" not in devices:
        print("ERROR: No emulator found")
        return False

    print("✓ Emulator is running")

    # Start terminal server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"✓ Server started: {server_url}")

    client = TerminalClient(base_url=server_url)

    try:
        # Create bash session
        session_id = client.create_session(
            command=["bash", "-c", "seq 1 100; sleep 120"],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        print(f"✓ Session created: {session_id}")
        await asyncio.sleep(1)

        # Get URL that emulator can reach
        # Android emulator accesses host via 10.0.2.2
        port = server_url.split(":")[-1].split("/")[0]
        android_url = f"http://10.0.2.2:{port}/?session={session_id}"

        print(f"✓ Android URL: {android_url}")

        # Open in Chrome on Android
        print("\nLaunching Chrome on Android emulator...")
        run_adb(["shell", "am", "force-stop", "com.android.chrome"])
        time.sleep(1)

        result = run_adb([
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", android_url,
            "com.android.chrome"
        ])

        print(f"✓ Chrome launched: {result}")

        print("\n" + "="*60)
        print("Chrome should now be open on the Android emulator!")
        print("="*60)
        print("\nNow I will:")
        print("1. Wait for page to load (5 seconds)")
        print("2. Simulate touch events via adb")
        print("3. Check if scrolling worked")
        print("\nPlease wait...")

        await asyncio.sleep(5)

        # Get screen size
        screen_size = run_adb(["shell", "wm", "size"])
        print(f"\nScreen size: {screen_size}")

        # Try to simulate touch events via adb input
        print("\nSimulating touch swipe gestures...")

        # Swipe down (scroll up) - from top to bottom
        # Format: adb shell input swipe x1 y1 x2 y2 duration
        print("Swipe 1: Down (to scroll up)")
        run_adb(["shell", "input", "swipe", "500", "500", "500", "1500", "500"])
        await asyncio.sleep(1)

        print("Swipe 2: Down (to scroll up)")
        run_adb(["shell", "input", "swipe", "500", "500", "500", "1500", "500"])
        await asyncio.sleep(1)

        print("Swipe 3: Up (to scroll down)")
        run_adb(["shell", "input", "swipe", "500", "1500", "500", "500", "500"])
        await asyncio.sleep(1)

        print("\n" + "="*60)
        print("Touch gestures completed!")
        print("="*60)

        # Take screenshot
        print("\nTaking screenshot...")
        run_adb(["shell", "screencap", "-p", "/sdcard/screenshot.png"])
        run_adb(["pull", "/sdcard/screenshot.png", "/tmp/android_screenshot.png"])

        if os.path.exists("/tmp/android_screenshot.png"):
            print("✓ Screenshot saved: /tmp/android_screenshot.png")

        print("\n" + "="*60)
        print("MANUAL VERIFICATION NEEDED:")
        print("="*60)
        print("1. Check the screenshot: /tmp/android_screenshot.png")
        print("2. Look for [TouchDebug] logs in the terminal session")
        print("3. Verify the terminal content changed after swipes")
        print("\nTo check logs from the session:")
        print(f"  Check the browser console on {android_url}")
        print("\n" + "="*60)

        # Try to get logcat output from Chrome
        print("\nChecking Chrome console logs...")
        logcat = run_adb(["logcat", "-d", "-s", "chromium:V", "cr_*:V"])

        if "TouchDebug" in logcat or "ScrollDebug" in logcat:
            print("\n✓ Found touch/scroll debug logs in logcat:")
            for line in logcat.split('\n'):
                if "TouchDebug" in line or "ScrollDebug" in line:
                    print(f"  {line}")
            return True
        else:
            print("\n⚠ No TouchDebug logs found in logcat")
            print("This might mean:")
            print("  1. Touch events aren't being captured")
            print("  2. Console logs aren't being forwarded to logcat")
            print("  3. Need to check browser console directly")

        print("\nTest completed. Please verify manually using the screenshot.")
        return None  # Manual verification needed

    finally:
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    try:
        result = asyncio.run(test_android_direct())
        if result is True:
            print("\n✅ TEST PASSED")
            sys.exit(0)
        elif result is False:
            print("\n❌ TEST FAILED")
            sys.exit(1)
        else:
            print("\n⚠ MANUAL VERIFICATION NEEDED")
            sys.exit(2)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
