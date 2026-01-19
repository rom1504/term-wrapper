#!/usr/bin/env python3
"""Extract frames from screencast video for analysis."""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1200, 'height': 900})

        # Load the video
        video_path = f"file://{'/home/ai/term_wrapper/test_screencast/827f017f6d20433e6897bc991eab4147.webm'}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; background: #000; }}
                video {{ width: 100%; height: 100vh; }}
            </style>
        </head>
        <body>
            <video id="vid" controls>
                <source src="{video_path}" type="video/webm">
            </video>
        </body>
        </html>
        """

        await page.set_content(html)
        await page.wait_for_selector('#vid')

        # Get video duration
        duration = await page.evaluate("""() => {
            const vid = document.getElementById('vid');
            return new Promise((resolve) => {
                vid.onloadedmetadata = () => resolve(vid.duration);
            });
        }""")

        print(f"Video duration: {duration:.2f} seconds")

        # Extract frames at 1fps
        fps = 1
        num_frames = int(duration * fps)

        print(f"Extracting {num_frames} frames at {fps} fps...")

        for i in range(num_frames):
            current_time = i / fps

            # Seek to position
            await page.evaluate(f"""() => {{
                const vid = document.getElementById('vid');
                vid.currentTime = {current_time};
                return new Promise((resolve) => {{
                    vid.onseeked = () => resolve();
                }});
            }}""")

            await asyncio.sleep(0.2)  # Wait for frame to render

            # Take screenshot
            await page.screenshot(path=f'frame_{i:03d}.png')
            print(f"  Frame {i:03d} @ {current_time:.1f}s")

        await browser.close()

        print(f"\n✓ Extracted {num_frames} frames")
        print("Now analyzing frames for 'Herding' text...")


if __name__ == "__main__":
    asyncio.run(main())
