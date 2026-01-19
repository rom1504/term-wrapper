"""Tests for screen buffer module."""

import pytest
from term_wrapper.screen_buffer import ScreenBuffer


def test_screen_buffer_init():
    """Test screen buffer initialization."""
    buffer = ScreenBuffer(24, 80)
    assert buffer.rows == 24
    assert buffer.cols == 80
    assert buffer.cursor_row == 0
    assert buffer.cursor_col == 0
    assert len(buffer.screen) == 24
    assert len(buffer.screen[0]) == 80


def test_write_simple_text():
    """Test writing simple text."""
    buffer = ScreenBuffer(5, 20)
    buffer.process_output("Hello, World!")

    lines = buffer.get_screen_lines()
    assert lines[0] == "Hello, World!"
    assert buffer.cursor_row == 0
    assert buffer.cursor_col == 13


def test_write_with_newline():
    """Test writing text with newlines."""
    buffer = ScreenBuffer(5, 20)
    buffer.process_output("Line 1\nLine 2\nLine 3")

    lines = buffer.get_screen_lines()
    assert lines[0] == "Line 1"
    assert lines[1] == "Line 2"
    assert lines[2] == "Line 3"
    assert buffer.cursor_row == 2
    assert buffer.cursor_col == 6


def test_carriage_return():
    """Test carriage return."""
    buffer = ScreenBuffer(5, 20)
    buffer.process_output("Hello\rWorld")

    lines = buffer.get_screen_lines()
    # "Hello" then \r moves cursor to start, then "World" overwrites
    assert lines[0] == "World"
    assert buffer.cursor_col == 5


def test_cursor_positioning_absolute():
    """Test absolute cursor positioning."""
    buffer = ScreenBuffer(10, 40)
    # ESC [ 5 ; 10 H moves to row 5, col 10 (1-indexed in ANSI, 0-indexed internally)
    buffer.process_output("\x1b[5;10HX")

    lines = buffer.get_screen_lines()
    assert lines[4][9] == "X"
    assert buffer.cursor_row == 4
    assert buffer.cursor_col == 10


def test_cursor_up():
    """Test cursor up movement."""
    buffer = ScreenBuffer(10, 40)
    buffer.process_output("Line 1\nLine 2\nLine 3")
    # Cursor is at row 2, move up 1
    buffer.process_output("\x1b[1A")
    buffer.process_output("X")

    lines = buffer.get_screen_lines()
    assert "X" in lines[1]


def test_cursor_down():
    """Test cursor down movement."""
    buffer = ScreenBuffer(10, 40)
    buffer.process_output("Line 1")
    # Move down 2 rows
    buffer.process_output("\x1b[2B")
    buffer.process_output("X")

    lines = buffer.get_screen_lines()
    assert "X" in lines[2]


def test_cursor_forward():
    """Test cursor forward movement."""
    buffer = ScreenBuffer(10, 40)
    buffer.process_output("AAA")
    # Move forward 5 positions
    buffer.process_output("\x1b[5C")
    buffer.process_output("X")

    lines = buffer.get_screen_lines()
    assert lines[0][8] == "X"  # 3 (AAA) + 5 (forward) = 8


def test_cursor_backward():
    """Test cursor backward movement."""
    buffer = ScreenBuffer(10, 40)
    buffer.process_output("AAAAA")
    # Move backward 2 positions
    buffer.process_output("\x1b[2D")
    buffer.process_output("X")

    lines = buffer.get_screen_lines()
    assert lines[0][3] == "X"  # 5 - 2 = 3


def test_clear_screen():
    """Test clear screen."""
    buffer = ScreenBuffer(10, 40)
    buffer.process_output("Line 1\nLine 2\nLine 3")

    # Clear screen
    buffer.process_output("\x1b[2J")

    lines = buffer.get_screen_lines()
    # All lines should be empty
    for line in lines:
        assert line == ""


def test_clear_line_to_end():
    """Test clear line from cursor to end."""
    buffer = ScreenBuffer(5, 20)
    buffer.process_output("Hello World")
    # Move cursor back
    buffer.move_cursor(0, 5)
    # Clear from cursor to end of line
    buffer.process_output("\x1b[K")

    lines = buffer.get_screen_lines()
    assert lines[0] == "Hello"


def test_clear_entire_line():
    """Test clear entire line."""
    buffer = ScreenBuffer(5, 20)
    buffer.process_output("Hello World")
    buffer.move_cursor(0, 5)
    # Clear entire line
    buffer.process_output("\x1b[2K")

    lines = buffer.get_screen_lines()
    assert lines[0] == ""


def test_ignore_color_codes():
    """Test that color/style codes are ignored."""
    buffer = ScreenBuffer(5, 40)
    # Text with color codes: red text
    buffer.process_output("\x1b[31mRed Text\x1b[0m Normal")

    lines = buffer.get_screen_lines()
    # Colors are ignored, only text remains
    assert lines[0] == "Red Text Normal"


def test_complex_htop_like_output():
    """Test complex output similar to htop."""
    buffer = ScreenBuffer(10, 80)

    # Simulate htop-like output with cursor positioning
    output = (
        "\x1b[H"  # Move to home
        "\x1b[2J"  # Clear screen
        "  PID USER      PRI  NI  VIRT   RES   SHR S CPU% MEM%   TIME+  Command\n"
        "\x1b[2;1H"  # Move to row 2
        " 1115 rom1504    20   0 3.4G  1.1G 11088 S  4.7  3.5  303h   syncthing\n"
        "\x1b[3;1H"  # Move to row 3
        " 2234 ai         20   0 1.2G  611M 58288 S 29.4  1.9   49h   claude\n"
    )

    buffer.process_output(output)
    lines = buffer.get_screen_lines()

    # Check header
    assert "PID USER" in lines[0]
    # Check process lines
    assert "1115" in lines[1]
    assert "syncthing" in lines[1]
    assert "2234" in lines[2]
    assert "claude" in lines[2]


def test_screen_wrapping():
    """Test cursor wrapping at line end."""
    buffer = ScreenBuffer(5, 10)
    # Write more than line width
    buffer.process_output("1234567890ABCDEF")

    lines = buffer.get_screen_lines()
    # First line should be full
    assert lines[0] == "1234567890"
    # Rest wraps to next line
    assert lines[1] == "ABCDEF"


def test_tab_character():
    """Test tab character handling."""
    buffer = ScreenBuffer(5, 40)
    buffer.process_output("A\tB")

    lines = buffer.get_screen_lines()
    # Tab moves to next 8-column boundary
    assert lines[0][0] == "A"
    assert lines[0][8] == "B"


def test_backspace():
    """Test backspace character."""
    buffer = ScreenBuffer(5, 20)
    buffer.process_output("Hello\b\b\bXYZ")

    lines = buffer.get_screen_lines()
    # "Hello" then 3 backspaces (to position 2), then "XYZ"
    assert lines[0] == "HeXYZ"


def test_save_and_restore_cursor():
    """Test save and restore cursor position."""
    buffer = ScreenBuffer(10, 40)
    buffer.process_output("Hello")
    # Save cursor position (at col 5)
    buffer.process_output("\x1b[s")
    buffer.process_output(" World")
    # Restore cursor position (back to col 5)
    buffer.process_output("\x1b[u")
    buffer.process_output("X")

    lines = buffer.get_screen_lines()
    assert lines[0][5] == "X"


def test_get_screen_text():
    """Test get_screen_text method."""
    buffer = ScreenBuffer(3, 20)
    buffer.process_output("Line 1\nLine 2\nLine 3")

    text = buffer.get_screen_text()
    assert text == "Line 1\nLine 2\nLine 3"


def test_multiple_processes():
    """Test parsing multiple process lines like in htop."""
    buffer = ScreenBuffer(30, 150)

    # Simulate htop output with multiple processes
    output = "\x1b[H\x1b[2J"  # Clear and home
    output += "  PID USER      CPU% MEM%   COMMAND\n"

    # Add 5 processes
    for i in range(5):
        pid = 1000 + i
        mem = 3.5 - (i * 0.3)
        output += f"\x1b[{i+2};1H"  # Move to line i+2
        output += f"{pid:5d} user     {i*10:4d}  {mem:4.1f}   process-{i}\n"

    buffer.process_output(output)
    lines = buffer.get_screen_lines()

    # Verify header
    assert "PID USER" in lines[0]

    # Verify all 5 processes are present
    for i in range(5):
        assert f"process-{i}" in lines[i + 1]
        assert f"{1000 + i}" in lines[i + 1]
