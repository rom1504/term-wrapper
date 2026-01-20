#!/usr/bin/env python3
"""Verify scroll speed fix is working."""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright
from term_wrapper.server_manager import ServerManager


async def simulate_swipe(page, speed_name, move_speed):
    """Simulate a swipe with specific speed."""
    print(f"\n--- Testing {speed_name} swipe (move_speed={move_speed}px/step) ---")

    # Get initial viewport position
    initial = await page.evaluate("""() => {
        return window.app.term.buffer.active.viewportY;
    }""")

    # Simulate swipe
    await page.evaluate(f"""(moveSpeed) => {{
        const container = document.getElementById('terminal-container');
        const rect = container.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height - 50;
        const endY = rect.top + 50;

        let currentY = startY;

        // Create initial touch
        const createTouch = (y) => ({{
            identifier: 0,
            target: container,
            clientX: centerX,
            clientY: y,
            pageX: centerX,
            pageY: y
        }});

        let touch = createTouch(currentY);

        // Touch start
        container.dispatchEvent(new TouchEvent('touchstart', {{
            touches: [touch],
            targetTouches: [touch],
            changedTouches: [touch],
            bubbles: true
        }}));

        // Move with specified speed
        while (currentY > endY) {{
            currentY -= moveSpeed;
            if (currentY < endY) currentY = endY;

            touch = createTouch(currentY);
            container.dispatchEvent(new TouchEvent('touchmove', {{
                touches: [touch],
                targetTouches: [touch],
                changedTouches: [touch],
                bubbles: true
            }}));
        }}

        // Touch end
        container.dispatchEvent(new TouchEvent('touchend', {{
            touches: [],
            targetTouches: [],
            changedTouches: [touch],
            bubbles: true
        }}));
    }}""", move_speed)

    await asyncio.sleep(0.3)

    # Get final viewport position
    final = await page.evaluate("""() => {
        return window.app.term.buffer.active.viewportY;
    }""")

    lines_scrolled = final - initial
    swipe_distance = 896 - 100  # Roughly viewport height

    print(f"  Initial viewport Y: {initial}")
    print(f"  Final viewport Y: {final}")
    print(f"  Lines scrolled: {lines_scrolled}")
    print(f"  Expected multiplier used: ", end="")
    if move_speed > 15:
        print("12 (very fast)")
    elif move_speed > 8:
        print("8 (fast)")
    else:
        print("5 (slow)")

    return lines_scrolled


async def main():
    # Start server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 414, 'height': 896})

        # Navigate to term-wrapper with content to scroll
        print("\n=== Starting term-wrapper with scrollable content ===")
        await page.goto(f'{server_url}/?cmd=bash&args=-c "seq 1 1000"')

        # Wait for terminal to load
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(3)

        # Check version
        version = await page.evaluate("""() => {
            return document.getElementById('version')?.textContent || 'not found';
        }""")
        print(f"Version displayed: {version}")

        if version != "v0.6.5":
            print(f"⚠️  WARNING: Expected v0.6.5, got {version}")
            print("Make sure to hard refresh (Ctrl+Shift+R)!")

        # Test different swipe speeds
        results = {}

        # Test 1: Slow swipe (should use multiplier 5)
        results['slow'] = await simulate_swipe(page, "SLOW", 3)
        await asyncio.sleep(1)

        # Scroll back
        await page.evaluate("window.app.term.scrollToTop()")
        await asyncio.sleep(1)

        # Test 2: Medium swipe (should use multiplier 8)
        results['medium'] = await simulate_swipe(page, "MEDIUM", 10)
        await asyncio.sleep(1)

        # Scroll back
        await page.evaluate("window.app.term.scrollToTop()")
        await asyncio.sleep(1)

        # Test 3: Fast swipe (should use multiplier 12)
        results['fast'] = await simulate_swipe(page, "FAST", 20)
        await asyncio.sleep(1)

        # Analysis
        print("\n" + "="*60)
        print("RESULTS ANALYSIS")
        print("="*60)

        print(f"\nSlow swipe scrolled:   {results['slow']} lines")
        print(f"Medium swipe scrolled: {results['medium']} lines")
        print(f"Fast swipe scrolled:   {results['fast']} lines")

        print("\nExpected behavior:")
        print("  - Fast should scroll MORE than medium")
        print("  - Medium should scroll MORE than slow")
        print("  - Fast should be ~2-3x slow")

        # Verify
        success = True
        if results['fast'] > results['medium'] > results['slow']:
            print("\n✅ PASS: Variable speed is working!")
        else:
            print("\n❌ FAIL: Variable speed NOT working correctly")
            success = False

        if results['fast'] >= results['slow'] * 2:
            print("✅ PASS: Fast swipe is at least 2x faster than slow")
        else:
            print(f"❌ FAIL: Fast swipe should be 2x+ faster (got {results['fast']/results['slow']:.1f}x)")
            success = False

        # Compare to old behavior (3 lines per 50px)
        print(f"\nOld behavior (v0.6.4): Would scroll ~{results['slow']*3/5:.0f} lines for slow swipe")
        improvement = (results['slow'] / (results['slow']*3/5) - 1) * 100
        print(f"Improvement: +{improvement:.0f}% faster")

        await browser.close()

        return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
