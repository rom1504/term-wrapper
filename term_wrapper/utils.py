"""Utility functions for terminal output processing."""

import re


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text.

    Args:
        text: Text containing ANSI escape codes

    Returns:
        Clean text with ANSI codes removed
    """
    # Pattern matches all ANSI escape sequences
    ansi_pattern = re.compile(r'\x1b[@-_][0-?]*[ -/]*[@-~]')
    return ansi_pattern.sub('', text)


def extract_visible_text(lines: list[str]) -> str:
    """Extract visible text from screen buffer lines.

    Args:
        lines: List of screen lines (already processed by ScreenBuffer)

    Returns:
        Clean text with empty lines removed
    """
    non_empty_lines = [line.rstrip() for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)
