#!/usr/bin/env python3
"""Test if filtering ESC[<u fixes the thinking indicator duplication."""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 414, 'height': 896})

        # Navigate to term-wrapper with Claude
        await page.goto('http://localhost:41831/?cmd=bash&args=-c%20%22cd%20/tmp%20%26%26%20claude%22')

        # Wait for terminal to be ready
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(3)

        # Type a command to trigger thinking
        await page.keyboard.type('write a 20 line poem')
        await asyncio.sleep(1)
        await page.keyboard.press('Enter')

        # Wait for thinking to start
        await asyncio.sleep(3)

        # Extract visible text from terminal buffer
        for i in range(10):  # Check 10 times over 10 seconds
            await asyncio.sleep(1)

            visible_text = await page.evaluate("""() => {
                const term = window.app.term;
                const buffer = term.buffer.active;
                const viewport_y = buffer.viewportY;
                let text_lines = [];
                for (let i = 0; i < term.rows; i++) {
                    const line = buffer.getLine(viewport_y + i);
                    if (line) {
                        text_lines.push(line.translateToString(true).trim());
                    }
                }
                return text_lines.join('\n');
            }""")

            # Count thinking indicators (any variant)
            indicators = ['Grooving', 'Herding', 'Mulling', 'Coalescing', 'Sketching', 'Pondering']
            counts = {ind: visible_text.count(ind) for ind in indicators}
            total = sum(counts.values())

            if total > 0:
                print(f"\n=== After {i+3}s ===")
                print(f"Total thinking indicators visible: {total}")
                for ind, count in counts.items():
                    if count > 0:
                        print(f"  {ind}: {count}")

                if total > 1:
                    print("  ⚠️ DUPLICATION DETECTED!")
                else:
                    print("  ✅ No duplication")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
