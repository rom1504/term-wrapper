# Touch Scrolling Fix - Root Cause Analysis

## User Report
"scrolling still bad and some repetition. i am on xiaomi 13 android. what are we missing? describe your testing strategy, something must be off"

## What Was Wrong With My Testing Strategy

### Previous (Broken) Testing Approach
I was NOT actually testing touch events. Instead:

1. **Used mouse events instead of touch events**
   - `page.mouse.move()` simulates MOUSE, not TOUCH
   - Real Android devices use TouchEvent objects, not MouseEvent

2. **Called xterm.js APIs directly**
   - `term.scrollLines()` via `page.evaluate()`
   - This bypassed my custom touch handlers entirely
   - Never verified touch event handlers were actually firing

3. **Never checked if touch events were being dispatched**
   - No console logging
   - No verification that `handleTouchStart/Move/End` were called
   - Just assumed they worked

### Result
My tests passed because I was directly calling the scroll API, but the actual touch handlers on real devices were **completely broken**.

## The Actual Bug

### Root Cause: Inverted Scroll Direction

**Location**: `term_wrapper/frontend/app.js:392`

**Original Code**:
```javascript
this.term.scrollLines(-scrollAmount); // Negative because touch down = scroll up
```

**The Problem**:
- When user swipes UP (finger moves up on screen):
  - clientY decreases (617 → 394)
  - diff = touchY - lastTouchY = negative value (e.g., -22)
  - scrollAmount = Math.round(-22 / 50 * 3) = -1
  - `scrollLines(-(-1))` = `scrollLines(1)` = **SCROLL DOWN** ❌

- User swipes UP → Content scrolls DOWN
- User swipes DOWN → Content scrolls UP
- **Completely backwards!**

**The Fix**:
```javascript
this.term.scrollLines(scrollAmount); // Positive diff (finger down) = scroll down
```

Now:
- User swipes UP → diff is negative → `scrollLines(-1)` → SCROLL UP ✅
- User swipes DOWN → diff is positive → `scrollLines(1)` → SCROLL DOWN ✅

Same fix applied to momentum scrolling in `handleTouchEnd`.

## Correct Testing Strategy

### New Approach (Working)
Created `docs/examples/debug_touch_events.py`:

1. **Dispatch actual TouchEvent objects**
   ```javascript
   const touchStart = new Touch({
       identifier: 0,
       target: container,
       clientX: startX,
       clientY: startY,
       ...
   });

   container.dispatchEvent(new TouchEvent('touchstart', {
       touches: [touchStart],
       ...
   }));
   ```

2. **Verify touch handlers fire**
   - Added console.log in handlers
   - Captured browser console output
   - Confirmed events reaching handlers

3. **Check viewport actually changes**
   - Read `term.buffer.active.viewportY` before/after
   - Verify it changes in correct direction
   - Test result: Changed from 24 → 14 ✅

## Secondary Issue: Touch Handler Attachment Point

### Initial Problem
Handlers were attached to `.xterm-viewport` (created by xterm.js):
```javascript
const viewport = document.querySelector('.xterm-viewport');
viewport.addEventListener('touchstart', ...);
```

This conflicted with xterm.js's built-in touch handling.

### Solution
Attach to parent container instead:
```javascript
const terminalContainer = document.getElementById('terminal-container');
terminalContainer.addEventListener('touchstart', ...);
```

This intercepts touch events BEFORE they reach xterm.js, allowing our custom scrolling to work.

## Verification

### Test Results
1. **Touch Event Test** (`debug_touch_events.py`):
   - ✅ Touch events fire correctly
   - ✅ Viewport changes from 24 → 14 on swipe up
   - ✅ 10 touchmove events processed

2. **Claude Mobile Scroll Test** (`test_mobile_scroll.py`):
   - ✅ Generated 45 lines of content
   - ✅ Scroll up/down both directions work
   - ✅ Can scroll to top (viewport_y = 0)
   - ✅ Can scroll to bottom (viewport_y = 118)
   - ✅ 8 screenshots captured

## Outstanding Issues

1. **"Some repetition"** - User reported repeated content, especially "thoughts"
   - Not reproduced in automated tests (see `test_screencast/` folder)
   - Comprehensive screencast analysis (303 lines, video recording) found NO content duplication
   - Only UI separators appear multiple times (expected)
   - May be timing-related or specific to real Xiaomi 13 device
   - Needs real device testing to confirm

2. **Real device testing**
   - Automated tests use Playwright with touch simulation
   - User has Xiaomi 13 Android - should test on actual device
   - May have device-specific behavior
   - See `test_screencast/README.md` for screencast test details

## Summary

**Testing Strategy Issue**: I was testing the wrong thing (API calls, not touch events)

**Actual Bug**: Scroll direction was inverted (math error with negation)

**Fix**: Removed extra negation in `scrollLines()` call

**Status**: Touch scrolling now works correctly in automated tests
