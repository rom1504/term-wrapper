"""
Terminal screen buffer for rendering terminal output with ANSI escape sequences.

This module provides a virtual terminal screen that tracks cursor positioning,
character rendering, and ANSI escape codes to produce a 2D grid representation
of what would appear on a real terminal screen.
"""

import re
from typing import List, Tuple, Optional


class ScreenBuffer:
    """
    Virtual terminal screen buffer that processes ANSI escape sequences
    and maintains a 2D grid of characters.

    This allows parsing complex TUI applications like htop, vim, etc. that
    use cursor positioning and screen updates.
    """

    def __init__(self, rows: int, cols: int):
        """
        Initialize screen buffer.

        Args:
            rows: Number of rows (height)
            cols: Number of columns (width)
        """
        self.rows = rows
        self.cols = cols
        self.cursor_row = 0
        self.cursor_col = 0
        self.screen: List[List[str]] = [[' ' for _ in range(cols)] for _ in range(rows)]

    def clear(self):
        """Clear the entire screen."""
        self.screen = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.cursor_row = 0
        self.cursor_col = 0

    def clear_line(self, row: Optional[int] = None):
        """Clear a line from cursor to end."""
        if row is None:
            row = self.cursor_row
        if 0 <= row < self.rows:
            for col in range(self.cursor_col, self.cols):
                self.screen[row][col] = ' '

    def clear_line_from_start(self, row: Optional[int] = None):
        """Clear a line from start to cursor."""
        if row is None:
            row = self.cursor_row
        if 0 <= row < self.rows:
            for col in range(0, min(self.cursor_col + 1, self.cols)):
                self.screen[row][col] = ' '

    def clear_entire_line(self, row: Optional[int] = None):
        """Clear entire line."""
        if row is None:
            row = self.cursor_row
        if 0 <= row < self.rows:
            self.screen[row] = [' ' for _ in range(self.cols)]

    def write_char(self, char: str):
        """
        Write a character at current cursor position and advance cursor.

        Args:
            char: Single character to write
        """
        if char == '\n':
            self.cursor_row += 1
            self.cursor_col = 0
        elif char == '\r':
            self.cursor_col = 0
        elif char == '\t':
            # Tab to next 8-column boundary
            self.cursor_col = ((self.cursor_col // 8) + 1) * 8
        elif char == '\b':
            # Backspace
            if self.cursor_col > 0:
                self.cursor_col -= 1
        else:
            # Regular character
            if 0 <= self.cursor_row < self.rows and 0 <= self.cursor_col < self.cols:
                self.screen[self.cursor_row][self.cursor_col] = char
            self.cursor_col += 1

        # Handle cursor overflow
        if self.cursor_col >= self.cols:
            self.cursor_col = 0
            self.cursor_row += 1

        # Clamp cursor to screen bounds (don't scroll beyond)
        if self.cursor_row >= self.rows:
            self.cursor_row = self.rows - 1

    def move_cursor(self, row: int, col: int):
        """
        Move cursor to absolute position (0-indexed).

        Args:
            row: Row position (0-indexed)
            col: Column position (0-indexed)
        """
        self.cursor_row = max(0, min(row, self.rows - 1))
        self.cursor_col = max(0, min(col, self.cols - 1))

    def move_cursor_relative(self, row_delta: int, col_delta: int):
        """
        Move cursor relative to current position.

        Args:
            row_delta: Rows to move (negative for up, positive for down)
            col_delta: Columns to move (negative for left, positive for right)
        """
        new_row = self.cursor_row + row_delta
        new_col = self.cursor_col + col_delta
        self.move_cursor(new_row, new_col)

    def process_ansi_escape(self, sequence: str) -> bool:
        """
        Process a single ANSI escape sequence.

        Args:
            sequence: ANSI escape sequence (without the ESC character)

        Returns:
            True if sequence was handled, False otherwise
        """
        # CSI sequences: ESC [ ... letter
        if sequence.startswith('['):
            csi_body = sequence[1:]

            # Cursor position: ESC [ row ; col H or ESC [ row ; col f
            if csi_body.endswith('H') or csi_body.endswith('f'):
                parts = csi_body[:-1].split(';')
                row = int(parts[0]) - 1 if len(parts) > 0 and parts[0] else 0
                col = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else 0
                self.move_cursor(row, col)
                return True

            # Cursor up: ESC [ n A
            if csi_body.endswith('A'):
                n = int(csi_body[:-1]) if csi_body[:-1] else 1
                self.move_cursor_relative(-n, 0)
                return True

            # Cursor down: ESC [ n B
            if csi_body.endswith('B'):
                n = int(csi_body[:-1]) if csi_body[:-1] else 1
                self.move_cursor_relative(n, 0)
                return True

            # Cursor forward: ESC [ n C
            if csi_body.endswith('C'):
                n = int(csi_body[:-1]) if csi_body[:-1] else 1
                self.move_cursor_relative(0, n)
                return True

            # Cursor backward: ESC [ n D
            if csi_body.endswith('D'):
                n = int(csi_body[:-1]) if csi_body[:-1] else 1
                self.move_cursor_relative(0, -n)
                return True

            # Clear screen: ESC [ 2 J
            if csi_body == '2J':
                self.clear()
                return True

            # Clear from cursor to end of screen: ESC [ 0 J or ESC [ J
            if csi_body == 'J' or csi_body == '0J':
                # Clear from cursor to end of current line
                self.clear_line()
                # Clear all lines below
                for row in range(self.cursor_row + 1, self.rows):
                    self.screen[row] = [' ' for _ in range(self.cols)]
                return True

            # Clear from cursor to end of line: ESC [ K or ESC [ 0 K
            if csi_body == 'K' or csi_body == '0K':
                self.clear_line()
                return True

            # Clear from beginning of line to cursor: ESC [ 1 K
            if csi_body == '1K':
                self.clear_line_from_start()
                return True

            # Clear entire line: ESC [ 2 K
            if csi_body == '2K':
                self.clear_entire_line()
                return True

            # Save cursor position: ESC [ s
            if csi_body == 's':
                self.saved_cursor = (self.cursor_row, self.cursor_col)
                return True

            # Restore cursor position: ESC [ u
            if csi_body == 'u':
                if hasattr(self, 'saved_cursor'):
                    self.cursor_row, self.cursor_col = self.saved_cursor
                return True

            # Ignore color/style sequences (SGR): ESC [ ... m
            if csi_body.endswith('m'):
                return True

        return False

    def process_output(self, output: str):
        """
        Process raw terminal output and update screen buffer.

        Args:
            output: Raw terminal output with ANSI escape sequences
        """
        i = 0
        while i < len(output):
            char = output[i]

            # Check for ANSI escape sequence
            if char == '\x1b' and i + 1 < len(output):
                # Find the end of the escape sequence
                # ESC [ ... letter (CSI sequences)
                if output[i + 1] == '[':
                    # Find the final character (letter)
                    j = i + 2
                    while j < len(output) and output[j] in '0123456789;?':
                        j += 1
                    if j < len(output):
                        # Found complete sequence
                        sequence = output[i + 1:j + 1]
                        self.process_ansi_escape(sequence)
                        i = j + 1
                        continue

                # ESC ( ... (character set selection)
                elif output[i + 1] == '(':
                    i += 3  # Skip ESC ( X
                    continue

                # ESC = or ESC > (keypad mode)
                elif output[i + 1] in '=><':
                    i += 2
                    continue

                # ESC ? ... (DEC private mode)
                elif output[i + 1] == '?':
                    j = i + 2
                    while j < len(output) and output[j] not in 'hlH':
                        j += 1
                    i = j + 1 if j < len(output) else j
                    continue

                # Unknown escape sequence, skip 2 chars
                i += 2
                continue

            # Regular character
            self.write_char(char)
            i += 1

    def get_screen_lines(self) -> List[str]:
        """
        Get screen contents as list of strings (one per row).

        Returns:
            List of strings, one per row, with trailing spaces stripped
        """
        return [''.join(row).rstrip() for row in self.screen]

    def get_screen_text(self) -> str:
        """
        Get screen contents as a single string.

        Returns:
            Screen contents with newlines between rows
        """
        return '\n'.join(self.get_screen_lines())

    def __str__(self) -> str:
        """String representation of screen buffer."""
        return self.get_screen_text()
