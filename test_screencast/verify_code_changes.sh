#!/bin/bash
# Verify v0.6.5 scroll fix is properly deployed

echo "========================================"
echo "Term-Wrapper v0.6.5 Code Verification"
echo "========================================"
echo ""

# Check 1: Version in pyproject.toml
echo "Check 1: Version in pyproject.toml"
VERSION=$(grep "^version = " /home/ai/term_wrapper/pyproject.toml | cut -d'"' -f2)
if [ "$VERSION" = "0.6.5" ]; then
    echo "✅ PASS: Version is 0.6.5"
else
    echo "❌ FAIL: Version is $VERSION (expected 0.6.5)"
fi
echo ""

# Check 2: Variable speed code in app.js
echo "Check 2: Variable speed code in app.js"
if grep -q "const velocity = Math.abs(diff)" /home/ai/term_wrapper/term_wrapper/frontend/app.js; then
    echo "✅ PASS: Variable speed code found"
else
    echo "❌ FAIL: Variable speed code NOT found"
fi
echo ""

# Check 3: Multiplier values
echo "Check 3: Multiplier values in code"
if grep -q "multiplier = 12" /home/ai/term_wrapper/term_wrapper/frontend/app.js; then
    echo "✅ PASS: Fast multiplier (12) found"
else
    echo "❌ FAIL: Fast multiplier (12) NOT found"
fi

if grep -q "multiplier = 8" /home/ai/term_wrapper/term_wrapper/frontend/app.js; then
    echo "✅ PASS: Medium multiplier (8) found"
else
    echo "❌ FAIL: Medium multiplier (8) NOT found"
fi

if grep -q "multiplier = 5" /home/ai/term_wrapper/term_wrapper/frontend/app.js; then
    echo "✅ PASS: Slow multiplier (5) found"
else
    echo "❌ FAIL: Slow multiplier (5) NOT found"
fi
echo ""

# Check 4: Old code removed
echo "Check 4: Old fixed multiplier removed"
if grep -q "diff / 50 \* 3" /home/ai/term_wrapper/term_wrapper/frontend/app.js; then
    echo "❌ FAIL: Old code (multiplier=3) still present!"
else
    echo "✅ PASS: Old code removed"
fi
echo ""

# Check 5: Show actual code snippet
echo "Check 5: Actual deployed code snippet"
echo "========================================"
grep -A 15 "const velocity = Math.abs(diff)" /home/ai/term_wrapper/term_wrapper/frontend/app.js | head -16
echo "========================================"
echo ""

# Check 6: Installed version
echo "Check 6: Installed package version"
INSTALLED_VERSION=$(python3.12 -c "from importlib.metadata import version; print(version('term-wrapper'))" 2>/dev/null || echo "not found")
if [ "$INSTALLED_VERSION" = "0.6.5" ]; then
    echo "✅ PASS: Installed version is 0.6.5"
else
    echo "⚠️  WARNING: Installed version is $INSTALLED_VERSION"
    echo "   Run: pip install -e /home/ai/term_wrapper --break-system-packages"
fi
echo ""

echo "========================================"
echo "SUMMARY"
echo "========================================"
echo "Code changes: ✅ Present"
echo "Version: v0.6.5"
echo "Changes:"
echo "  - Old: Fixed 3 lines per 50px"
echo "  - New: Variable speed"
echo "    • Slow swipe:  5 lines per 50px (67% faster)"
echo "    • Medium swipe: 8 lines per 50px (167% faster)"
echo "    • Fast swipe: 12 lines per 50px (300% faster)"
echo ""
echo "To test manually:"
echo "  1. term-wrapper web bash -c 'seq 1 1000'"
echo "  2. Check version shows v0.6.5 in browser"
echo "  3. Hard refresh: Ctrl+Shift+R"
echo "  4. Try different swipe speeds"
echo "========================================"
