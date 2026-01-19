#!/usr/bin/env python3
"""Test different scroll speed configurations."""

import asyncio
from playwright.async_api import async_playwright


async def test_scroll_config(page, multiplier, description):
    """Test a specific scroll configuration."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Multiplier: {multiplier}")
    print(f"{'='*60}")

    # Inject the scroll multiplier
    await page.evaluate(f"""() => {{
        window.app.scrollMultiplier = {multiplier};
    }}""")

    # Get initial scroll position
    initial_pos = await page.evaluate("""() => {
        const term = window.app.term;
        return term.buffer.active.viewportY;
    }""")

    # Simulate swipe up (scroll down in content)
    await page.evaluate("""() => {
        const container = document.getElementById('terminal-container');
        const rect = container.getBoundingClientRect();
        const startY = rect.top + rect.height - 100;
        const endY = rect.top + 100;

        // Create touch events
        const touch = {
            identifier: 0,
            target: container,
            clientX: rect.left + rect.width / 2,
            clientY: startY,
            pageX: rect.left + rect.width / 2,
            pageY: startY
        };

        // Touch start
        container.dispatchEvent(new TouchEvent('touchstart', {
            touches: [touch],
            targetTouches: [touch],
            changedTouches: [touch],
            bubbles: true
        }));

        // Move in steps
        for (let y = startY; y > endY; y -= 10) {
            touch.clientY = y;
            touch.pageY = y;
            container.dispatchEvent(new TouchEvent('touchmove', {
                touches: [touch],
                targetTouches: [touch],
                changedTouches: [touch],
                bubbles: true
            }));
        }

        // Touch end
        container.dispatchEvent(new TouchEvent('touchend', {
            touches: [],
            targetTouches: [],
            changedTouches: [touch],
            bubbles: true
        }));
    }""")

    await asyncio.sleep(0.5)

    # Get final scroll position
    final_pos = await page.evaluate("""() => {
        const term = window.app.term;
        return term.buffer.active.viewportY;
    }""")

    lines_scrolled = final_pos - initial_pos
    print(f"Lines scrolled: {lines_scrolled}")
    print(f"Swipe distance: ~200px")
    print(f"Lines per 50px: {lines_scrolled / 4:.1f}")

    return lines_scrolled


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 414, 'height': 896})

        # Start term-wrapper
        print("Navigate to term-wrapper with vim (has lots of content to scroll)")
        await page.goto('http://localhost:41831/?cmd=bash&args=-c%20%22yes%20hello%20%7C%20head%20-100%22')

        await asyncio.sleep(3)

        # Test configurations
        configs = [
            (3, "Current (3 lines per 50px)"),
            (6, "2x faster (6 lines per 50px)"),
            (8, "Fast (8 lines per 50px)"),
            (10, "Very fast (10 lines per 50px)"),
            (12, "Aggressive (12 lines per 50px)"),
        ]

        for multiplier, description in configs:
            await test_scroll_config(page, multiplier, description)
            await asyncio.sleep(1)

        print("\n" + "="*60)
        print("RECOMMENDATION:")
        print("- Current (3): TOO SLOW")
        print("- 6-8: Good balance")
        print("- 10-12: Very fast, might be hard to control")
        print("="*60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
