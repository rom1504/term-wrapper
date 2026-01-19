# Fix Plan for Duplication Issue

## Problem Analysis

### What the User Sees
1. **TWO "Grooving..." status messages** visible simultaneously during Claude generation
2. **TWO scrollbars**: one for browser page, one for terminal
3. This does NOT happen in a normal terminal with Claude Code

### Evidence from Frames
- Frame 0015-0039: Shows 2 instances of thinking indicator
- Different bullet points (·, *, ∗) suggest multiple lines
- Duplication disappears after scrolling

## Root Cause Hypotheses

### Theory 1: Double Scrollbar Issue ⭐ (MOST LIKELY)

User reported: "i have both the main browser scrolling bar and the one for the term"

**Problem**: If page body is scrollable AND terminal has internal scroll, touch events and rendering can conflict.

**Evidence**:
- CSS has `body { overflow: hidden }` but user still sees page scrollbar
- `#terminal-container` has `overflow: hidden` which might prevent terminal scroll
- This could cause xterm.js viewport to behave unexpectedly

**Fix**: Ensure ONLY terminal scrolls, not page body

### Theory 2: Scrollback Buffer + Status Line Updates

Claude Code probably:
1. Writes status line at bottom
2. Generates content (pushes status up)
3. Writes new status line at bottom
4. Old status remains in scrollback buffer
5. Both visible when scrolling

**Problem**: xterm.js scrollback (10000 lines) keeps old status lines

**Fix**: Reduce scrollback OR ensure status lines are properly overwritten

### Theory 3: ANSI Sequence Handling

Claude Code might use cursor positioning to update status in-place:
```
\r         # Carriage return to line start
\x1b[K     # Clear to end of line
New text   # Write new status
```

If term-wrapper doesn't handle these correctly, old text remains visible.

**Fix**: Ensure xterm.js properly handles line clearing sequences

## Proposed Fixes

### Fix 1: Prevent Page Body Scrolling (HIGH PRIORITY)

**Issue**: User sees TWO scrollbars

**Change**: Add to CSS:
```css
html, body {
    overflow: hidden !important;
    position: fixed;
    width: 100%;
    height: 100%;
}

#terminal-container {
    overflow: auto;  /* Change from hidden to auto */
}
```

**Rationale**: Ensure ONLY the terminal scrolls, not the page

### Fix 2: Reduce Scrollback Buffer (MEDIUM PRIORITY)

**Issue**: Old status lines remain in scrollback

**Change**: In `app.js`:
```javascript
scrollback: 1000,  // Reduce from 10000 to 1000
```

**Rationale**: Reduce chance of old status lines being visible

### Fix 3: Disable Alternative Screen Buffer (TEST)

**Issue**: Claude Code might expect alternate screen buffer

**Change**: In `app.js`:
```javascript
this.term = new Terminal({
    ...
    altClickMovesCursor: false,
    allowProposedApi: true,
});
```

Then enable:
```javascript
this.term.options.altClickMovesCursor = false;
```

**Rationale**: Ensure alternate screen works like normal terminal

### Fix 4: Test with Minimal Config

**Create minimal test case**:
```javascript
// Bare minimum xterm.js config
const term = new Terminal({
    rows: 24,
    cols: 80,
    scrollback: 1000
});
```

Test if duplication still occurs.

## Testing Strategy

### Test 1: Check for Double Scrollbar
1. Open on mobile (or mobile viewport)
2. Look for scrollbars on:
   - Page body (html/body element)
   - Terminal container (#terminal-container)
   - xterm.js viewport (.xterm-viewport)
3. Only ONE should be visible (terminal's)

### Test 2: Reproduce Duplication
1. Run Claude Code
2. Generate long output
3. During "Grooving..." phase, take screenshot
4. Count how many "Grooving..." messages visible
5. Should be: 1 (not 2+)

### Test 3: Test in Regular Terminal
1. Run same command in normal terminal (not term-wrapper)
2. Verify no duplication
3. Compare ANSI output sequences

### Test 4: ANSI Sequence Analysis
1. Capture raw PTY output during Claude generation
2. Check for cursor positioning and line clearing sequences
3. Verify xterm.js handles them correctly

## Implementation Order

1. **FIX 1** - Prevent page body scrolling (CSS change)
2. **TEST 1** - Verify only one scrollbar
3. **TEST 2** - Check if duplication fixed
4. If not fixed → **FIX 2** - Reduce scrollback
5. If still not fixed → **FIX 3** - Alternate screen buffer
6. If still not fixed → **TEST 3** + **TEST 4** - Deep ANSI analysis

## Expected Outcome

After fixes:
- ✅ Only ONE scrollbar (terminal's)
- ✅ Only ONE thinking indicator visible at a time
- ✅ Touch scrolling works correctly
- ✅ Behavior matches normal terminal
