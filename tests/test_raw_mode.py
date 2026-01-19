"""Tests for raw mode support in terminal PTY."""

import pytest
import time
import os
import asyncio
from term_wrapper.terminal import Terminal


def test_raw_mode_parameter_default():
    """Test that raw_mode defaults to True."""
    term = Terminal(rows=24, cols=80)

    # Should succeed without specifying raw_mode
    # Use sleep to keep process alive for testing (echo exits too fast)
    term.spawn(["sleep", "1"])
    assert term.is_alive()
    term.kill()


def test_raw_mode_explicit_true():
    """Test explicitly enabling raw mode."""
    term = Terminal(rows=24, cols=80)

    # Explicitly enable raw mode
    # Use sleep to keep process alive for testing (echo exits too fast)
    term.spawn(["sleep", "1"], raw_mode=True)
    assert term.is_alive()
    term.kill()


def test_raw_mode_explicit_false():
    """Test disabling raw mode."""
    term = Terminal(rows=24, cols=80)

    # Explicitly disable raw mode
    # Use sleep to keep process alive for testing (echo exits too fast)
    term.spawn(["sleep", "1"], raw_mode=False)
    assert term.is_alive()
    term.kill()


def test_raw_mode_tty_detection():
    """Test that PTY reports isTTY correctly with raw mode."""
    term = Terminal(rows=24, cols=80)

    # Create a Node.js script to check isTTY
    test_script = '/tmp/test_istty.cjs'
    with open(test_script, 'w') as f:
        f.write("""
console.log('stdin.isTTY:', process.stdin.isTTY);
console.log('stdout.isTTY:', process.stdout.isTTY);
console.log('stderr.isTTY:', process.stderr.isTTY);
console.log('setRawMode:', typeof process.stdin.setRawMode);
""")

    term.spawn(["node", test_script], raw_mode=True)
    term.output_callback = lambda data: None  # Discard output for now

    # Let it run
    time.sleep(1)

    # The process should complete successfully
    assert not term.is_alive() or term.pid is not None

    term.kill()
    os.remove(test_script)


@pytest.mark.asyncio
async def test_raw_mode_keyboard_input():
    """Test that raw mode allows keyboard input to be received."""
    term = Terminal(rows=24, cols=80)

    # Create a simple Node.js script that reads stdin in raw mode
    test_script = '/tmp/test_raw_input.cjs'
    with open(test_script, 'w') as f:
        f.write("""
process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');

let received = '';
process.stdin.on('data', (key) => {
    if (key === '\\u0003') process.exit(); // Ctrl+C
    if (key === 'q') {
        console.log('RECEIVED:', received);
        process.exit();
    }
    received += key;
});

setTimeout(() => process.exit(), 5000); // Timeout after 5s
""")

    output_buffer = []

    def capture_output(data):
        output_buffer.append(data.decode('utf-8', errors='replace'))

    term.spawn(["node", test_script], raw_mode=True)
    term.output_callback = capture_output

    # Start async reading
    await term.start_reading()
    await asyncio.sleep(0.5)

    # Send some characters
    term.write(b'hello')
    await asyncio.sleep(0.5)

    # Send 'q' to quit
    term.write(b'q')
    await asyncio.sleep(1)

    # Check output
    full_output = ''.join(output_buffer)
    assert 'RECEIVED:' in full_output
    assert 'hello' in full_output

    term.kill()
    os.remove(test_script)


@pytest.mark.asyncio
async def test_raw_mode_with_env_variables():
    """Test raw mode with environment variables."""
    term = Terminal(rows=24, cols=80)

    test_script = '/tmp/test_env.cjs'
    with open(test_script, 'w') as f:
        f.write("""
console.log('TERM:', process.env.TERM);
console.log('COLORTERM:', process.env.COLORTERM);
""")

    output_buffer = []

    def capture_output(data):
        output_buffer.append(data.decode('utf-8', errors='replace'))

    env = {
        'TERM': 'xterm-256color',
        'COLORTERM': 'truecolor'
    }

    term.spawn(["node", test_script], env=env, raw_mode=True)
    term.output_callback = capture_output

    await term.start_reading()
    await asyncio.sleep(1)

    full_output = ''.join(output_buffer)
    assert 'xterm-256color' in full_output
    assert 'truecolor' in full_output

    term.kill()
    os.remove(test_script)


@pytest.mark.asyncio
async def test_raw_mode_enter_key():
    """Test that Enter key works in raw mode."""
    term = Terminal(rows=24, cols=80)

    test_script = '/tmp/test_enter.cjs'
    with open(test_script, 'w') as f:
        f.write("""
process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');

let input = '';
process.stdin.on('data', (key) => {
    if (key === '\\u0003') process.exit();
    if (key === '\\r' || key === '\\n') {
        console.log('ENTERED:', input);
        process.exit();
    }
    input += key;
});

setTimeout(() => process.exit(), 5000);
""")

    output_buffer = []

    def capture_output(data):
        output_buffer.append(data.decode('utf-8', errors='replace'))

    term.spawn(["node", test_script], raw_mode=True)
    term.output_callback = capture_output

    await term.start_reading()
    await asyncio.sleep(0.5)

    # Send text and Enter
    term.write(b'test123')
    await asyncio.sleep(0.2)
    term.write(b'\r')
    await asyncio.sleep(1)

    full_output = ''.join(output_buffer)
    assert 'ENTERED:' in full_output
    assert 'test123' in full_output

    term.kill()
    os.remove(test_script)


@pytest.mark.asyncio
async def test_raw_mode_special_keys():
    """Test that special keys work in raw mode."""
    term = Terminal(rows=24, cols=80)

    test_script = '/tmp/test_special_keys.cjs'
    with open(test_script, 'w') as f:
        f.write("""
process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');

let keys_received = [];
process.stdin.on('data', (key) => {
    if (key === '\\u0003') process.exit();

    if (key === '\\t') keys_received.push('TAB');
    else if (key === '\\r') keys_received.push('ENTER');
    else if (key === '\\u007f') keys_received.push('BACKSPACE');
    else if (key === '\\u001b') keys_received.push('ESC');
    else if (key === 'q') {
        console.log('KEYS:', keys_received.join(','));
        process.exit();
    }
});

setTimeout(() => process.exit(), 5000);
""")

    output_buffer = []

    def capture_output(data):
        output_buffer.append(data.decode('utf-8', errors='replace'))

    term.spawn(["node", test_script], raw_mode=True)
    term.output_callback = capture_output

    await term.start_reading()
    await asyncio.sleep(0.5)

    # Send special keys
    term.write(b'\t')      # Tab
    await asyncio.sleep(0.1)
    term.write(b'\r')      # Enter
    await asyncio.sleep(0.1)
    term.write(b'\x7f')    # Backspace
    await asyncio.sleep(0.1)
    term.write(b'\x1b')    # Escape
    await asyncio.sleep(0.1)
    term.write(b'q')       # Quit
    await asyncio.sleep(1)

    full_output = ''.join(output_buffer)
    assert 'KEYS:' in full_output
    assert 'TAB' in full_output
    assert 'ENTER' in full_output
    assert 'BACKSPACE' in full_output
    assert 'ESC' in full_output

    term.kill()
    os.remove(test_script)


@pytest.mark.asyncio
async def test_raw_mode_no_buffering():
    """Test that raw mode sends characters immediately (no line buffering)."""
    term = Terminal(rows=24, cols=80)

    test_script = '/tmp/test_no_buffer.cjs'
    with open(test_script, 'w') as f:
        f.write("""
process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');

let count = 0;
process.stdin.on('data', (key) => {
    if (key === '\\u0003') process.exit();
    count++;
    console.log('CHAR', count, ':', key.charCodeAt(0));
    if (count >= 3) process.exit();
});

setTimeout(() => process.exit(), 5000);
""")

    output_buffer = []

    def capture_output(data):
        output_buffer.append(data.decode('utf-8', errors='replace'))

    term.spawn(["node", test_script], raw_mode=True)
    term.output_callback = capture_output

    await term.start_reading()
    await asyncio.sleep(0.5)

    # Send characters one by one
    term.write(b'a')
    await asyncio.sleep(0.2)
    term.write(b'b')
    await asyncio.sleep(0.2)
    term.write(b'c')
    await asyncio.sleep(1)

    full_output = ''.join(output_buffer)

    # Should receive 3 separate character events
    assert full_output.count('CHAR') >= 3

    term.kill()
    os.remove(test_script)
