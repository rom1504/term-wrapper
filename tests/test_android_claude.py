#!/usr/bin/env python3
"""Test touch scrolling with Claude Code on Android emulator."""

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


async def test_android_claude_touch():
    """Test touch scrolling in Claude Code on Android."""

    print("=== Android Claude Code Touch Scrolling Test ===\n")

    # Check if claude command exists
    claude_check = subprocess.run(["which", "claude"], capture_output=True)
    if claude_check.returncode != 0:
        print("⚠ WARNING: 'claude' command not found")
        print("Installing Claude Code is recommended but not required for this test")
        print("Testing with a simulated Claude-like environment (alternate buffer + output)")
        use_real_claude = False
    else:
        print("✓ Claude Code found")
        use_real_claude = True

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
        if use_real_claude:
            print("\nCreating Claude Code session...")
            # Start Claude Code interactively
            session_id = client.create_session(
                command=["bash", "-c", """
                    echo "Starting Claude Code..."
                    echo "You can type questions and Claude will respond."
                    echo "This will use alternate buffer like vim."
                    echo ""
                    # Run claude in interactive mode
                    claude
                """],
                rows=24,
                cols=80,
                env={"TERM": "xterm-256color"}
            )
        else:
            print("\nCreating simulated Claude-like session (less command)...")
            # Use 'less' which also uses alternate buffer
            session_id = client.create_session(
                command=["bash", "-c", """
                    # Create a file with Claude-like conversation
                    cat > /tmp/claude_conversation.txt << 'EOF'
Human: Can you help me understand how touch scrolling works in web terminals?

Claude: I'd be happy to explain touch scrolling in web terminals!

Touch scrolling in web-based terminal emulators works by:

1. Capturing touch events (touchstart, touchmove, touchend)
2. Detecting the buffer type (normal vs alternate)
3. Taking different actions based on buffer:
   - Normal buffer: Directly scroll the viewport
   - Alternate buffer: Send arrow key sequences

Let me break this down further...

[Buffer Detection]
The terminal has two main buffer types:
- Normal buffer: Used by shells (bash, zsh) for command output
- Alternate buffer: Used by full-screen apps (vim, less, htop)

[Touch Handling]
When you swipe on a mobile device:
- touchstart: Record initial Y position
- touchmove: Calculate deltaY from last position
- touchend: Reset state

[Normal Buffer Scrolling]
In normal buffer mode:
- deltaY > 0 (swipe down) → scroll up in history
- deltaY < 0 (swipe up) → scroll down to recent

[Alternate Buffer Scrolling]
In alternate buffer mode:
- deltaY > 0 → send arrow UP keys
- deltaY < 0 → send arrow DOWN keys

This allows apps like vim to handle scrolling themselves!EOF
                    # Open in less (alternate buffer like Claude)
                    less /tmp/claude_conversation.txt
                """],
                rows=24,
                cols=80,
                env={"TERM": "xterm-256color"}
            )

        android_url = f"http://10.0.2.2:{port}/?session={session_id}"
        print(f"✓ Session created: {session_id}")
        print(f"✓ Android URL: {android_url}\n")

        await asyncio.sleep(3)

        # Open URL in Chrome
        print("Opening in Chrome on Android...")
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

                # Wait for Claude/less to load
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

                # Get buffer type
                buffer_type = await page.evaluate("window.app.term.buffer.active.type")
                print(f"\nBuffer type: {buffer_type}")

                if buffer_type != "alternate":
                    print(f"⚠ WARNING: Expected 'alternate' buffer, got '{buffer_type}'")
                    print("Claude/less may not have loaded properly")

                # Dispatch touch swipes
                print("\nDispatching touch swipe gestures...")
                await page.evaluate("""() => {
                    const container = document.getElementById('terminal-container');
                    const centerX = window.innerWidth / 2;
                    const startY = window.innerHeight * 0.4;
                    const endY = window.innerHeight * 0.8;

                    console.log('[TEST] Touch gesture - should send arrow keys in alternate buffer');

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

                # Check if arrow keys were sent
                arrow_key_logs = [log for log in console_logs if "arrow" in log.lower() and "sent" in log.lower()]

                print("\n" + "="*60)
                if use_real_claude:
                    print("Testing with: REAL Claude Code")
                else:
                    print("Testing with: less (Claude-like alternate buffer)")

                if buffer_type == "alternate" and arrow_key_logs:
                    print(f"✅ SUCCESS: Touch scrolling WORKS in alternate buffer!")
                    print(f"Arrow keys sent: {len(arrow_key_logs)} batches")
                    for log in arrow_key_logs:
                        print(f"  {log}")
                    return True
                elif buffer_type == "alternate" and not arrow_key_logs:
                    print(f"❌ FAILED: Alternate buffer detected but NO arrow keys sent")
                    return False
                else:
                    print(f"⚠ INCONCLUSIVE: Buffer type is '{buffer_type}'")
                    return None

            finally:
                await browser.close()

    finally:
        try:
            # Send q to quit less/claude
            client.send_keys(session_id, "q")
            await asyncio.sleep(1)
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    try:
        success = asyncio.run(test_android_claude_touch())
        if success is True:
            print("\n✅ CLAUDE/ALTERNATE BUFFER TOUCH SCROLLING TEST PASSED")
            sys.exit(0)
        elif success is False:
            print("\n❌ CLAUDE/ALTERNATE BUFFER TOUCH SCROLLING TEST FAILED")
            sys.exit(1)
        else:
            print("\n⚠ TEST INCONCLUSIVE")
            sys.exit(2)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
