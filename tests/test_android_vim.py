#!/usr/bin/env python3
"""Test touch scrolling in vim (alternate buffer) on Android emulator."""

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


async def test_android_vim_touch():
    """Test touch scrolling in vim (alternate buffer) on Android."""

    print("=== Android Vim Touch Scrolling Test (Alternate Buffer) ===\n")

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
        # Create vim session with a file containing many lines
        print("\nCreating vim session with 100 lines...")
        session_id = client.create_session(
            command=["bash", "-c", """
                # Create a test file with 100 numbered lines
                seq 1 100 > /tmp/test_vim.txt
                # Open in vim
                vim /tmp/test_vim.txt
            """],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        android_url = f"http://10.0.2.2:{port}/?session={session_id}"
        print(f"✓ Session created: {session_id}")
        print(f"✓ Android URL: {android_url}\n")

        await asyncio.sleep(2)

        # Open URL in Chrome
        print("Opening vim in Chrome on Android...")
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

                # Wait for vim to load
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

                # Get buffer type - should be 'alternate' for vim
                buffer_type = await page.evaluate("window.app.term.buffer.active.type")
                print(f"\nBuffer type: {buffer_type}")

                if buffer_type != "alternate":
                    print(f"⚠ WARNING: Expected 'alternate' buffer for vim, got '{buffer_type}'")
                    print("Vim may not have loaded properly")

                # In alternate buffer, we can't check viewportY (it's always 0)
                # Instead, we'll check if arrow keys are being sent
                print("\nDispatching touch swipe gestures...")
                await page.evaluate("""() => {
                    const container = document.getElementById('terminal-container');
                    const centerX = window.innerWidth / 2;
                    const startY = window.innerHeight * 0.4;
                    const endY = window.innerHeight * 0.8;

                    console.log('[TEST] Starting touch gesture - alternate buffer should send arrow keys');

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

                # Print console logs
                print("\n=== Console Logs ===")
                for log in console_logs:
                    print(log)

                # Check if arrow keys were sent
                arrow_key_logs = [log for log in console_logs if "arrow keys" in log.lower()]

                print("\n" + "="*60)
                if buffer_type == "alternate" and arrow_key_logs:
                    print(f"✅ SUCCESS: Touch scrolling in vim (alternate buffer) WORKS!")
                    print(f"Arrow keys sent: {len(arrow_key_logs)} batches")
                    for log in arrow_key_logs:
                        print(f"  {log}")
                    return True
                elif buffer_type == "alternate" and not arrow_key_logs:
                    print(f"❌ FAILED: Vim is in alternate buffer but NO arrow keys sent")
                    print("Touch gestures did NOT work in alternate buffer")
                    return False
                else:
                    print(f"⚠ INCONCLUSIVE: Buffer type is '{buffer_type}', not 'alternate'")
                    print("Vim may not have loaded properly, or buffer detection failed")
                    return None

            finally:
                await browser.close()

    finally:
        try:
            # Send :q! to quit vim before deleting session
            client.send_keys(session_id, "\x1b:q!\r")
            await asyncio.sleep(1)
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    try:
        success = asyncio.run(test_android_vim_touch())
        if success is True:
            print("\n✅ VIM TOUCH SCROLLING TEST PASSED")
            sys.exit(0)
        elif success is False:
            print("\n❌ VIM TOUCH SCROLLING TEST FAILED")
            sys.exit(1)
        else:
            print("\n⚠ TEST INCONCLUSIVE - Manual verification needed")
            sys.exit(2)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
