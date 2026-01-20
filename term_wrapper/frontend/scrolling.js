/**
 * Scrolling logic for terminal wrapper
 * Extracted for testing purposes
 */

/**
 * Check if buffer is in alternate mode (used by vim, Claude Code, etc.)
 * @param {Object} buffer - Terminal buffer object with 'type' property
 * @returns {boolean} True if alternate buffer
 */
export function isAlternateBuffer(buffer) {
    return !!(buffer && buffer.type === 'alternate');
}

/**
 * Calculate number of lines to scroll from wheel delta
 * @param {number} deltaY - Wheel event deltaY value
 * @param {number} pixelsPerLine - Pixels per line threshold (default 40)
 * @returns {Object} {lines: number, direction: 'up'|'down'}
 */
export function calculateWheelScroll(deltaY, pixelsPerLine = 40) {
    const lines = Math.ceil(Math.abs(deltaY) / pixelsPerLine);
    const direction = deltaY < 0 ? 'up' : 'down';
    return { lines, direction };
}

/**
 * Calculate number of lines to scroll from touch delta
 * @param {number} deltaY - Touch deltaY (difference from last touch position)
 * @param {number} pixelsPerLine - Pixels per line threshold (default 20)
 * @returns {Object} {lines: number, direction: 'up'|'down'}
 */
export function calculateTouchScroll(deltaY, pixelsPerLine = 20) {
    const lines = Math.floor(Math.abs(deltaY) / pixelsPerLine);
    const direction = deltaY > 0 ? 'up' : 'down'; // Swipe up = scroll up
    return { lines, direction };
}

/**
 * Generate arrow key escape sequence
 * @param {'up'|'down'} direction - Scroll direction
 * @returns {string} Escape sequence (\x1b[A for up, \x1b[B for down)
 */
export function getArrowKeySequence(direction) {
    return direction === 'up' ? '\x1b[A' : '\x1b[B';
}

/**
 * Generate multiple arrow key sequences
 * @param {'up'|'down'} direction - Scroll direction
 * @param {number} count - Number of arrow keys to generate
 * @param {number} maxKeys - Maximum keys to generate (default 5)
 * @returns {string[]} Array of escape sequences
 */
export function generateArrowKeys(direction, count, maxKeys = 5) {
    const key = getArrowKeySequence(direction);
    const actualCount = Math.min(count, maxKeys);
    return Array(actualCount).fill(key);
}

/**
 * Check if touch gesture meets threshold to trigger scroll
 * @param {number} totalDelta - Total delta from touch start
 * @param {number} threshold - Minimum threshold (default 20)
 * @returns {boolean} True if gesture should trigger scroll
 */
export function shouldTriggerScroll(totalDelta, threshold = 20) {
    return Math.abs(totalDelta) >= threshold;
}

/**
 * Determine scroll behavior based on buffer type and event
 * @param {Object} buffer - Terminal buffer object
 * @param {number} deltaY - Scroll delta
 * @param {'wheel'|'touch'} eventType - Type of scroll event
 * @returns {Object} {action: 'arrow-keys'|'term-scroll'|'none', data: any}
 */
export function determineScrollAction(buffer, deltaY, eventType) {
    if (!deltaY || deltaY === 0) {
        return { action: 'none' };
    }

    const isAlternate = isAlternateBuffer(buffer);

    if (isAlternate) {
        // In alternate buffer: send arrow keys
        const scrollCalc = eventType === 'wheel'
            ? calculateWheelScroll(deltaY)
            : calculateTouchScroll(deltaY);

        if (scrollCalc.lines > 0) {
            const keys = generateArrowKeys(scrollCalc.direction, scrollCalc.lines);
            return { action: 'arrow-keys', data: keys };
        }
    } else {
        // In normal buffer: use terminal scrolling
        const scrollCalc = eventType === 'wheel'
            ? calculateWheelScroll(deltaY)
            : calculateTouchScroll(deltaY);

        if (scrollCalc.lines > 0) {
            const scrollLines = scrollCalc.direction === 'up' ? -scrollCalc.lines : scrollCalc.lines;
            return { action: 'term-scroll', data: scrollLines };
        }
    }

    return { action: 'none' };
}
