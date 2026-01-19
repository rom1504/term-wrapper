#!/usr/bin/env python3
"""Debug repeated content issue, especially thoughts section."""

import asyncio
import sys
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright
from term_wrapper.cli import TerminalClient
from term_wrapper.server_manager import ServerManager


async def main():
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"Server URL: {server_url}")

    client = TerminalClient(base_url=server_url)

    # Create Claude session
    session_id = client.create_session(
        command=["bash", "-c", "cd /tmp && claude"],
        rows=40,
        cols=120
    )
    print(f"Session ID: {session_id}")

    await asyncio.sleep(3)

    web_url = f"{server_url}/?session={session_id}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

        await page.goto(web_url)
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(4)

        # Screenshot initial
        await page.screenshot(path='/home/ai/term_wrapper/thoughts_01_initial.png', full_page=True)
        print("📸 Initial state")

        # Ask question that triggers thinking
        await page.keyboard.type('what is 2+2?', delay=50)
        await asyncio.sleep(0.5)
        await page.keyboard.press('Enter')

        # Wait for response with thinking
        await asyncio.sleep(5)

        await page.screenshot(path='/home/ai/term_wrapper/thoughts_02_response.png', full_page=True)
        print("📸 After response")

        # Get buffer content and look for duplicates
        content = await page.evaluate("""() => {
            const term = window.app ? window.app.term : null;
            if (!term) return null;

            let lines = [];
            for (let i = 0; i < term.buffer.active.length; i++) {
                const line = term.buffer.active.getLine(i);
                if (line) {
                    lines.push(line.translateToString(true));
                }
            }
            return lines;
        }""")

        # Look for "thinking" duplicates
        thinking_lines = [i for i, line in enumerate(content) if 'thinking' in line.lower()]
        print(f"\nLines containing 'thinking': {thinking_lines}")

        for idx in thinking_lines:
            print(f"  Line {idx}: {content[idx][:80]}")

        # Look for other duplicates
        seen = {}
        duplicates = []
        for i, line in enumerate(content):
            stripped = line.strip()
            if len(stripped) > 10:  # Ignore short lines
                if stripped in seen:
                    duplicates.append((seen[stripped], i, stripped[:80]))
                else:
                    seen[stripped] = i

        if duplicates:
            print(f"\n❌ Found {len(duplicates)} duplicate lines:")
            for orig_idx, dup_idx, text in duplicates[:10]:
                print(f"  Line {orig_idx} == Line {dup_idx}: {text}")
        else:
            print("\n✅ No duplicate lines found")

        await browser.close()

    try:
        client.delete_session(session_id)
    except:
        pass
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
