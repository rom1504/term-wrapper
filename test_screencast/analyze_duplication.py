#!/usr/bin/env python3
"""Analyze the exact duplication pattern in visible viewport."""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 414, 'height': 896},
            has_touch=True,
            is_mobile=True
        )
        page = await context.new_page()

        # Load one of the frames that shows duplication
        await page.goto(f"file:///home/ai/term_wrapper/test_screencast/analysis_frame_0020.png")
        await page.wait_for_load_state()

        await asyncio.sleep(1)

        # Can't analyze a PNG image directly, need to check the actual terminal buffer
        # Let me instead modify the approach

        await browser.close()

    print("Let me check the frames manually to count duplications...")
    print("\nChecking frames 0015-0039 (during generation):")

    from PIL import Image
    import pytesseract

    # Try to use OCR if available
    try:
        for frame_num in [15, 20, 25, 30, 35]:
            img_path = f'analysis_frame_{frame_num:04d}.png'
            img = Image.open(img_path)

            # Extract text from image
            text = pytesseract.image_to_string(img)

            grooving_count = text.count('Grooving')
            print(f"\nFrame {frame_num}: 'Grooving' appears {grooving_count} times")

            if grooving_count > 1:
                print("  TEXT EXTRACTED:")
                for line in text.split('\n'):
                    if 'grooving' in line.lower():
                        print(f"    {line}")

    except Exception as e:
        print(f"\nOCR not available: {e}")
        print("\nManually analyzing frames by viewing them...")


if __name__ == "__main__":
    asyncio.run(main())
