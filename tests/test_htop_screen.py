"""End-to-end tests for htop with screen buffer parsing."""

import pytest
import httpx
import asyncio
import time
from multiprocessing import Process
import uvicorn


BASE_URL = "http://localhost:8006"


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="127.0.0.1",
        port=8006,
        log_level="error",
    )


@pytest.fixture(scope="module")
def server():
    """Start server for tests."""
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(2)
    yield
    proc.terminate()
    proc.join(timeout=5)


@pytest.mark.asyncio
async def test_htop_screen_buffer_basic(server):
    """Test that htop output can be parsed via screen buffer."""
    base_url = BASE_URL

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # Create htop session with good size
        response = await client.post("/sessions", json={
            "command": ["htop", "-C"],  # -C for no colors (easier testing)
            "rows": 30,
            "cols": 150,
            "env": {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor"
            }
        })

        assert response.status_code == 200
        session_data = response.json()
        session_id = session_data["session_id"]

        # Wait for htop to start and render
        await asyncio.sleep(2)

        # Get screen buffer
        response = await client.get(f"/sessions/{session_id}/screen")
        assert response.status_code == 200

        screen_data = response.json()
        assert "lines" in screen_data
        assert "rows" in screen_data
        assert "cols" in screen_data
        assert screen_data["rows"] == 30
        assert screen_data["cols"] == 150

        lines = screen_data["lines"]
        assert len(lines) == 30

        # Check for htop header
        header_found = False
        for line in lines:
            if "PID" in line and "USER" in line and "Command" in line:
                header_found = True
                break

        assert header_found, "htop header not found in screen buffer"

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_htop_parse_processes(server):
    """Test parsing individual processes from htop screen buffer."""
    base_url = BASE_URL

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # Create htop session sorted by memory
        response = await client.post("/sessions", json={
            "command": ["htop", "-C", "--sort-key=PERCENT_MEM"],
            "rows": 40,
            "cols": 150,
            "env": {"TERM": "xterm-256color"}
        })

        session_id = response.json()["session_id"]

        # Wait for htop
        await asyncio.sleep(2)

        # Get screen buffer
        response = await client.get(f"/sessions/{session_id}/screen")
        screen_data = response.json()
        lines = screen_data["lines"]

        # Find header line
        header_idx = None
        for i, line in enumerate(lines):
            if "PID" in line and "USER" in line:
                header_idx = i
                break

        assert header_idx is not None, "Could not find htop header"

        # Parse process lines after header
        processes = []
        for line in lines[header_idx + 1:]:
            # Skip empty lines
            if not line.strip():
                continue

            # Try to parse process line
            # htop format: PID USER PRI NI VIRT RES SHR S CPU% MEM% TIME+ Command
            parts = line.split()
            if len(parts) >= 11:
                try:
                    pid = int(parts[0])
                    user = parts[1]
                    mem_pct = float(parts[9])
                    cmd = ' '.join(parts[11:]) if len(parts) > 11 else parts[10]

                    processes.append({
                        'pid': pid,
                        'user': user,
                        'mem': mem_pct,
                        'cmd': cmd
                    })
                except (ValueError, IndexError):
                    # Skip lines that don't parse as processes
                    continue

        # Should have found at least one process
        assert len(processes) >= 1, f"Expected at least 1 process, found {len(processes)}"

        # Processes should be sorted by memory (descending)
        if len(processes) >= 2:
            # Allow some tolerance for ties
            assert processes[0]['mem'] >= processes[1]['mem'] - 0.1

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_htop_top_memory_processes(server):
    """Test getting top 5 memory-using processes via htop screen buffer."""
    base_url = BASE_URL

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # Create htop session
        response = await client.post("/sessions", json={
            "command": ["htop", "-C", "--sort-key=PERCENT_MEM"],
            "rows": 40,
            "cols": 150,
            "env": {"TERM": "xterm-256color"}
        })

        session_id = response.json()["session_id"]
        await asyncio.sleep(2.5)

        # Get screen
        response = await client.get(f"/sessions/{session_id}/screen")
        lines = response.json()["lines"]

        # Find and parse processes
        header_idx = None
        for i, line in enumerate(lines):
            if "PID" in line and "MEM%" in line:
                header_idx = i
                break

        assert header_idx is not None

        processes = []
        for line in lines[header_idx + 1:]:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 10:
                try:
                    pid = int(parts[0])
                    mem_str = parts[9]
                    # Handle mem% which might have % symbol
                    mem = float(mem_str.rstrip('%'))

                    if mem > 0:  # Only include processes using memory
                        processes.append({
                            'pid': pid,
                            'mem': mem,
                            'line': line[:100]  # First 100 chars
                        })
                except (ValueError, IndexError):
                    continue

        # Get top 5
        top5 = sorted(processes, key=lambda x: x['mem'], reverse=True)[:5]

        # Should have found at least one process
        assert len(top5) >= 1, f"Expected at least 1 process, got {len(top5)}"

        # Verify they're sorted
        for i in range(len(top5) - 1):
            assert top5[i]['mem'] >= top5[i + 1]['mem']

        # Print for debugging
        print("\nTop 5 Memory Processes via htop screen buffer:")
        for i, p in enumerate(top5, 1):
            print(f"{i}. PID {p['pid']}: {p['mem']:.1f}% - {p['line']}")

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_htop_interactive_sort(server):
    """Test sending sort command to htop and verifying screen update."""
    base_url = BASE_URL

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # Create htop session
        response = await client.post("/sessions", json={
            "command": ["htop", "-C"],
            "rows": 35,
            "cols": 150,
            "env": {"TERM": "xterm-256color"}
        })

        session_id = response.json()["session_id"]
        await asyncio.sleep(2)

        # Get initial screen
        response = await client.get(f"/sessions/{session_id}/screen")
        initial_lines = response.json()["lines"]

        # Send 'M' key to sort by memory
        await client.post(f"/sessions/{session_id}/input", json={"data": "M"})
        await asyncio.sleep(1)

        # Get updated screen
        response = await client.get(f"/sessions/{session_id}/screen")
        updated_lines = response.json()["lines"]

        # Screen should have changed
        assert initial_lines != updated_lines, "Screen did not update after sort command"

        # Should still have header
        header_found = any("PID" in line and "MEM%" in line for line in updated_lines)
        assert header_found

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_screen_buffer_vs_raw_output(server):
    """Compare screen buffer vs raw output to verify parsing."""
    base_url = BASE_URL

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # Create simple command that outputs known text
        response = await client.post("/sessions", json={
            "command": ["bash", "-c", "echo 'Line 1'; echo 'Line 2'; echo 'Line 3'; sleep 3"],
            "rows": 10,
            "cols": 40
        })

        session_id = response.json()["session_id"]
        await asyncio.sleep(1)

        # Get raw output
        response = await client.get(f"/sessions/{session_id}/output")
        raw_output = response.json()["output"]

        # Get screen buffer
        response = await client.get(f"/sessions/{session_id}/screen")
        screen_data = response.json()
        screen_lines = screen_data["lines"]

        # Screen buffer should have parsed the lines cleanly
        assert "Line 1" in screen_lines[0]
        assert "Line 2" in screen_lines[1]
        assert "Line 3" in screen_lines[2]

        # Raw output should contain ANSI codes (if any) and the text
        assert "Line 1" in raw_output
        assert "Line 2" in raw_output
        assert "Line 3" in raw_output

        # Clean up
        await client.delete(f"/sessions/{session_id}")


@pytest.mark.asyncio
async def test_screen_buffer_cursor_position(server):
    """Test that cursor position is tracked correctly."""
    base_url = BASE_URL

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # Create session with vim (cursor will move around)
        response = await client.post("/sessions", json={
            "command": ["bash", "-c", "printf 'Line 1\\nLine 2\\nLine 3'; sleep 3"],
            "rows": 10,
            "cols": 40
        })

        session_id = response.json()["session_id"]
        await asyncio.sleep(1)

        # Get screen with cursor info
        response = await client.get(f"/sessions/{session_id}/screen")
        screen_data = response.json()

        assert "cursor" in screen_data
        assert "row" in screen_data["cursor"]
        assert "col" in screen_data["cursor"]

        # Cursor position should be valid
        assert 0 <= screen_data["cursor"]["row"] < screen_data["rows"]
        assert 0 <= screen_data["cursor"]["col"] < screen_data["cols"]

        # Clean up
        await client.delete(f"/sessions/{session_id}")
