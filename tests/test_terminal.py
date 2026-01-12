"""Unit tests for terminal emulator."""

import asyncio
import pytest
from term_wrapper.terminal import Terminal


@pytest.mark.asyncio
async def test_terminal_spawn_simple_command():
    """Test spawning a simple command."""
    terminal = Terminal(rows=24, cols=80)
    outputs = []

    def capture_output(data: bytes):
        outputs.append(data)

    terminal.output_callback = capture_output
    terminal.spawn(["echo", "Hello, World!"])

    await terminal.start_reading()
    await asyncio.sleep(0.5)

    terminal.kill()

    output = b"".join(outputs).decode()
    assert "Hello, World!" in output


@pytest.mark.asyncio
async def test_terminal_interactive_input():
    """Test writing input to terminal."""
    terminal = Terminal(rows=24, cols=80)
    outputs = []

    def capture_output(data: bytes):
        outputs.append(data)

    terminal.output_callback = capture_output
    terminal.spawn(["cat"])

    await terminal.start_reading()
    await asyncio.sleep(0.1)

    # Write input
    terminal.write(b"test input\n")
    await asyncio.sleep(0.2)

    terminal.kill()

    output = b"".join(outputs).decode()
    assert "test input" in output


@pytest.mark.asyncio
async def test_terminal_is_alive():
    """Test checking if terminal process is alive."""
    terminal = Terminal()
    assert not terminal.is_alive()

    terminal.spawn(["sleep", "1"])
    await terminal.start_reading()

    assert terminal.is_alive()

    terminal.kill()
    await asyncio.sleep(0.1)

    assert not terminal.is_alive()


@pytest.mark.asyncio
async def test_terminal_resize():
    """Test resizing terminal."""
    terminal = Terminal(rows=24, cols=80)
    terminal.spawn(["cat"])
    await terminal.start_reading()

    assert terminal.rows == 24
    assert terminal.cols == 80

    terminal.resize(40, 120)

    assert terminal.rows == 40
    assert terminal.cols == 120

    terminal.kill()


@pytest.mark.asyncio
async def test_terminal_multiple_outputs():
    """Test capturing multiple outputs."""
    terminal = Terminal()
    outputs = []

    def capture_output(data: bytes):
        outputs.append(data)

    terminal.output_callback = capture_output
    terminal.spawn(["sh", "-c", "echo line1; echo line2; echo line3"])

    await terminal.start_reading()
    await asyncio.sleep(0.5)

    terminal.kill()

    output = b"".join(outputs).decode()
    assert "line1" in output
    assert "line2" in output
    assert "line3" in output
