/**
 * Integration tests for scrolling logic with mock WebSocket and terminal
 */

import { describe, test, expect, beforeEach, jest } from '@jest/globals';
import { TextEncoder, TextDecoder } from 'util';
import {
    determineScrollAction,
    isAlternateBuffer,
    generateArrowKeys,
    calculateWheelScroll,
    calculateTouchScroll,
} from '../term_wrapper/frontend/scrolling.js';

// Polyfill TextEncoder/TextDecoder for Node.js test environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

describe('Integration Tests - WebSocket Interaction', () => {
    let mockWs;
    let sentMessages;

    beforeEach(() => {
        sentMessages = [];
        mockWs = {
            readyState: 1, // OPEN
            send: jest.fn((data) => {
                const decoder = new TextDecoder();
                sentMessages.push(decoder.decode(data));
            })
        };
    });

    test('wheel scroll in alternate buffer sends correct arrow keys to WebSocket', () => {
        const alternateBuffer = { type: 'alternate' };
        const scrollAction = determineScrollAction(alternateBuffer, 120, 'wheel'); // 120px down

        expect(scrollAction.action).toBe('arrow-keys');

        // Simulate sending through WebSocket
        for (const key of scrollAction.data) {
            mockWs.send(new TextEncoder().encode(key));
        }

        // Should send 3 down arrow keys (120/40 = 3)
        expect(sentMessages.length).toBe(3);
        expect(sentMessages.every(msg => msg === '\x1b[B')).toBe(true);
    });

    test('touch swipe in alternate buffer sends correct arrow keys to WebSocket', () => {
        const alternateBuffer = { type: 'alternate' };
        const scrollAction = determineScrollAction(alternateBuffer, 50, 'touch'); // 50px swipe up

        expect(scrollAction.action).toBe('arrow-keys');

        // Simulate sending through WebSocket
        for (const key of scrollAction.data) {
            mockWs.send(new TextEncoder().encode(key));
        }

        // Should send 2 up arrow keys (50/20 = 2)
        expect(sentMessages.length).toBe(2);
        expect(sentMessages.every(msg => msg === '\x1b[A')).toBe(true);
    });

    test('normal buffer wheel scroll does not send WebSocket messages', () => {
        const normalBuffer = { type: 'normal' };
        const scrollAction = determineScrollAction(normalBuffer, 100, 'wheel');

        expect(scrollAction.action).toBe('term-scroll');
        expect(scrollAction.data).toBe(3); // 3 lines down

        // No WebSocket messages should be sent
        expect(sentMessages.length).toBe(0);
    });

    test('multiple rapid wheel scrolls accumulate correctly', () => {
        const alternateBuffer = { type: 'alternate' };

        // Simulate 5 rapid wheel events
        const events = [100, 80, 120, 60, 90]; // deltaY values

        for (const deltaY of events) {
            const scrollAction = determineScrollAction(alternateBuffer, deltaY, 'wheel');

            if (scrollAction.action === 'arrow-keys') {
                for (const key of scrollAction.data) {
                    mockWs.send(new TextEncoder().encode(key));
                }
            }
        }

        // Calculate expected total
        // 100/40=3, 80/40=2, 120/40=3, 60/40=2, 90/40=3 = 13 total
        expect(sentMessages.length).toBe(13);
        expect(sentMessages.every(msg => msg === '\x1b[B')).toBe(true); // All down
    });
});

describe('Touch Gesture Sequence Tests', () => {
    test('complete touch gesture: start -> move -> move -> end', () => {
        const alternateBuffer = { type: 'alternate' };
        let touchStartY = 100;
        let lastTouchY = 100;
        const totalKeys = [];

        // First move: 100 -> 150 (deltaY = 50, swipe up)
        let touchY = 150;
        let deltaY = touchY - lastTouchY;
        let scrollAction = determineScrollAction(alternateBuffer, deltaY, 'touch');

        if (scrollAction.action === 'arrow-keys') {
            totalKeys.push(...scrollAction.data);
        }
        lastTouchY = touchY;

        // Second move: 150 -> 180 (deltaY = 30, swipe up)
        touchY = 180;
        deltaY = touchY - lastTouchY;
        scrollAction = determineScrollAction(alternateBuffer, deltaY, 'touch');

        if (scrollAction.action === 'arrow-keys') {
            totalKeys.push(...scrollAction.data);
        }
        lastTouchY = touchY;

        // Third move: 180 -> 160 (deltaY = -20, swipe down)
        touchY = 160;
        deltaY = touchY - lastTouchY;
        scrollAction = determineScrollAction(alternateBuffer, deltaY, 'touch');

        if (scrollAction.action === 'arrow-keys') {
            totalKeys.push(...scrollAction.data);
        }
        lastTouchY = touchY;

        // Verify gesture was tracked
        // Move 1: 50/20 = 2 up arrows
        // Move 2: 30/20 = 1 up arrow
        // Move 3: 20/20 = 1 down arrow
        expect(totalKeys.length).toBe(4);
        expect(totalKeys.filter(k => k === '\x1b[A').length).toBe(3); // 3 up
        expect(totalKeys.filter(k => k === '\x1b[B').length).toBe(1); // 1 down
    });

    test('touch gesture with direction reversal', () => {
        const alternateBuffer = { type: 'alternate' };
        const keys = [];

        // Swipe up (deltaY > 0)
        let scrollAction = determineScrollAction(alternateBuffer, 60, 'touch');
        if (scrollAction.action === 'arrow-keys') {
            keys.push(...scrollAction.data);
        }

        // Swipe down (deltaY < 0)
        scrollAction = determineScrollAction(alternateBuffer, -60, 'touch');
        if (scrollAction.action === 'arrow-keys') {
            keys.push(...scrollAction.data);
        }

        // Should have both up and down arrows
        expect(keys.length).toBe(6); // 3 + 3
        expect(keys.slice(0, 3).every(k => k === '\x1b[A')).toBe(true); // First 3 are up
        expect(keys.slice(3, 6).every(k => k === '\x1b[B')).toBe(true); // Last 3 are down
    });

    test('touch gesture below threshold produces no scroll', () => {
        const alternateBuffer = { type: 'alternate' };

        // Small movements below threshold
        const smallDeltas = [5, 8, 12, 15, 18];
        const keys = [];

        for (const deltaY of smallDeltas) {
            const scrollAction = determineScrollAction(alternateBuffer, deltaY, 'touch');
            if (scrollAction.action === 'arrow-keys') {
                keys.push(...scrollAction.data);
            }
        }

        // None should produce scrolling (all < 20px threshold)
        expect(keys.length).toBe(0);
    });
});

describe('Buffer Type Transition Tests', () => {
    test('switching from alternate to normal buffer changes scroll behavior', () => {
        // Start in alternate buffer
        let buffer = { type: 'alternate' };
        let scrollAction = determineScrollAction(buffer, 100, 'wheel');
        expect(scrollAction.action).toBe('arrow-keys');

        // Switch to normal buffer
        buffer = { type: 'normal' };
        scrollAction = determineScrollAction(buffer, 100, 'wheel');
        expect(scrollAction.action).toBe('term-scroll');
        expect(scrollAction.data).toBe(3); // Positive for down
    });

    test('switching from normal to alternate buffer changes scroll behavior', () => {
        // Start in normal buffer
        let buffer = { type: 'normal' };
        let scrollAction = determineScrollAction(buffer, -80, 'wheel');
        expect(scrollAction.action).toBe('term-scroll');
        expect(scrollAction.data).toBe(-2); // Negative for up

        // Switch to alternate buffer
        buffer = { type: 'alternate' };
        scrollAction = determineScrollAction(buffer, -80, 'wheel');
        expect(scrollAction.action).toBe('arrow-keys');
        expect(scrollAction.data.length).toBe(2);
        expect(scrollAction.data.every(k => k === '\x1b[A')).toBe(true);
    });

    test('null buffer transitions to normal buffer behavior', () => {
        let buffer = null;
        let scrollAction = determineScrollAction(buffer, 100, 'wheel');
        expect(scrollAction.action).toBe('term-scroll');

        // Transition to alternate
        buffer = { type: 'alternate' };
        scrollAction = determineScrollAction(buffer, 100, 'wheel');
        expect(scrollAction.action).toBe('arrow-keys');
    });
});

describe('Boundary Value Tests', () => {
    test('extremely large positive deltaY is capped', () => {
        const alternateBuffer = { type: 'alternate' };
        const scrollAction = determineScrollAction(alternateBuffer, 10000, 'wheel');

        expect(scrollAction.action).toBe('arrow-keys');
        // 10000/40 = 250, but should be capped at maxKeys (5)
        expect(scrollAction.data.length).toBe(5);
    });

    test('extremely large negative deltaY is capped', () => {
        const alternateBuffer = { type: 'alternate' };
        const scrollAction = determineScrollAction(alternateBuffer, -10000, 'wheel');

        expect(scrollAction.action).toBe('arrow-keys');
        // Should be capped at maxKeys (5)
        expect(scrollAction.data.length).toBe(5);
        expect(scrollAction.data.every(k => k === '\x1b[A')).toBe(true); // Up arrows
    });

    test('exactly at line threshold produces 1 line scroll', () => {
        const alternateBuffer = { type: 'alternate' };

        // Wheel: exactly 40px
        let scrollAction = determineScrollAction(alternateBuffer, 40, 'wheel');
        expect(scrollAction.action).toBe('arrow-keys');
        expect(scrollAction.data.length).toBe(1);

        // Touch: exactly 20px
        scrollAction = determineScrollAction(alternateBuffer, 20, 'touch');
        expect(scrollAction.action).toBe('arrow-keys');
        expect(scrollAction.data.length).toBe(1);
    });

    test('just below line threshold produces correct scroll', () => {
        const alternateBuffer = { type: 'alternate' };

        // Wheel: 39px (just below 40)
        let scrollAction = determineScrollAction(alternateBuffer, 39, 'wheel');
        expect(scrollAction.action).toBe('arrow-keys');
        expect(scrollAction.data.length).toBe(1); // ceil(39/40) = 1

        // Touch: 19px (just below 20)
        scrollAction = determineScrollAction(alternateBuffer, 19, 'touch');
        expect(scrollAction.action).toBe('none'); // floor(19/20) = 0
    });

    test('fractional scroll values are handled correctly', () => {
        const alternateBuffer = { type: 'alternate' };

        // Wheel uses ceil, so any fraction rounds up
        const result1 = calculateWheelScroll(41); // 41/40 = 1.025
        expect(result1.lines).toBe(2); // ceil(1.025) = 2

        // Touch uses floor, so fractions round down
        const result2 = calculateTouchScroll(39); // 39/20 = 1.95
        expect(result2.lines).toBe(1); // floor(1.95) = 1
    });
});

describe('Performance and Rapid Fire Tests', () => {
    test('handles 100 rapid wheel events without error', () => {
        const alternateBuffer = { type: 'alternate' };
        const results = [];

        for (let i = 0; i < 100; i++) {
            const deltaY = (Math.random() * 200) - 100; // Random between -100 and 100
            const scrollAction = determineScrollAction(alternateBuffer, deltaY, 'wheel');
            results.push(scrollAction);
        }

        expect(results.length).toBe(100);
        expect(results.every(r => r.action !== undefined)).toBe(true);
    });

    test('handles 100 rapid touch events without error', () => {
        const alternateBuffer = { type: 'alternate' };
        const results = [];

        for (let i = 0; i < 100; i++) {
            const deltaY = (Math.random() * 100) - 50; // Random between -50 and 50
            const scrollAction = determineScrollAction(alternateBuffer, deltaY, 'touch');
            results.push(scrollAction);
        }

        expect(results.length).toBe(100);
        expect(results.every(r => r.action !== undefined)).toBe(true);
    });

    test('alternating wheel and touch events', () => {
        const alternateBuffer = { type: 'alternate' };
        const results = [];

        for (let i = 0; i < 50; i++) {
            // Alternate between wheel and touch
            const eventType = i % 2 === 0 ? 'wheel' : 'touch';
            const deltaY = 60;
            const scrollAction = determineScrollAction(alternateBuffer, deltaY, eventType);
            results.push(scrollAction);
        }

        expect(results.length).toBe(50);
        // All should produce arrow-keys
        expect(results.every(r => r.action === 'arrow-keys')).toBe(true);
    });

    test('zero deltaY events do not accumulate', () => {
        const alternateBuffer = { type: 'alternate' };
        const keys = [];

        // Send 50 zero-delta events
        for (let i = 0; i < 50; i++) {
            const scrollAction = determineScrollAction(alternateBuffer, 0, 'wheel');
            if (scrollAction.action === 'arrow-keys') {
                keys.push(...scrollAction.data);
            }
        }

        // Should produce no keys
        expect(keys.length).toBe(0);
    });
});
