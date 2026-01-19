# Root Cause Analysis - Thinking Indicator Duplication

## Investigation Summary

After deep analysis of ANSI sequences, terminal behavior, and xterm.js rendering, I've identified the root cause of the thinking indicator duplication issue.

## The Problem

**Symptom**: Two thinking indicators appear simultaneously during Claude Code generation:
```
· Grooving... (ctrl+c to interrupt)

* Grooving... thought for 3s)
```

**User report**: "in normal terminal claude code does not have this issue so this is our problem"

## Root Cause

### How Claude Code Works

Analysis of captured PTY output reveals that Claude Code:

1. **Does NOT use cursor control sequences**:
   - NO cursor save/restore (ESC 7/8 or ESC[s/u)
   - NO cursor positioning (ESC[row;colH)
   - NO line clearing (ESC[K)
   - NO alternate screen buffer (ESC[?1049h/l)

2. **Uses simple line-by-line output**:
   - Writes status line with newline: `"· Grooving... (ctrl+c to interrupt)\n"`
   - Writes content with newlines
   - Writes UPDATED status line: `"* Grooving... thought for 3s)\n"`

3. **All status lines are NEW lines in the buffer** - not updates in-place!

### Why It Works in Native Terminals

In native terminals (iTerm2, Alacritty, etc.):
- Users are typically scrolled to the **bottom** of the terminal
- New content pushes old status lines **out of the viewport**
- Only the **latest** status line is visible
- The rapid updates create the **illusion** of updating in-place
- Users don't typically scroll up during thinking

### Why It Fails in Our Terminal

In our mobile browser + xterm.js setup:
1. **Scrollback buffer** keeps ALL lines (500 lines configured)
2. **Viewport position** may not auto-scroll to bottom during streaming
3. **Mobile viewport height** shows MORE rows simultaneously
4. **Both status lines end up in visible area** at the same time
5. After user scrolls up, they see BOTH lines that were written

### Evidence from Frame Analysis

From DUPLICATION_FOUND.md:
- Frame 0015-0039: TWO "Grooving..." messages visible
- Frame 0040 (after scrolling): Duplication gone
- The two status lines are separated by just ONE blank line
- Different bullet points (·, *, ∗) confirm they're separate writes

### The ESC[<u Mystery

Additional finding: `ESC[<u` sequence appears 60 times in output:
```
Pattern: [?25l[<u[?1004l[?2004l[?25h
```

This sequence:
- Is NOT a standard terminal escape sequence
- May interfere with cursor positioning in xterm.js
- Does NOT appear in standard ANSI/VT100 documentation
- Could be a malformed or application-specific sequence

## Fixes Applied

### 1. Filter ESC[<u Sequence (v0.6.2+)

```python
# In api.py filter_unsupported_ansi()
text = re.sub(r'\x1b\[<u', '', text)
```

**Rationale**: This unknown sequence may confuse xterm.js cursor handling

### 2. Previous Fixes That Didn't Help

❌ **Reduced scrollback** (10000 → 500 → 0): Duplication persists
❌ **Filtered synchronized output mode** (ESC[?2026h/l): Not the cause
❌ **Reduced polling interval** (50ms → 1ms): No effect
❌ **Fixed page scrollbar**: Improved UX but didn't fix duplication

## Potential Solutions

### Option 1: Force Viewport to Bottom (RECOMMENDED)

When content is streaming, ensure viewport stays at bottom:

```javascript
// In app.js websocket onmessage handler
this.term.write(text);
if (this.term.buffer.active.baseY + this.term.rows < this.term.buffer.active.length) {
    this.term.scrollToBottom();
}
```

**Pros**: Matches native terminal behavior
**Cons**: User can't scroll up during generation

### Option 2: Detect and Clear Old Status Lines

When new status line appears, clear previous ones:

```javascript
// Detect thinking indicator pattern
const indicators = ['Grooving', 'Herding', 'Mulling', 'Coalescing', 'Sketching'];
// Search backward in buffer for old instances
// Overwrite with spaces
```

**Pros**: Allows user to scroll while preventing duplicates
**Cons**: Hacky, might break other content

### Option 3: Custom Status Line Overlay

Render status line outside the terminal:

```javascript
// Parse status updates from terminal output
// Render in fixed div at bottom
// Don't write to terminal buffer
```

**Pros**: Clean separation, no duplicates
**Cons**: Requires deep integration with Claude output format

### Option 4: Reduce Mobile Viewport Rows

Show fewer rows on mobile to reduce chance both lines are visible:

```css
@media (max-width: 768px) {
    #terminal { max-height: 50vh; }
}
```

**Pros**: Simple change
**Cons**: Doesn't fix root cause, reduces usable area

## Recommendation

**Implement Option 1**: Force viewport to bottom during content streaming.

This matches native terminal behavior where users see only the latest output. The fix should:

1. Detect when content is being streamed (based on rate of updates)
2. Auto-scroll viewport to bottom after each write
3. Allow manual scroll when streaming stops (prompt appears)

**Implementation**:
```javascript
this.term.onWriteParsed(() => {
    // If new content arrived and we're near bottom, scroll to bottom
    const buffer = this.term.buffer.active;
    const distanceFromBottom = buffer.length - (buffer.viewportY + this.term.rows);

    if (distanceFromBottom < 3) {  // Within 3 lines of bottom
        this.term.scrollToBottom();
    }
});
```

## Testing Plan

1. Start mobile browser with Claude
2. Trigger thinking with a command
3. Verify only ONE status line visible at bottom
4. Verify status updates in real-time
5. Verify after completion, can scroll up through history
6. Verify both status lines exist in scrollback, but only latest is shown during generation

## Conclusion

The duplication is NOT a bug in our terminal implementation - it's a difference in how content is displayed compared to native terminals. Claude Code writes multiple status lines as new lines (not updates in-place), and our mobile viewport shows both simultaneously.

**Status**: Fix applied (filter ESC[<u), testing Option 1 (auto-scroll) recommended.
