#!/usr/bin/env python3
"""Debug test to check if app.js module loading works."""

import asyncio
from playwright.async_api import async_playwright
from term_wrapper.server_manager import ServerManager
from term_wrapper.cli import TerminalClient


async def test_module_loading():
    """Test if the ES6 module loads correctly."""
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    client = TerminalClient(base_url=server_url)

    try:
        # Create a simple session
        session_id = client.create_session(
            command=["bash"],
            rows=20,
            cols=80,
            env={"TERM": "xterm-256color"}
        )

        await asyncio.sleep(1)
        web_url = f"{server_url}/?session={session_id}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Listen to console messages
            console_messages = []
            page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))

            # Listen to page errors
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            # Navigate
            await page.goto(web_url)

            # Wait a bit for page to load
            await asyncio.sleep(3)

            # Check what loaded
            print("=== Console Messages ===")
            for msg in console_messages:
                print(msg)

            print("\n=== Page Errors ===")
            for err in page_errors:
                print(err)

            # Check if app exists
            print("\n=== Checking window.app ===")
            app_exists = await page.evaluate("typeof window.app")
            print(f"typeof window.app: {app_exists}")

            if app_exists != "undefined":
                print("✅ window.app loaded successfully!")
            else:
                print("❌ window.app did NOT load")

                # Check if script tags loaded
                scripts = await page.evaluate("""() => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    return scripts.map(s => ({
                        src: s.src,
                        type: s.type,
                        loaded: s.hasAttribute('loaded')
                    }));
                }""")
                print("\nScript tags:")
                for script in scripts:
                    print(f"  {script}")

            await browser.close()

    finally:
        try:
            client.delete_session(session_id)
        except:
            pass
        client.close()


if __name__ == "__main__":
    asyncio.run(test_module_loading())
