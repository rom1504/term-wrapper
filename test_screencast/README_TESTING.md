# Testing Documentation for v0.6.5 Scroll Fix

## Quick Links

- **[TESTING_SUMMARY_V0.6.5.md](TESTING_SUMMARY_V0.6.5.md)** - START HERE! Overview of what was done and what you need to do
- **[COMPREHENSIVE_TESTING_STRATEGY.md](COMPREHENSIVE_TESTING_STRATEGY.md)** - Detailed manual testing guide
- **[V0.6.5_VERIFICATION_REPORT.md](V0.6.5_VERIFICATION_REPORT.md)** - Code verification results

## Files in This Directory

### Documentation
- `TESTING_SUMMARY_V0.6.5.md` - Executive summary of testing status
- `COMPREHENSIVE_TESTING_STRATEGY.md` - Full testing strategy with research references
- `V0.6.5_VERIFICATION_REPORT.md` - Detailed code verification report
- `ROOT_CAUSE_ANALYSIS.md` - Analysis of thinking indicator duplication issue
- `DUPLICATION_FOUND.md` - Evidence of duplication from frame analysis
- `AFTER_FIX_ANALYSIS.md` - Analysis after v0.6.2 fixes
- `FIX_PLAN.md` - Initial fix planning document

### Scripts
- `verify_code_changes.sh` - Quick automated verification (EXECUTABLE)
- `comprehensive_scroll_test.py` - Multi-device automated testing (requires Playwright)
- `verify_scroll_fix.py` - Single test verification (requires Playwright)
- `manual_scroll_test.html` - Browser-based manual test page
- `debug_ansi_sequences.py` - Capture raw ANSI output from Claude
- `analyze_frames.py` - Frame-by-frame video analysis
- `screencast_mobile_scroll.py` - Original mobile scroll test

### Test Data
- `analysis_frame_*.png` - Frame-by-frame screenshots (45 frames)
- `claude_ansi_output.txt` - Raw ANSI sequences captured
- `claude_screen_output.txt` - Parsed screen buffer
- `frame_analysis*.log` - Frame analysis results

## Quick Verification

Run this to verify v0.6.5 is deployed correctly:

```bash
cd /home/ai/term_wrapper/test_screencast
./verify_code_changes.sh
```

Expected output:
```
✅ PASS: Version is 0.6.5
✅ PASS: Variable speed code found
✅ PASS: Fast multiplier (12) found
✅ PASS: Medium multiplier (8) found
✅ PASS: Slow multiplier (5) found
✅ PASS: Old code removed
```

## Manual Testing

1. **Start terminal**:
   ```bash
   term-wrapper web bash -c 'seq 1 1000'
   ```

2. **Open in mobile browser** on Xiaomi 13

3. **Verify version** shows "v0.6.5" in top left
   - If not, hard refresh: Ctrl+Shift+R

4. **Test scrolling**:
   - Slow drag → Should scroll ~5 lines per 50px
   - Medium swipe → Should scroll ~8 lines per 50px
   - Fast flick → Should scroll ~12 lines per 50px

5. **Report results**:
   - Is it faster than v0.6.4?
   - Does variable speed work?
   - Any issues?

## If Still Slow

1. Check version in browser (should be v0.6.5)
2. Hard refresh browser (Ctrl+Shift+R)
3. Clear browser cache completely
4. Kill old servers: `pkill -f term_wrapper.server`
5. Check browser console for errors (F12)

## Research References

Testing strategy based on 2025 best practices:

- [Playwright Mobile Testing - AlphaBin](https://www.alphabin.co/blog/using-playwright-for-mobile-web-testing)
- [xterm.js Touch Issues - GitHub #5377](https://github.com/xtermjs/xterm.js/issues/5377)
- [Device Emulation - Playwright Docs](https://playwright.dev/docs/emulation)
- [Mobile Testing Guide - Qualiti](https://www.qualiti.ai/playwright-test-automation/playwright-mobile-testing)
- [Emulating Mobile Devices - Checkly](https://www.checklyhq.com/docs/learn/playwright/emulating-mobile-devices/)

## Key Findings from Research

1. **xterm.js has limited mobile touch support** (GitHub #5377, July 2025)
   - Our custom implementation was necessary
   - Touch scrolling doesn't work well out-of-the-box

2. **Device emulation != real device testing**
   - Emulation good for CI/CD and quick checks
   - Real device testing essential for production
   - Must test on actual Xiaomi 13

3. **Variable speed is best practice**
   - Natural feel - faster swipe = faster scroll
   - Improves mobile UX significantly
   - Velocity-based multipliers are standard

## Code Changes (v0.6.5)

**Old behavior** (v0.6.4):
```javascript
const scrollAmount = Math.round(diff / 50 * 3);  // Fixed multiplier
```

**New behavior** (v0.6.5):
```javascript
const velocity = Math.abs(diff);
let multiplier;
if (velocity > 15) multiplier = 12;      // Very fast
else if (velocity > 8) multiplier = 8;   // Fast
else multiplier = 5;                     // Slow
const scrollAmount = Math.round(diff / 50 * multiplier);
```

**Result**:
- Slow swipe: +67% faster (5 vs 3 lines/50px)
- Medium swipe: +167% faster (8 vs 3)
- Fast swipe: +300% faster (12 vs 3)

## Automated Testing (Requires Dependencies)

The comprehensive test suite needs Playwright and libcairo.so.2:

```bash
# Install Playwright
pip install playwright
playwright install chromium

# Install system dependencies
sudo apt-get install libcairo2

# Run tests
python3 comprehensive_scroll_test.py
```

This will test on:
- iPhone 13 (390x844)
- Xiaomi 13 Android (414x896)
- Samsung Galaxy S21 (360x800)
- iPad Pro (1024x1366)

And capture:
- Screenshots at different scroll positions
- Velocity measurements
- Scroll distance calculations
- Cross-device consistency checks

## Test Output

Automated tests (when working) generate:
- `scroll_test_output/` directory
- Screenshots: `*_initial.png`, `*_slow_drag.png`, etc.
- Scroll sequences: `*_sequence_*.png`
- Summary report with cross-device comparison

## Contributing

To add new tests:

1. Create test script in this directory
2. Document in README_TESTING.md
3. Update COMPREHENSIVE_TESTING_STRATEGY.md if needed
4. Commit with descriptive message

## Version History

- **v0.6.5** - Variable speed scrolling (5/8/12 multipliers)
- **v0.6.4** - Version display added
- **v0.6.3** - Auto-scroll + ANSI filtering
- **v0.6.2** - Double scrollbar fix, scrollback reduction
- **v0.6.1** - Touch scroll direction fix
- **v0.6.0** - One-command workflow, Enter button, touch improvements

## Contact

If you find issues or have questions about testing:
- Check existing documentation first
- Run `verify_code_changes.sh` to confirm deployment
- Test on real device (most important!)
- Report specific observations (slow/fast, responsive/laggy, etc.)
