/**
 * Unit tests for scrolling logic
 */

import {
    isAlternateBuffer,
    calculateWheelScroll,
    calculateTouchScroll,
    getArrowKeySequence,
    generateArrowKeys,
    shouldTriggerScroll,
    determineScrollAction
} from '../term_wrapper/frontend/scrolling.js';

describe('isAlternateBuffer', () => {
    test('returns true for alternate buffer', () => {
        const buffer = { type: 'alternate' };
        expect(isAlternateBuffer(buffer)).toBe(true);
    });

    test('returns false for normal buffer', () => {
        const buffer = { type: 'normal' };
        expect(isAlternateBuffer(buffer)).toBe(false);
    });

    test('returns false for null buffer', () => {
        expect(isAlternateBuffer(null)).toBe(false);
    });

    test('returns false for undefined buffer', () => {
        expect(isAlternateBuffer(undefined)).toBe(false);
    });
});

describe('calculateWheelScroll', () => {
    test('calculates scroll down (positive delta)', () => {
        const result = calculateWheelScroll(100);
        expect(result.lines).toBe(3); // ceil(100/40) = 3
        expect(result.direction).toBe('down');
    });

    test('calculates scroll up (negative delta)', () => {
        const result = calculateWheelScroll(-120);
        expect(result.lines).toBe(3); // ceil(120/40) = 3
        expect(result.direction).toBe('up');
    });

    test('uses custom pixels per line', () => {
        const result = calculateWheelScroll(100, 50);
        expect(result.lines).toBe(2); // ceil(100/50) = 2
    });

    test('handles small deltas', () => {
        const result = calculateWheelScroll(10);
        expect(result.lines).toBe(1); // ceil(10/40) = 1
    });

    test('handles zero delta', () => {
        const result = calculateWheelScroll(0);
        expect(result.lines).toBe(0);
    });
});

describe('calculateTouchScroll', () => {
    test('calculates scroll up (positive delta = swipe up)', () => {
        const result = calculateTouchScroll(50);
        expect(result.lines).toBe(2); // floor(50/20) = 2
        expect(result.direction).toBe('up');
    });

    test('calculates scroll down (negative delta = swipe down)', () => {
        const result = calculateTouchScroll(-60);
        expect(result.lines).toBe(3); // floor(60/20) = 3
        expect(result.direction).toBe('down');
    });

    test('uses custom pixels per line', () => {
        const result = calculateTouchScroll(50, 25);
        expect(result.lines).toBe(2); // floor(50/25) = 2
    });

    test('handles small deltas (no scroll)', () => {
        const result = calculateTouchScroll(15);
        expect(result.lines).toBe(0); // floor(15/20) = 0
    });

    test('handles zero delta', () => {
        const result = calculateTouchScroll(0);
        expect(result.lines).toBe(0);
    });
});

describe('getArrowKeySequence', () => {
    test('returns up arrow escape sequence', () => {
        expect(getArrowKeySequence('up')).toBe('\x1b[A');
    });

    test('returns down arrow escape sequence', () => {
        expect(getArrowKeySequence('down')).toBe('\x1b[B');
    });
});

describe('generateArrowKeys', () => {
    test('generates multiple up arrow keys', () => {
        const result = generateArrowKeys('up', 3);
        expect(result).toEqual(['\x1b[A', '\x1b[A', '\x1b[A']);
        expect(result.length).toBe(3);
    });

    test('generates multiple down arrow keys', () => {
        const result = generateArrowKeys('down', 2);
        expect(result).toEqual(['\x1b[B', '\x1b[B']);
        expect(result.length).toBe(2);
    });

    test('caps at maxKeys (default 5)', () => {
        const result = generateArrowKeys('up', 10);
        expect(result.length).toBe(5); // capped at 5
    });

    test('respects custom maxKeys', () => {
        const result = generateArrowKeys('down', 10, 3);
        expect(result.length).toBe(3);
    });

    test('returns empty array for zero count', () => {
        const result = generateArrowKeys('up', 0);
        expect(result).toEqual([]);
    });
});

describe('shouldTriggerScroll', () => {
    test('returns true when delta exceeds threshold', () => {
        expect(shouldTriggerScroll(25, 20)).toBe(true);
        expect(shouldTriggerScroll(-25, 20)).toBe(true);
    });

    test('returns true when delta equals threshold', () => {
        expect(shouldTriggerScroll(20, 20)).toBe(true);
    });

    test('returns false when delta below threshold', () => {
        expect(shouldTriggerScroll(15, 20)).toBe(false);
        expect(shouldTriggerScroll(-15, 20)).toBe(false);
    });

    test('returns false for zero delta', () => {
        expect(shouldTriggerScroll(0, 20)).toBe(false);
    });
});

describe('determineScrollAction', () => {
    describe('alternate buffer', () => {
        const alternateBuffer = { type: 'alternate' };

        test('wheel scroll down generates arrow keys', () => {
            const result = determineScrollAction(alternateBuffer, 100, 'wheel');
            expect(result.action).toBe('arrow-keys');
            expect(result.data).toEqual(['\x1b[B', '\x1b[B', '\x1b[B']); // 3 down keys
        });

        test('wheel scroll up generates arrow keys', () => {
            const result = determineScrollAction(alternateBuffer, -100, 'wheel');
            expect(result.action).toBe('arrow-keys');
            expect(result.data).toEqual(['\x1b[A', '\x1b[A', '\x1b[A']); // 3 up keys
        });

        test('touch swipe up generates arrow keys', () => {
            const result = determineScrollAction(alternateBuffer, 50, 'touch');
            expect(result.action).toBe('arrow-keys');
            expect(result.data).toEqual(['\x1b[A', '\x1b[A']); // 2 up keys
        });

        test('touch swipe down generates arrow keys', () => {
            const result = determineScrollAction(alternateBuffer, -60, 'touch');
            expect(result.action).toBe('arrow-keys');
            expect(result.data).toEqual(['\x1b[B', '\x1b[B', '\x1b[B']); // 3 down keys
        });

        test('zero delta returns none action', () => {
            const result = determineScrollAction(alternateBuffer, 0, 'wheel');
            expect(result.action).toBe('none');
        });
    });

    describe('normal buffer', () => {
        const normalBuffer = { type: 'normal' };

        test('wheel scroll down uses term-scroll', () => {
            const result = determineScrollAction(normalBuffer, 100, 'wheel');
            expect(result.action).toBe('term-scroll');
            expect(result.data).toBe(3); // positive = scroll down
        });

        test('wheel scroll up uses term-scroll', () => {
            const result = determineScrollAction(normalBuffer, -100, 'wheel');
            expect(result.action).toBe('term-scroll');
            expect(result.data).toBe(-3); // negative = scroll up
        });

        test('touch swipe up uses term-scroll', () => {
            const result = determineScrollAction(normalBuffer, 50, 'touch');
            expect(result.action).toBe('term-scroll');
            expect(result.data).toBe(-2); // negative = scroll up
        });

        test('touch swipe down uses term-scroll', () => {
            const result = determineScrollAction(normalBuffer, -60, 'touch');
            expect(result.action).toBe('term-scroll');
            expect(result.data).toBe(3); // positive = scroll down
        });

        test('zero delta returns none action', () => {
            const result = determineScrollAction(normalBuffer, 0, 'wheel');
            expect(result.action).toBe('none');
        });
    });

    describe('edge cases', () => {
        test('null buffer returns none action', () => {
            const result = determineScrollAction(null, 100, 'wheel');
            expect(result.action).toBe('term-scroll'); // null treated as normal
        });

        test('small delta below line threshold returns none', () => {
            const alternateBuffer = { type: 'alternate' };
            const result = determineScrollAction(alternateBuffer, 10, 'touch');
            expect(result.action).toBe('none'); // 10px / 20 = 0 lines
        });
    });
});
