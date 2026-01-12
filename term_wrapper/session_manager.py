"""Terminal session manager."""

import asyncio
import uuid
from typing import Dict, Optional
from .terminal import Terminal


class TerminalSession:
    """Represents a terminal session."""

    def __init__(self, session_id: str, terminal: Terminal):
        """Initialize terminal session.

        Args:
            session_id: Unique session identifier
            terminal: Terminal instance
        """
        self.session_id = session_id
        self.terminal = terminal
        self.output_buffer: list[bytes] = []
        self.lock = asyncio.Lock()

    def add_output(self, data: bytes) -> None:
        """Add output data to buffer.

        Args:
            data: Output bytes from terminal
        """
        self.output_buffer.append(data)

    async def get_output(self, clear: bool = True) -> bytes:
        """Get accumulated output.

        Args:
            clear: Whether to clear the buffer after reading

        Returns:
            Accumulated output bytes
        """
        async with self.lock:
            output = b"".join(self.output_buffer)
            if clear:
                self.output_buffer.clear()
            return output


class SessionManager:
    """Manages multiple terminal sessions."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, TerminalSession] = {}

    def create_session(
        self,
        command: list[str],
        rows: int = 24,
        cols: int = 80,
        env: Optional[dict] = None,
    ) -> str:
        """Create a new terminal session.

        Args:
            command: Command to run in terminal
            rows: Terminal rows
            cols: Terminal columns
            env: Environment variables

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        terminal = Terminal(rows, cols)

        session = TerminalSession(session_id, terminal)
        terminal.output_callback = session.add_output

        terminal.spawn(command, env)

        self.sessions[session_id] = session

        return session_id

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get a terminal session by ID.

        Args:
            session_id: Session identifier

        Returns:
            TerminalSession or None if not found
        """
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a terminal session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.terminal.kill()
        del self.sessions[session_id]
        return True

    def list_sessions(self) -> list[str]:
        """List all active session IDs.

        Returns:
            List of session IDs
        """
        return list(self.sessions.keys())
