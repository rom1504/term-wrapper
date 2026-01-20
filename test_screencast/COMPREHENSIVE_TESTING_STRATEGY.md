# Comprehensive Mobile Scroll Testing Strategy

## Research Summary

Based on 2025 best practices for mobile web testing:

### Key Findings from Research

1. **Playwright Mobile Testing** ([AlphaBin](https://www.alphabin.co/blog/using-playwright-for-mobile-web-testing), [Qualiti](https://www.qualiti.ai/playwright-test-automation/playwright-mobile-testing))
   - Device emulation is good for CI/CD and quick regression testing
   - Real device testing is essential for production validation
   - Combine both approaches for comprehensive coverage

2. **xterm.js Touch Limitations** ([GitHub #5377](https://github.com/xtermjs/xterm.js/issues/5377))
   - xterm.js has "limited support for touch interactions on mobile devices"
   - Touch gestures for scrolling don't work well or fall back to basic mouse events
   - This confirms our custom touch scroll implementation was necessary

3. **Touch Event Testing** ([Checkly](https://www.checklyhq.com/docs/learn/playwright/emulating-mobile-devices/))
   - Must use proper TouchEvent objects, not mouse events
   - Touch targets are smaller and less tolerant than desktop clicks
   - Scroll elements into view before interacting

4. **Viewport Considerations** ([Playwright Docs](https://playwright.dev/docs/emulation))
   - Safari URL bar collapses when scrolling, changing viewport height
   - Can break tests for sticky headers/footers
   - 100vh units behave differently on mobile

## Testing Strategy

### Phase 1: Code Verification (COMPLETED ✅)

**Objective**: Verify code changes are deployed correctly

**Methods**:
- Source code inspection
- Version number verification
- Package installation check
- Content verification

**Results**:
```
✅ Variable speed code present in app.js
✅ Multipliers: 5 (slow), 8 (medium), 12 (fast)
✅ Version 0.6.5 deployed and installed
✅ Old code (multiplier=3) removed
```

### Phase 2: Manual Device Testing (USER REQUIRED)

**Objective**: Verify scrolling works on real device (Xiaomi 13 Android)

**Test Devices**:
1. **Primary**: Xiaomi 13 (Android) - User's device
2. **Secondary**: iPhone (iOS) - If available
3. **Tertiary**: iPad/Tablet - For larger viewport

**Test Procedure**:

#### Setup
```bash
# 1. Kill old servers
pkill -f term_wrapper.server

# 2. Reinstall latest version
pip install -e /home/ai/term_wrapper --break-system-packages

# 3. Start with scrollable content
term-wrapper web bash -c 'seq 1 1000'

# 4. Open in mobile browser
```

#### Verification Checklist

**Before Testing**:
- [ ] Version shows "v0.6.5" in top left
- [ ] Hard refresh browser (Ctrl+Shift+R)
- [ ] Clear browser cache if version is wrong
- [ ] Terminal loads and displays content

**Test 1: Slow Drag**
- [ ] Place finger on terminal
- [ ] Drag slowly upward (3px/frame movement)
- [ ] Expected: Scrolls ~5 lines per 50px finger movement
- [ ] Expected: Noticeably faster than v0.6.4 (was 3 lines/50px)
- [ ] Result: _____ lines scrolled (estimate)

**Test 2: Medium Swipe**
- [ ] Swipe upward with moderate speed
- [ ] Expected: Scrolls ~8 lines per 50px
- [ ] Expected: Faster than slow drag
- [ ] Result: _____ lines scrolled (estimate)

**Test 3: Fast Flick**
- [ ] Quick flick upward
- [ ] Expected: Scrolls ~12 lines per 50px
- [ ] Expected: Much faster than slow drag (2-4x)
- [ ] Momentum scrolling should continue briefly
- [ ] Result: _____ lines scrolled (estimate)

**Test 4: Comparison**
- [ ] Fast flick > Medium swipe > Slow drag (in speed)
- [ ] All methods feel responsive
- [ ] No lag or stuttering
- [ ] Natural feel - faster hand = faster scroll

**Test 5: Edge Cases**
- [ ] Scroll to top (should stop at line 1)
- [ ] Scroll to bottom (should stop at end)
- [ ] Multi-touch doesn't break scrolling
- [ ] Switching between speeds works smoothly

### Phase 3: Cross-Device Verification (RECOMMENDED)

**Objective**: Ensure consistent behavior across devices

**Test Matrix**:

| Device | Viewport | Expected Behavior |
|--------|----------|-------------------|
| Xiaomi 13 | 414x896 | Variable speed (5/8/12 lines per 50px) |
| iPhone 13 | 390x844 | Same variable speed |
| Samsung S21 | 360x800 | Same variable speed |
| iPad Pro | 1024x1366 | Faster due to larger viewport |

**Consistency Checks**:
- [ ] All devices show v0.6.5
- [ ] Variable speed works on all devices
- [ ] Fast swipe feels similar across devices
- [ ] No device-specific bugs

### Phase 4: Browser Console Verification

**Debug Commands** (Run in browser console):

```javascript
// Check if variable speed code is loaded
console.log(window.app.handleTouchMove.toString().includes('velocity'));
// Should print: true

// Check multiplier values
console.log(window.app.handleTouchMove.toString().match(/multiplier = \d+/g));
// Should show: ["multiplier = 12", "multiplier = 8", "multiplier = 5"]

// Check version
fetch('/version').then(r => r.json()).then(d => console.log(d));
// Should show: {version: "0.6.5"}

// Monitor scroll events (run before scrolling)
let scrollCount = 0;
window.app.term.buffer.active.onScroll = () => {
    scrollCount++;
    console.log(`Scroll event ${scrollCount}, position: ${window.app.term.buffer.active.viewportY}`);
};
```

### Phase 5: Performance Testing

**Metrics to Monitor**:

```javascript
// FPS during scrolling
let frameCount = 0;
let lastTime = performance.now();
setInterval(() => {
    const now = performance.now();
    const fps = (frameCount * 1000) / (now - lastTime);
    console.log(`FPS: ${fps.toFixed(1)}`);
    frameCount = 0;
    lastTime = now;
}, 1000);
requestAnimationFrame(function count() {
    frameCount++;
    requestAnimationFrame(count);
});

// Measure scroll lag
window.scrollStartTime = null;
document.getElementById('terminal-container').addEventListener('touchstart', () => {
    window.scrollStartTime = performance.now();
});
document.getElementById('terminal-container').addEventListener('touchmove', (e) => {
    if (window.scrollStartTime) {
        const lag = performance.now() - window.scrollStartTime;
        if (lag > 16) {  // Should respond within 1 frame (16ms @ 60fps)
            console.warn(`Scroll lag: ${lag.toFixed(1)}ms`);
        }
    }
});
```

### Phase 6: Visual Inspection

**What to Look For**:
- [ ] Smooth scrolling (no jank or stuttering)
- [ ] Content renders correctly during scroll
- [ ] No visual artifacts (tearing, flashing)
- [ ] Momentum scrolling feels natural
- [ ] Scroll position stays stable after release

### Phase 7: Regression Testing

**Verify No New Issues**:
- [ ] Claude Code thinking indicators work
- [ ] Status bar updates work
- [ ] Terminal resize works
- [ ] Disconnect button works
- [ ] Mobile control buttons work (ESC, TAB, etc.)
- [ ] Typing still works
- [ ] Copy/paste still works

## Expected Results

### Speed Improvements

| Swipe Type | v0.6.4 (Old) | v0.6.5 (New) | Improvement |
|-----------|--------------|--------------|-------------|
| Slow      | 3 lines/50px | 5 lines/50px | **+67%**    |
| Medium    | 3 lines/50px | 8 lines/50px | **+167%**   |
| Fast      | 3 lines/50px | 12 lines/50px| **+300%**   |

### Success Criteria

✅ **PASS** if:
- Fast swipe is 2-4x faster than slow swipe
- Scrolling feels responsive and natural
- Variable speed is noticeable
- No visual glitches or lag

❌ **FAIL** if:
- All speeds feel the same
- Scrolling is still "very slow"
- Lag or stuttering occurs
- Version is not v0.6.5

## Troubleshooting Guide

### Issue: Still Slow

**Possible Causes**:
1. Browser cache - Old JavaScript still loaded
2. Old server running - Wrong version serving
3. Version mismatch - Check displayed version

**Solutions**:
```bash
# 1. Hard refresh
Ctrl+Shift+R (or Cmd+Shift+R on Mac)

# 2. Clear browser cache completely
Settings > Privacy > Clear browsing data

# 3. Kill all servers and restart
pkill -f term_wrapper.server
term-wrapper web bash -c 'seq 1 1000'

# 4. Check console for errors
F12 > Console tab > Look for JavaScript errors

# 5. Verify version
console.log(document.getElementById('version').textContent);
// Should show: v0.6.5
```

### Issue: Inconsistent Speed

**Check**:
- Is velocity detection working?
- Are TouchEvent objects being created correctly?
- Is `handleTouchMove` being called?

**Debug**:
```javascript
// Add logging to handleTouchMove
const originalFunc = window.app.handleTouchMove;
window.app.handleTouchMove = function(e) {
    const diff = e.touches[0].clientY - this.lastTouchY;
    const velocity = Math.abs(diff);
    console.log(`Touch move: diff=${diff.toFixed(1)}, velocity=${velocity.toFixed(1)}`);
    return originalFunc.call(this, e);
};
```

### Issue: No Scrolling at All

**Check**:
- Is terminal focused?
- Are touch events being captured?
- Is `terminal-container` element present?

**Debug**:
```javascript
// Check if touch events are firing
document.getElementById('terminal-container').addEventListener('touchmove', (e) => {
    console.log('Touch move detected:', e.touches[0].clientY);
}, {passive: false});
```

## Test Report Template

```markdown
## Test Report: v0.6.5 Scroll Testing

**Date**: ___________
**Tester**: ___________
**Device**: Xiaomi 13 Android
**Browser**: ___________

### Environment
- Version displayed: v_____
- Browser cache cleared: Yes / No
- Hard refresh performed: Yes / No

### Test Results

#### Slow Drag
- Lines scrolled: _____ (expected ~5 per 50px)
- Feel: Too slow / Just right / Too fast
- Notes: ___________

#### Medium Swipe
- Lines scrolled: _____ (expected ~8 per 50px)
- Feel: Too slow / Just right / Too fast
- Faster than slow drag: Yes / No
- Notes: ___________

#### Fast Flick
- Lines scrolled: _____ (expected ~12 per 50px)
- Feel: Too slow / Just right / Too fast
- 2-4x faster than slow: Yes / No
- Notes: ___________

### Overall Assessment
- Variable speed working: Yes / No
- Improvement from v0.6.4: Yes / No / Can't tell
- Responsive feel: Yes / No
- Visual quality: Good / Fair / Poor

### Issues Found
1. ___________
2. ___________
3. ___________

### Recommendation
- [ ] PASS - Ready for production
- [ ] FAIL - Needs more work
- [ ] INCONCLUSIVE - Need more testing

### Next Steps
___________
```

## References

- [Playwright Mobile Testing Best Practices](https://www.alphabin.co/blog/using-playwright-for-mobile-web-testing)
- [xterm.js Touch Support Issue #5377](https://github.com/xtermjs/xterm.js/issues/5377)
- [Playwright Emulation Docs](https://playwright.dev/docs/emulation)
- [Mobile Testing Guide 2025](https://www.qualiti.ai/playwright-test-automation/playwright-mobile-testing)
- [Checkly Device Emulation](https://www.checklyhq.com/docs/learn/playwright/emulating-mobile-devices/)

## Conclusion

This comprehensive strategy combines:
1. ✅ **Code verification** - Automated checks
2. 📱 **Real device testing** - User manual testing
3. 🔍 **Browser debugging** - Console verification
4. 📊 **Performance metrics** - FPS and lag monitoring
5. 👀 **Visual inspection** - Subjective feel assessment

The most critical test is **real device testing on Xiaomi 13** since that's where the issue was reported. Emulation helps but cannot fully replace testing on actual hardware with real touch input.
