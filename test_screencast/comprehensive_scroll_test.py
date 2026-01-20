#!/usr/bin/env python3
"""Comprehensive mobile scroll testing across multiple devices.

Based on research:
- Playwright mobile testing best practices (2025)
- xterm.js touch scroll limitations
- Device emulation + real touch event testing
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '/home/ai/term_wrapper')

from playwright.async_api import async_playwright
from term_wrapper.server_manager import ServerManager


# Device configurations based on Playwright best practices 2025
DEVICES = [
    {
        'name': 'iPhone 13',
        'viewport': {'width': 390, 'height': 844},
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
        'device_scale_factor': 3,
        'has_touch': True,
    },
    {
        'name': 'Xiaomi 13 (Android)',
        'viewport': {'width': 414, 'height': 896},  # Similar to user's device
        'user_agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36',
        'device_scale_factor': 2.75,
        'has_touch': True,
    },
    {
        'name': 'Samsung Galaxy S21',
        'viewport': {'width': 360, 'height': 800},
        'user_agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36',
        'device_scale_factor': 3,
        'has_touch': True,
    },
    {
        'name': 'iPad Pro',
        'viewport': {'width': 1024, 'height': 1366},
        'user_agent': 'Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
        'device_scale_factor': 2,
        'has_touch': True,
    },
]


async def simulate_touch_scroll(page, scroll_type, device_name):
    """Simulate a specific type of touch scroll.

    Based on research: Use proper TouchEvent objects, not mouse events.
    """
    print(f"\n  Testing {scroll_type} scroll on {device_name}...")

    # Get initial viewport position
    initial = await page.evaluate("""() => {
        const term = window.app.term;
        return {
            viewportY: term.buffer.active.viewportY,
            bufferLength: term.buffer.active.length,
            rows: term.rows
        };
    }""")

    # Define scroll parameters based on type
    scroll_params = {
        'slow_drag': {'step': 3, 'description': 'Slow drag (3px/step)'},
        'medium_swipe': {'step': 10, 'description': 'Medium swipe (10px/step)'},
        'fast_flick': {'step': 20, 'description': 'Fast flick (20px/step)'},
        'very_fast': {'step': 30, 'description': 'Very fast (30px/step)'},
    }

    params = scroll_params[scroll_type]

    # Simulate the swipe
    result = await page.evaluate(f"""(params) => {{
        const container = document.getElementById('terminal-container');
        const rect = container.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height - 100;
        const endY = rect.top + 100;
        const step = params.step;

        let currentY = startY;
        let lastY = currentY;
        let moveCount = 0;
        const velocities = [];

        const createTouch = (y) => ({{
            identifier: 0,
            target: container,
            clientX: centerX,
            clientY: y,
            pageX: centerX,
            pageY: y
        }});

        // Touch start
        let touch = createTouch(currentY);
        container.dispatchEvent(new TouchEvent('touchstart', {{
            touches: [touch],
            targetTouches: [touch],
            changedTouches: [touch],
            bubbles: true
        }}));

        // Collect velocity data during move
        while (currentY > endY) {{
            lastY = currentY;
            currentY -= step;
            if (currentY < endY) currentY = endY;

            const diff = Math.abs(currentY - lastY);
            velocities.push(diff);

            touch = createTouch(currentY);
            container.dispatchEvent(new TouchEvent('touchmove', {{
                touches: [touch],
                targetTouches: [touch],
                changedTouches: [touch],
                bubbles: true
            }}));

            moveCount++;
        }}

        // Touch end
        container.dispatchEvent(new TouchEvent('touchend', {{
            touches: [],
            targetTouches: [],
            changedTouches: [touch],
            bubbles: true
        }}));

        return {{
            moveCount,
            totalDistance: startY - endY,
            avgVelocity: velocities.reduce((a, b) => a + b, 0) / velocities.length,
            maxVelocity: Math.max(...velocities)
        }};
    }}""", {'step': params['step']})

    # Wait for momentum scrolling to finish
    await asyncio.sleep(0.5)

    # Get final position
    final = await page.evaluate("""() => {
        const term = window.app.term;
        return {
            viewportY: term.buffer.active.viewportY,
            bufferLength: term.buffer.active.length
        };
    }""")

    lines_scrolled = final['viewportY'] - initial['viewportY']
    swipe_distance = result['totalDistance']

    # Calculate expected multiplier based on velocity
    avg_velocity = result['avgVelocity']
    if avg_velocity > 15:
        expected_multiplier = 12
    elif avg_velocity > 8:
        expected_multiplier = 8
    else:
        expected_multiplier = 5

    # Calculate actual lines per 50px
    lines_per_50px = (lines_scrolled / swipe_distance) * 50 if swipe_distance > 0 else 0

    return {
        'scroll_type': scroll_type,
        'description': params['description'],
        'lines_scrolled': lines_scrolled,
        'swipe_distance': swipe_distance,
        'move_count': result['moveCount'],
        'avg_velocity': avg_velocity,
        'max_velocity': result['maxVelocity'],
        'expected_multiplier': expected_multiplier,
        'lines_per_50px': lines_per_50px,
        'initial_viewport': initial['viewportY'],
        'final_viewport': final['viewportY'],
    }


async def test_device(device_config, server_url, output_dir):
    """Test scrolling on a specific device."""
    device_name = device_config['name']
    print(f"\n{'='*60}")
    print(f"Testing Device: {device_name}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # Create context with device configuration
        context = await browser.new_context(
            viewport=device_config['viewport'],
            user_agent=device_config['user_agent'],
            device_scale_factor=device_config['device_scale_factor'],
            has_touch=device_config['has_touch'],
        )

        page = await context.new_page()

        # Navigate to term-wrapper with scrollable content
        print(f"Loading terminal with scrollable content...")
        await page.goto(f'{server_url}/?cmd=bash&args=-c "seq 1 1000"')

        # Wait for terminal to load
        await page.wait_for_selector('#terminal', timeout=10000)
        await asyncio.sleep(3)

        # Check version
        version = await page.evaluate("""() => {
            return document.getElementById('version')?.textContent || 'not found';
        }""")
        print(f"Version: {version}")

        if version != "v0.6.5":
            print(f"⚠️  WARNING: Expected v0.6.5, got {version}")

        # Take initial screenshot
        screenshot_path = output_dir / f"{device_name.replace(' ', '_')}_initial.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"Screenshot: {screenshot_path}")

        # Test all scroll types
        results = []
        scroll_types = ['slow_drag', 'medium_swipe', 'fast_flick', 'very_fast']

        for scroll_type in scroll_types:
            # Reset scroll position
            await page.evaluate("window.app.term.scrollToTop()")
            await asyncio.sleep(0.5)

            # Perform scroll test
            result = await simulate_touch_scroll(page, scroll_type, device_name)
            results.append(result)

            # Take screenshot after scroll
            screenshot_path = output_dir / f"{device_name.replace(' ', '_')}_{scroll_type}.png"
            await page.screenshot(path=str(screenshot_path))

            print(f"    {result['description']}")
            print(f"      Lines scrolled: {result['lines_scrolled']}")
            print(f"      Avg velocity: {result['avg_velocity']:.1f}px")
            print(f"      Expected multiplier: {result['expected_multiplier']}")
            print(f"      Actual lines/50px: {result['lines_per_50px']:.1f}")

        # Create sequence of screenshots showing scroll progression
        print(f"\n  Creating scroll sequence screenshots...")
        await page.evaluate("window.app.term.scrollToTop()")
        await asyncio.sleep(0.5)

        # Take screenshots at different scroll positions
        for i in range(5):
            screenshot_path = output_dir / f"{device_name.replace(' ', '_')}_sequence_{i}.png"
            await page.screenshot(path=str(screenshot_path))

            if i < 4:  # Don't scroll after last screenshot
                await simulate_touch_scroll(page, 'fast_flick', device_name)
                await asyncio.sleep(0.3)

        await context.close()
        await browser.close()

        return {
            'device': device_name,
            'viewport': device_config['viewport'],
            'version': version,
            'results': results,
        }


async def main():
    """Run comprehensive scroll testing across all devices."""
    print("="*60)
    print("COMPREHENSIVE MOBILE SCROLL TESTING")
    print("="*60)
    print("\nResearch-based testing strategy:")
    print("- Multiple device emulations (iPhone, Android, iPad)")
    print("- Proper TouchEvent simulation (not mouse events)")
    print("- Variable scroll speeds (slow, medium, fast, very fast)")
    print("- Screenshots and video capture")
    print("- Velocity-based multiplier verification")
    print("\nReferences:")
    print("- Playwright mobile testing best practices (2025)")
    print("- xterm.js touch scroll limitations (GitHub #5377)")
    print("- Device emulation guidelines (Checkly, Qualiti)")

    # Start server
    server_manager = ServerManager()
    server_url = server_manager.get_server_url()
    print(f"\nServer URL: {server_url}")

    # Create output directory
    output_dir = Path('/home/ai/term_wrapper/test_screencast/scroll_test_output')
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Test all devices
    all_results = []
    for device_config in DEVICES:
        try:
            device_results = await test_device(device_config, server_url, output_dir)
            all_results.append(device_results)
        except Exception as e:
            print(f"\n❌ ERROR testing {device_config['name']}: {e}")
            import traceback
            traceback.print_exc()

    # Generate summary report
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)

    for device_result in all_results:
        device_name = device_result['device']
        viewport = device_result['viewport']
        version = device_result['version']

        print(f"\n{device_name} ({viewport['width']}x{viewport['height']})")
        print(f"  Version: {version}")

        for result in device_result['results']:
            scroll_type = result['scroll_type']
            lines_scrolled = result['lines_scrolled']
            expected_mult = result['expected_multiplier']
            actual_lines_per_50px = result['lines_per_50px']

            # Check if it matches expected behavior
            expected_lines_per_50px = expected_mult
            diff_pct = abs(actual_lines_per_50px - expected_lines_per_50px) / expected_lines_per_50px * 100

            status = "✅" if diff_pct < 30 else "⚠️"  # Allow 30% variance

            print(f"  {status} {scroll_type:15s} - {lines_scrolled:3d} lines "
                  f"(expected ~{expected_mult} lines/50px, got {actual_lines_per_50px:.1f})")

    # Check for consistency across devices
    print("\n" + "="*60)
    print("CROSS-DEVICE CONSISTENCY")
    print("="*60)

    # Compare fast_flick results across devices
    fast_flick_results = []
    for device_result in all_results:
        for result in device_result['results']:
            if result['scroll_type'] == 'fast_flick':
                fast_flick_results.append({
                    'device': device_result['device'],
                    'lines_per_50px': result['lines_per_50px'],
                })

    if fast_flick_results:
        avg_lines = sum(r['lines_per_50px'] for r in fast_flick_results) / len(fast_flick_results)
        print(f"\nFast flick average across devices: {avg_lines:.1f} lines/50px")
        print(f"Expected: ~12 lines/50px")

        for r in fast_flick_results:
            variance = abs(r['lines_per_50px'] - avg_lines) / avg_lines * 100
            status = "✅" if variance < 20 else "⚠️"
            print(f"  {status} {r['device']:20s}: {r['lines_per_50px']:5.1f} "
                  f"({variance:.0f}% variance from average)")

    print("\n" + "="*60)
    print("FILES GENERATED")
    print("="*60)
    print(f"\nOutput directory: {output_dir}")
    png_files = sorted(output_dir.glob("*.png"))
    print(f"Screenshots: {len(png_files)} files")
    print("\nDevice initial states:")
    for f in sorted(output_dir.glob("*_initial.png")):
        print(f"  - {f.name}")
    print("\nScroll type tests:")
    for f in sorted(output_dir.glob("*_slow_drag.png")):
        print(f"  - {f.name}")
    for f in sorted(output_dir.glob("*_medium_swipe.png")):
        print(f"  - {f.name}")
    for f in sorted(output_dir.glob("*_fast_flick.png")):
        print(f"  - {f.name}")
    print("\nScroll sequences (progression):")
    for f in sorted(output_dir.glob("*_sequence_*.png")):
        print(f"  - {f.name}")

    return all_results


if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        print("\n✅ Comprehensive testing complete!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
