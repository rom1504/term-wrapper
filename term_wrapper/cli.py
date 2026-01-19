"""CLI client for terminal wrapper."""

import asyncio
import sys
import termios
import tty
import time
from typing import Optional, Callable
import httpx
import websockets
import json
from .utils import strip_ansi, extract_visible_text


class TerminalClient:
    """Client for interacting with terminal wrapper backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client.

        Args:
            base_url: Base URL of the backend server
        """
        self.base_url = base_url
        self.http_client = httpx.Client(base_url=base_url, timeout=10.0)
        self._read_marks = {}  # Track read positions per session

    def create_session(
        self, command: list[str], rows: int = 24, cols: int = 80, env: Optional[dict] = None
    ) -> str:
        """Create a new terminal session.

        Args:
            command: Command to run
            rows: Terminal rows
            cols: Terminal columns
            env: Optional environment variables

        Returns:
            Session ID
        """
        payload = {"command": command, "rows": rows, "cols": cols}
        if env is not None:
            payload["env"] = env

        response = self.http_client.post(
            "/sessions",
            json=payload,
        )
        response.raise_for_status()
        return response.json()["session_id"]

    def list_sessions(self) -> list[str]:
        """List all sessions.

        Returns:
            List of session IDs
        """
        response = self.http_client.get("/sessions")
        response.raise_for_status()
        return response.json()["sessions"]

    def get_session_info(self, session_id: str) -> dict:
        """Get session information.

        Args:
            session_id: Session ID

        Returns:
            Session information
        """
        response = self.http_client.get(f"/sessions/{session_id}")
        response.raise_for_status()
        return response.json()

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session ID
        """
        response = self.http_client.delete(f"/sessions/{session_id}")
        response.raise_for_status()

    def write_input(self, session_id: str, data: str) -> None:
        """Write input to session.

        Args:
            session_id: Session ID
            data: Input data
        """
        response = self.http_client.post(
            f"/sessions/{session_id}/input",
            json={"data": data},
        )
        response.raise_for_status()

    def get_output(self, session_id: str, clear: bool = True) -> str:
        """Get session output.

        Args:
            session_id: Session ID
            clear: Whether to clear buffer

        Returns:
            Output data
        """
        response = self.http_client.get(
            f"/sessions/{session_id}/output",
            params={"clear": clear},
        )
        response.raise_for_status()
        return response.json()["output"]

    def get_screen(self, session_id: str) -> dict:
        """Get parsed terminal screen as 2D array.

        This returns the terminal screen buffer processed through the
        ScreenBuffer class, which handles ANSI escape sequences and
        cursor positioning to produce clean, parseable text lines.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with:
                - lines: List of strings, one per screen row
                - rows: Number of rows
                - cols: Number of columns
                - cursor: Current cursor position {row, col}
        """
        response = self.http_client.get(f"/sessions/{session_id}/screen")
        response.raise_for_status()
        return response.json()

    def get_text(self, session_id: str, strip_ansi_codes: bool = True,
                 source: str = "output") -> str:
        """Get clean text output from session.

        Args:
            session_id: Session ID
            strip_ansi_codes: Whether to remove ANSI escape codes
            source: Source to read from - "output" (raw, default) or "screen" (2D buffer)

        Returns:
            Clean text output
        """
        if source == "screen":
            screen = self.get_screen(session_id)
            text = extract_visible_text(screen['lines'])
        else:
            text = self.get_output(session_id, clear=False)
            if strip_ansi_codes:
                text = strip_ansi(text)

        return text

    def wait_for_text(self, session_id: str, text: str, timeout: float = 30,
                     poll_interval: float = 0.5, strip_ansi_codes: bool = True) -> bool:
        """Wait for specific text to appear in output.

        Args:
            session_id: Session ID
            text: Text to wait for
            timeout: Maximum seconds to wait
            poll_interval: Seconds between polls
            strip_ansi_codes: Whether to strip ANSI codes before checking

        Returns:
            True if text found, False if timeout

        Raises:
            TimeoutError: If timeout is reached
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_text = self.get_text(session_id, strip_ansi_codes=strip_ansi_codes)
            if text in current_text:
                return True
            time.sleep(poll_interval)

        raise TimeoutError(f"Text '{text}' not found within {timeout} seconds")

    def wait_for_condition(self, session_id: str, condition: Callable[[str], bool],
                          timeout: float = 30, poll_interval: float = 0.5) -> bool:
        """Wait for a condition function to return True.

        Args:
            session_id: Session ID
            condition: Function that takes current text and returns bool
            timeout: Maximum seconds to wait
            poll_interval: Seconds between polls

        Returns:
            True if condition met, False if timeout

        Raises:
            TimeoutError: If timeout is reached
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_text = self.get_text(session_id)
            if condition(current_text):
                return True
            time.sleep(poll_interval)

        raise TimeoutError(f"Condition not met within {timeout} seconds")

    def wait_for_quiet(self, session_id: str, duration: float = 2.0,
                      poll_interval: float = 0.5, timeout: float = 30) -> bool:
        """Wait for output to stop changing.

        Args:
            session_id: Session ID
            duration: Seconds of no change required
            poll_interval: Seconds between polls
            timeout: Maximum seconds to wait

        Returns:
            True if quiet period achieved

        Raises:
            TimeoutError: If timeout is reached
        """
        start_time = time.time()
        last_text = None
        quiet_start = None

        while time.time() - start_time < timeout:
            current_text = self.get_text(session_id)

            if current_text == last_text:
                if quiet_start is None:
                    quiet_start = time.time()
                elif time.time() - quiet_start >= duration:
                    return True
            else:
                quiet_start = None
                last_text = current_text

            time.sleep(poll_interval)

        raise TimeoutError(f"Output did not stabilize within {timeout} seconds")

    def get_new_lines(self, session_id: str, strip_ansi_codes: bool = True) -> list[str]:
        """Get new lines since last call to this method.

        Args:
            session_id: Session ID
            strip_ansi_codes: Whether to strip ANSI codes

        Returns:
            List of new lines since last call
        """
        current_text = self.get_text(session_id, strip_ansi_codes=strip_ansi_codes)
        current_lines = current_text.split('\n')

        if session_id not in self._read_marks:
            # First call - return all lines
            self._read_marks[session_id] = len(current_lines)
            return current_lines

        # Return only new lines
        last_count = self._read_marks[session_id]
        new_lines = current_lines[last_count:]
        self._read_marks[session_id] = len(current_lines)

        return new_lines

    def mark_read(self, session_id: str) -> None:
        """Mark current output as read.

        Subsequent calls to get_new_lines() will only return output after this mark.

        Args:
            session_id: Session ID
        """
        current_text = self.get_text(session_id)
        current_lines = current_text.split('\n')
        self._read_marks[session_id] = len(current_lines)

    async def interactive_session(self, session_id: str) -> None:
        """Run an interactive session via WebSocket.

        Args:
            session_id: Session ID
        """
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/sessions/{session_id}/ws"

        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set terminal to raw mode
            tty.setraw(sys.stdin)

            async with websockets.connect(ws_url) as websocket:

                async def send_input():
                    """Read from stdin and send to WebSocket."""
                    loop = asyncio.get_event_loop()
                    while True:
                        try:
                            # Read one byte at a time
                            char = await loop.run_in_executor(
                                None, sys.stdin.buffer.read, 1
                            )
                            if char:
                                await websocket.send(char)
                        except Exception:
                            break

                async def receive_output():
                    """Receive from WebSocket and write to stdout."""
                    while True:
                        try:
                            message = await websocket.recv()
                            if isinstance(message, bytes):
                                sys.stdout.buffer.write(message)
                                sys.stdout.buffer.flush()
                            elif message == "__TERMINAL_CLOSED__":
                                break
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception:
                            break

                # Run both tasks concurrently
                await asyncio.gather(send_input(), receive_output())

        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def close(self) -> None:
        """Close the HTTP client."""
        self.http_client.close()


async def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Terminal Wrapper CLI")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Backend server URL",
    )
    parser.add_argument(
        "command",
        nargs="+",
        help="Command to run in terminal",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=24,
        help="Terminal rows",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=80,
        help="Terminal columns",
    )

    args = parser.parse_args()

    client = TerminalClient(base_url=args.url)

    try:
        # Create session
        print(f"Creating session for command: {' '.join(args.command)}")
        session_id = client.create_session(
            command=args.command,
            rows=args.rows,
            cols=args.cols,
        )
        print(f"Session created: {session_id}")
        print("Starting interactive session (press Ctrl+C to exit)...")
        print()

        # Start interactive session
        await client.interactive_session(session_id)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up
        try:
            client.delete_session(session_id)
            print(f"\nSession {session_id} deleted")
        except Exception:
            pass
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
