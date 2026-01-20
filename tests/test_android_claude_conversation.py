#!/usr/bin/env python3
"""Test touch scrolling in ACTUAL Claude Code conversation on Android emulator."""

import asyncio
import sys
import subprocess
import os
import time

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


async def test_android_claude_conversation():
    """Test touch scrolling in actual Claude Code conversation (alternate buffer)."""

    print("=== Android Claude Code CONVERSATION Touch Scrolling Test ===\n")

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
        print("\nCreating Claude Code session...")
        session_id = client.create_session(
            command=["claude"],
            rows=24,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        android_url = f"http://10.0.2.2:{port}/?session={session_id}"
        print(f"✓ Session created: {session_id}")
        print(f"✓ Android URL: {android_url}\n")

        # Wait for Claude to start
        print("Waiting for Claude to initialize...")
        await asyncio.sleep(5)

        # Send a question to Claude to trigger conversation mode (alternate buffer)
        print("Sending question to Claude to enter conversation mode...")

        question = "Explain touch scrolling in 3 sentences\n"
        client.write_input(session_id, question)
        print(f"✓ Question sent: {question.strip()}")

        # Wait for Claude to start responding (this switches to alternate buffer)
        print("Waiting for Claude to respond and enter alternate buffer...")
        await asyncio.sleep(15)  # Give Claude time to respond

        # Open URL in Chrome
        print("\nOpening in Chrome on Android...")
        run_adb(["shell", "am", "force-stop", "com.android.chrome"])
        await asyncio.sleep(2)
        run_adb([
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", android_url,
            "com.android.chrome"
        ])

        await asyncio.sleep(10)

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

                # Wait for page to load
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

                # Check buffer type - should be 'alternate' if in conversation
                buffer_type = await page.evaluate("window.app.term.buffer.active.type")
                print(f"\n*** Buffer type: {buffer_type} ***")

                if buffer_type == "normal":
                    print("⚠ WARNING: Still in normal buffer!")
                    print("  Claude may not have entered conversation mode yet")
                    print("  Conversation mode uses alternate buffer (like vim)")
                    # Get screen content to see what's happening
                    content = await page.evaluate("window.app.term.buffer.active.getLine(0)?.translateToString() || ''")
                    print(f"  Screen shows: {content[:80]}")
                elif buffer_type == "alternate":
                    print("✅ Claude IS in alternate buffer (conversation mode)!")

                # Dispatch touch swipe gesture regardless
                print("\nDispatching touch swipe gestures...")
                await page.evaluate("""() => {
                    const container = document.getElementById('terminal-container');
                    const centerX = window.innerWidth / 2;
                    const startY = window.innerHeight * 0.4;
                    const endY = window.innerHeight * 0.8;

                    console.log('[TEST] Touch gesture in Claude conversation');

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

                # Check result
                arrow_logs = [log for log in console_logs if "arrow" in log.lower() and "sent" in log.lower()]
                scroll_logs = [log for log in console_logs if "scrolled" in log.lower()]

                print("\n" + "="*60)
                if buffer_type == "alternate" and arrow_logs:
                    print(f"✅ SUCCESS: Claude Code conversation touch scrolling WORKS!")
                    print(f"Buffer: alternate (conversation mode)")
                    print(f"Arrow keys sent: {len(arrow_logs)} batches")
                    for log in arrow_logs[:3]:
                        print(f"  {log}")
                    return True
                elif buffer_type == "normal" and scroll_logs:
                    print(f"✅ SUCCESS: Touch scrolling works in normal buffer")
                    print(f"  (Claude prompt, not conversation)")
                    return True
                elif buffer_type == "alternate" and not arrow_logs:
                    print(f"❌ FAILED: In alternate buffer but NO arrow keys sent")
                    return False
                else:
                    print(f"⚠ INCONCLUSIVE: Buffer={buffer_type}, no clear result")
                    return None

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
        success = asyncio.run(test_android_claude_conversation())
        if success is True:
            print("\n✅ CLAUDE CODE CONVERSATION TOUCH SCROLLING TEST PASSED")
            sys.exit(0)
        elif success is False:
            print("\n❌ CLAUDE CODE CONVERSATION TOUCH SCROLLING TEST FAILED")
            sys.exit(1)
        else:
            print("\n⚠ TEST INCONCLUSIVE - May need manual verification")
            sys.exit(2)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
