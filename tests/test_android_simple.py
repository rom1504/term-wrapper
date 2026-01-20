#!/usr/bin/env python3
"""Simple Android touch test - assumes Chrome is already set up."""

import asyncio
import sys
import subprocess
import os

ANDROID_HOME = os.path.expanduser("~/Android/Sdk")
ADB = f"{ANDROID_HOME}/platform-tools/adb"

from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


def run_adb(cmd):
    """Run adb command."""
    result = subprocess.run([ADB] + cmd, capture_output=True, text=True)
    return result.stdout.strip()


def take_screenshot(filename):
    """Take screenshot from Android."""
    run_adb(["shell", "screencap", "-p", "/sdcard/screenshot.png"])
    run_adb(["pull", "/sdcard/screenshot.png", filename])
    if os.path.exists(filename):
        print(f"✓ Screenshot saved: {filename}")
        return True
    return False


async def test_android_simple():
    """Simple Android touch test without resetting Chrome."""

    print("=== Simple Android Touch Scrolling Test ===\n")

    # Start terminal server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    port = server_url.split(":")[-1].split("/")[0]
    print(f"✓ Server started on port {port}")

    client = TerminalClient(base_url=server_url)

    try:
        # Create session with numbered output
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

        # Open URL in Chrome (don't clear Chrome - use existing setup)
        print("Opening terminal in Chrome...")
        run_adb([
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", android_url,
            "com.android.chrome"
        ])

        print("Waiting for page to load...")
        await asyncio.sleep(8)

        # Take initial screenshot
        print("\n1. Capturing BEFORE state...")
        take_screenshot("/tmp/before_swipe.png")

        # Perform touch swipes (swipe down = scroll up to see earlier content)
        print("\n2. Performing touch swipe gestures...")
        print("   - Swipe 1: Down (scroll up)")
        run_adb(["shell", "input", "swipe", "540", "800", "540", "1600", "500"])
        await asyncio.sleep(1)

        print("   - Swipe 2: Down (scroll up)")
        run_adb(["shell", "input", "swipe", "540", "800", "540", "1600", "500"])
        await asyncio.sleep(1)

        print("   - Swipe 3: Down (scroll up)")
        run_adb(["shell", "input", "swipe", "540", "800", "540", "1600", "500"])
        await asyncio.sleep(1)

        # Take after screenshot
        print("\n3. Capturing AFTER state...")
        take_screenshot("/tmp/after_swipe.png")

        # Swipe back (scroll down)
        print("\n4. Swiping back (scroll down)...")
        run_adb(["shell", "input", "swipe", "540", "1600", "540", "800", "500"])
        await asyncio.sleep(1)

        take_screenshot("/tmp/swipe_back.png")

        print("\n" + "="*60)
        print("TEST COMPLETED - Screenshots saved:")
        print("="*60)
        print("  /tmp/before_swipe.png - Before touch swipes")
        print("  /tmp/after_swipe.png  - After touch swipes")
        print("  /tmp/swipe_back.png   - After swiping back")
        print()
        print("VERIFICATION:")
        print("  Compare before_swipe.png and after_swipe.png")
        print("  If terminal content changed = TOUCH WORKS! ✅")
        print("  If content same = Touch failed ❌")
        print("="*60)

        return True

    finally:
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    try:
        result = asyncio.run(test_android_simple())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
