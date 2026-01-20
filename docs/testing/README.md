# Testing Documentation

This directory contains documentation and tools for testing term-wrapper, with a focus on mobile/touch scrolling verification.

## Test Suite Overview

### JavaScript Tests (56 tests)

Located in `tests/` directory:
- **Unit tests** (`tests/scrolling.test.js`) - 37 tests for scrolling logic
- **Integration tests** (`tests/scrolling-integration.test.js`) - 19 tests for WebSocket, gestures, boundaries

Run tests:
```bash
npm test                 # Run all tests
npm run test:watch       # Watch mode
npm run test:coverage    # Coverage report
```

### Python Tests (118 tests)

Run with pytest:
```bash
pytest tests/            # All Python tests
```

## Mobile/Touch Testing

### Android Emulator Testing

**Quick Start:**
```bash
# 1. Set up Android emulator (one-time setup)
./docs/testing/setup_android_emulator.sh

# 2. Start emulator
~/Android/Sdk/emulator/emulator -avd Pixel_5_API_33 -no-snapshot-load &

# 3. Run automated touch test via Chrome DevTools Protocol
uv run --python 3.12 python tests/test_android_cdp.py
```

**Documentation:**
- [ANDROID_TESTING.md](ANDROID_TESTING.md) - Complete Android emulator setup and testing guide
- [TEST_ON_REAL_DEVICE.md](TEST_ON_REAL_DEVICE.md) - Testing on physical devices (Xiaomi 13, etc.)

### Android Test Scripts

Located in `tests/test_android_*.py`:
- `test_android_cdp.py` - **Recommended** - Uses Chrome DevTools Protocol for automated touch testing
- `test_android_simple.py` - Basic ADB touch simulation
- `test_android_chrome.py` - Playwright + CDP approach
- `test_android_final.py` - Visual verification with screenshots
- `test_android_direct.py` - Direct ADB approach

## Test Results (v0.7.3)

### Touch Scrolling Fix Verification

✅ **Android 13 Emulator (Pixel 5)**
- Touch events captured and processed correctly
- Viewport scrolls: 82 → 72 (10 lines up on swipe down)
- All console debug logs show proper touch handling

✅ **JavaScript Tests**
- All 56 tests passing
- Unit tests cover all scrolling functions
- Integration tests verify WebSocket interaction

✅ **Bug Fixed**
- Root cause: Inverted scroll direction in `scrolling.js:103`
- Before: `scrollLines = direction === 'up' ? -scrollCalc.lines : scrollCalc.lines`
- After: `scrollLines = direction === 'up' ? scrollCalc.lines : -scrollCalc.lines`

### Test Coverage

**JavaScript (100% coverage on scrolling logic):**
- `isAlternateBuffer()` - 3 tests
- `calculateWheelScroll()` - 6 tests
- `calculateTouchScroll()` - 6 tests
- `getArrowKeySequence()` - 2 tests
- `generateArrowKeys()` - 8 tests
- `checkScrollThreshold()` - 2 tests
- `determineScrollAction()` - 10 tests
- Integration scenarios - 19 tests

**Python (118 tests):**
- Unit tests for terminal client
- Integration tests for session management
- E2E tests for vim, htop, claude CLI
- Web frontend tests

## Quick Reference

### Run All Tests

```bash
# JavaScript tests
npm test

# Python tests
pytest

# Android emulator test
uv run --python 3.12 python tests/test_android_cdp.py
```

### Common Issues

**Android emulator won't start:**
- Check KVM permissions: `sudo chmod 666 /dev/kvm`
- Verify installation: `~/Android/Sdk/emulator/emulator -list-avds`

**Chrome DevTools connection fails:**
- Ensure port forwarding: `adb forward tcp:9222 localabstract:chrome_devtools_remote`
- Force stop Chrome: `adb shell am force-stop com.android.chrome`

**Touch events not working:**
- Clear Chrome cache by force-stopping Chrome
- Verify JavaScript loaded: Check for `window.app` in console

## Related Documentation

- [CHANGELOG.md](../../CHANGELOG.md) - Release history
- [frontend/README.md](../../frontend/README.md) - Web frontend documentation
- [README.md](../../README.md) - Main project README
