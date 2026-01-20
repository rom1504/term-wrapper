#!/usr/bin/env python3
"""Final Android emulator test with proper Chrome setup and visual verification."""

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


async def test_android_final():
    """Final comprehensive Android test."""

    print("=== Final Android Emulator Touch Scrolling Test ===\n")

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

        # Setup Chrome properly
        print("Step 1: Setting up Chrome...")
        print("-" * 60)

        # Clear Chrome data
        print("  - Clearing Chrome data...")
        run_adb(["shell", "pm", "clear", "com.android.chrome"])
        await asyncio.sleep(2)

        # Start Chrome
        print("  - Starting Chrome...")
        run_adb(["shell", "am", "start", "-n", "com.android.chrome/com.google.android.apps.chrome.Main"])
        await asyncio.sleep(3)

        # Take screenshot of welcome screen
        take_screenshot("/tmp/step1_welcome.png")

        # Accept welcome
        print("  - Accepting welcome screen...")
        run_adb(["shell", "input", "tap", "360", "1435"])
        await asyncio.sleep(2)

        # Skip sync
        print("  - Skipping sync...")
        run_adb(["shell", "input", "tap", "180", "1435"])
        await asyncio.sleep(2)

        print("✓ Chrome setup complete\n")

        # Navigate to terminal
        print("Step 2: Opening terminal in Chrome...")
        print("-" * 60)

        run_adb([
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", android_url,
            "com.android.chrome"
        ])

        print("  - Waiting for page to load...")
        await asyncio.sleep(5)

        take_screenshot("/tmp/step2_terminal_loaded.png")
        print("✓ Terminal should be loaded\n")

        # Perform touch gestures
        print("Step 3: Performing touch swipe gestures...")
        print("-" * 60)

        # Get initial screenshot
        print("  - Taking initial screenshot...")
        take_screenshot("/tmp/step3_before_swipe.png")

        # Swipe down multiple times (scroll up to see earlier content)
        print("  - Swipe 1: Down (scroll up)")
        run_adb(["shell", "input", "swipe", "540", "600", "540", "1800", "500"])
        await asyncio.sleep(1)

        print("  - Swipe 2: Down (scroll up)")
        run_adb(["shell", "input", "swipe", "540", "600", "540", "1800", "500"])
        await asyncio.sleep(1)

        print("  - Swipe 3: Down (scroll up)")
        run_adb(["shell", "input", "swipe", "540", "600", "540", "1800", "500"])
        await asyncio.sleep(1)

        # Take screenshot after swipes
        print("  - Taking after-swipe screenshot...")
        take_screenshot("/tmp/step3_after_swipe.png")

        print("✓ Touch gestures completed\n")

        # Try to swipe back
        print("Step 4: Swiping back (scroll down)...")
        print("-" * 60)

        print("  - Swipe up (scroll down)")
        run_adb(["shell", "input", "swipe", "540", "1800", "540", "600", "500"])
        await asyncio.sleep(1)

        take_screenshot("/tmp/step4_swipe_back.png")
        print("✓ Swipe back completed\n")

        # Final results
        print("=" * 60)
        print("TEST COMPLETED - Screenshots saved:")
        print("=" * 60)
        print("  /tmp/step1_welcome.png       - Chrome welcome screen")
        print("  /tmp/step2_terminal_loaded.png - Terminal loaded in Chrome")
        print("  /tmp/step3_before_swipe.png   - Before touch swipes")
        print("  /tmp/step3_after_swipe.png    - After touch swipes")
        print("  /tmp/step4_swipe_back.png     - After swiping back")
        print("")
        print("VERIFICATION:")
        print("  1. Compare step3_before_swipe.png and step3_after_swipe.png")
        print("  2. The terminal content should be different (scrolled)")
        print("  3. If content changed = TOUCH SCROLLING WORKS! ✅")
        print("  4. If content same = Touch scrolling failed ❌")
        print("=" * 60)

        return True

    finally:
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    try:
        result = asyncio.run(test_android_final())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
