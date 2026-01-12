#!/usr/bin/env python3
"""Simple TUI app for testing terminal wrapper."""

import sys
import termios
import tty

def main():
    # Print header
    print("\033[2J\033[H")  # Clear screen
    print("=" * 40)
    print("  Terminal Wrapper Test App")
    print("=" * 40)
    print()

    counter = 0
    print(f"Counter: {counter}")
    print()
    print("Controls:")
    print("  + : increment")
    print("  - : decrement")
    print("  r : reset")
    print("  q : quit")
    print()

    # Set terminal to raw mode
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())

        while True:
            char = sys.stdin.read(1)

            if char == 'q':
                break
            elif char == '+':
                counter += 1
            elif char == '-':
                counter -= 1
            elif char == 'r':
                counter = 0
            else:
                continue

            # Update display
            print(f"\r\033[K\033[5ACounter: {counter}\033[5B", end='', flush=True)

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\nGoodbye!")

if __name__ == "__main__":
    main()
