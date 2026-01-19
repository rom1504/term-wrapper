"""FastAPI backend for terminal wrapper."""

import asyncio
import os
import re
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from .session_manager import SessionManager

# Get package version
try:
    from importlib.metadata import version
    VERSION = version("term-wrapper")
except Exception:
    # Fallback to reading from pyproject.toml if not installed
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "r") as f:
            for line in f:
                if line.startswith("version = "):
                    VERSION = line.split("=")[1].strip().strip('"')
                    break
            else:
                VERSION = "unknown"
    except Exception:
        VERSION = "unknown"

app = FastAPI(title="Terminal Wrapper API")

# Mount frontend static files
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager()


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    command: list[str]
    rows: int = 24
    cols: int = 80
    env: Optional[dict] = None


class WriteInputRequest(BaseModel):
    """Request model for writing input to terminal."""

    data: str


class ResizeRequest(BaseModel):
    """Request model for resizing terminal."""

    rows: int
    cols: int


@app.post("/sessions")
async def create_session(request: CreateSessionRequest) -> JSONResponse:
    """Create a new terminal session.

    Args:
        request: Session creation request

    Returns:
        JSON response with session_id
    """
    session_id = session_manager.create_session(
        command=request.command,
        rows=request.rows,
        cols=request.cols,
        env=request.env,
    )

    session = session_manager.get_session(session_id)
    if session:
        # Start reading from terminal
        await session.terminal.start_reading()

    return JSONResponse({"session_id": session_id})


@app.get("/sessions")
async def list_sessions() -> JSONResponse:
    """List all active sessions.

    Returns:
        JSON response with list of session IDs
    """
    sessions = session_manager.list_sessions()
    return JSONResponse({"sessions": sessions})


@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str) -> JSONResponse:
    """Get session information.

    Args:
        session_id: Session identifier

    Returns:
        JSON response with session info

    Raises:
        HTTPException: If session not found
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return JSONResponse(
        {
            "session_id": session_id,
            "alive": session.terminal.is_alive(),
            "rows": session.terminal.rows,
            "cols": session.terminal.cols,
            "command": session.command,
        }
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> JSONResponse:
    """Delete a terminal session.

    Args:
        session_id: Session identifier

    Returns:
        JSON response with success status

    Raises:
        HTTPException: If session not found
    """
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return JSONResponse({"status": "deleted"})


@app.post("/sessions/{session_id}/input")
async def write_input(session_id: str, request: WriteInputRequest) -> JSONResponse:
    """Write input to terminal session.

    Args:
        session_id: Session identifier
        request: Input data request

    Returns:
        JSON response with success status

    Raises:
        HTTPException: If session not found
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.terminal.write(request.data.encode())
    return JSONResponse({"status": "ok"})


@app.post("/sessions/{session_id}/resize")
async def resize_terminal(session_id: str, request: ResizeRequest) -> JSONResponse:
    """Resize terminal session.

    Args:
        session_id: Session identifier
        request: Resize request

    Returns:
        JSON response with success status

    Raises:
        HTTPException: If session not found
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.terminal.resize(request.rows, request.cols)
    return JSONResponse({"status": "ok"})


@app.get("/sessions/{session_id}/output")
async def get_output(session_id: str, clear: bool = True) -> JSONResponse:
    """Get terminal output.

    Args:
        session_id: Session identifier
        clear: Whether to clear buffer after reading

    Returns:
        JSON response with output data

    Raises:
        HTTPException: If session not found
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    output = await session.get_output(clear=clear)
    return JSONResponse({"output": output.decode("utf-8", errors="replace")})


@app.get("/sessions/{session_id}/screen")
async def get_screen(session_id: str) -> JSONResponse:
    """Get rendered terminal screen as 2D array.

    This endpoint provides a parsed view of the terminal screen,
    processing ANSI escape sequences and cursor positioning to
    produce a 2D grid of characters. This is useful for parsing
    complex TUI applications like htop, vim, etc.

    Args:
        session_id: Session identifier

    Returns:
        JSON response with:
            - lines: List of strings, one per screen row
            - rows: Number of rows
            - cols: Number of columns
            - cursor: Current cursor position {row, col}

    Raises:
        HTTPException: If session not found
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lines = session.screen_buffer.get_screen_lines()

    return JSONResponse({
        "lines": lines,
        "rows": session.screen_buffer.rows,
        "cols": session.screen_buffer.cols,
        "cursor": {
            "row": session.screen_buffer.cursor_row,
            "col": session.screen_buffer.cursor_col
        }
    })


def filter_unsupported_ansi(data: bytes) -> bytes:
    """Filter out ANSI sequences not fully supported by xterm.js.

    This prevents rendering issues with applications like Claude Code that use
    newer terminal features or send malformed sequences.

    Args:
        data: Raw terminal output with ANSI escape sequences

    Returns:
        Filtered output with unsupported/malformed sequences removed
    """
    # Convert to string for regex processing
    text = data.decode('utf-8', errors='replace')

    # Remove synchronized output mode sequences (DEC 2026)
    # ESC[?2026h - Enable synchronized output
    # ESC[?2026l - Disable synchronized output
    text = re.sub(r'\x1b\[\?2026[hl]', '', text)

    # Remove ESC[<u sequence which appears frequently and may cause rendering issues
    # This is not a standard terminal escape sequence and xterm.js doesn't handle it
    text = re.sub(r'\x1b\[<u', '', text)

    # Convert back to bytes
    return text.encode('utf-8', errors='replace')


@app.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time terminal interaction.

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    await websocket.accept()

    async def send_output():
        """Send terminal output to WebSocket."""
        while True:
            try:
                await asyncio.sleep(0.001)  # 1ms polling interval for real-time updates
                output = await session.get_output(clear=True)
                if output:
                    # Filter unsupported ANSI sequences before sending
                    filtered_output = filter_unsupported_ansi(output)
                    await websocket.send_bytes(filtered_output)

                if not session.terminal.is_alive():
                    await websocket.send_text("__TERMINAL_CLOSED__")
                    break
            except WebSocketDisconnect:
                break
            except Exception:
                break

    async def receive_input():
        """Receive input from WebSocket and send to terminal."""
        while True:
            try:
                data = await websocket.receive_bytes()
                session.terminal.write(data)
            except WebSocketDisconnect:
                break
            except Exception:
                break

    # Run both tasks concurrently
    try:
        await asyncio.gather(send_output(), receive_input())
    except asyncio.CancelledError:
        # Handle cancellation (e.g., client disconnect) gracefully
        pass
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSON response with health status
    """
    return JSONResponse({"status": "healthy"})


@app.get("/version")
async def get_version() -> JSONResponse:
    """Get application version.

    Returns:
        JSON response with version string
    """
    return JSONResponse({"version": VERSION})


@app.get("/")
async def root():
    """Serve the frontend application.

    Returns:
        HTML page
    """
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        {"message": "Frontend not found. API is running at /health"},
        status_code=404
    )
