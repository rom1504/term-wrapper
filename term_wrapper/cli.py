"""CLI client for terminal wrapper."""

import asyncio
import sys
import termios
import tty
import time
import webbrowser
from typing import Optional, Callable
import httpx
import websockets
import json
from .utils import strip_ansi, extract_visible_text
from .server_manager import ServerManager


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


def sync_main():
    """Main CLI entry point (synchronous commands)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Terminal Wrapper CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a session (flags before command)
  term-wrapper create --rows 40 --cols 120 bash
  term-wrapper create bash -c "ls -la"

  # Send input to a session
  term-wrapper send <session-id> "ls -la\\r"

  # Wait for text to appear
  term-wrapper wait-text <session-id> "username:"

  # Get clean text output
  term-wrapper get-text <session-id>

  # Attach interactively
  term-wrapper attach <session-id>
        """
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Backend server URL (default: auto-discover or start server)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create session
    create_parser = subparsers.add_parser("create", help="Create a new terminal session")
    create_parser.add_argument("--rows", type=int, default=24, help="Terminal rows")
    create_parser.add_argument("--cols", type=int, default=80, help="Terminal columns")
    create_parser.add_argument("--env", help="Environment variables as JSON")
    create_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run")

    # List sessions
    subparsers.add_parser("list", help="List all sessions")

    # Get session info
    info_parser = subparsers.add_parser("info", help="Get session information")
    info_parser.add_argument("session_id", help="Session ID")

    # Delete session
    delete_parser = subparsers.add_parser("delete", help="Delete a session")
    delete_parser.add_argument("session_id", help="Session ID")

    # Send input
    send_parser = subparsers.add_parser("send", help="Send input to session")
    send_parser.add_argument("session_id", help="Session ID")
    send_parser.add_argument("text", help="Text to send (use \\n for newline, \\r for enter)")

    # Get output
    output_parser = subparsers.add_parser("get-output", help="Get raw output")
    output_parser.add_argument("session_id", help="Session ID")
    output_parser.add_argument("--no-clear", action="store_true", help="Don't clear buffer")

    # Get text
    text_parser = subparsers.add_parser("get-text", help="Get clean text output")
    text_parser.add_argument("session_id", help="Session ID")
    text_parser.add_argument("--no-strip-ansi", action="store_true", help="Don't strip ANSI codes")
    text_parser.add_argument("--source", choices=["output", "screen"], default="output",
                            help="Source to read from")

    # Get screen
    screen_parser = subparsers.add_parser("get-screen", help="Get parsed screen buffer")
    screen_parser.add_argument("session_id", help="Session ID")

    # Wait for text
    wait_text_parser = subparsers.add_parser("wait-text", help="Wait for specific text to appear")
    wait_text_parser.add_argument("session_id", help="Session ID")
    wait_text_parser.add_argument("text", help="Text to wait for")
    wait_text_parser.add_argument("--timeout", type=float, default=30, help="Timeout in seconds")
    wait_text_parser.add_argument("--poll-interval", type=float, default=0.5, help="Poll interval in seconds")

    # Wait for quiet
    wait_quiet_parser = subparsers.add_parser("wait-quiet", help="Wait for output to stabilize")
    wait_quiet_parser.add_argument("session_id", help="Session ID")
    wait_quiet_parser.add_argument("--duration", type=float, default=2.0, help="Quiet duration in seconds")
    wait_quiet_parser.add_argument("--timeout", type=float, default=30, help="Timeout in seconds")

    # Attach (interactive)
    attach_parser = subparsers.add_parser("attach", help="Attach to session interactively")
    attach_parser.add_argument("session_id", help="Session ID")

    # Web (open in browser)
    web_parser = subparsers.add_parser("web", help="Open session in browser or create and open")
    web_parser.add_argument("session_or_command", help="Session ID or command to run")
    web_parser.add_argument("cmd_args", nargs=argparse.REMAINDER, help="Additional command arguments")
    web_parser.add_argument("--rows", type=int, default=40, help="Terminal rows (when creating new session)")
    web_parser.add_argument("--cols", type=int, default=120, help="Terminal columns (when creating new session)")

    # Stop server
    subparsers.add_parser("stop", help="Stop the term-wrapper server")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle stop command separately (doesn't need server)
    if args.command == "stop":
        server_manager = ServerManager()
        result = server_manager.stop_server()
        print(json.dumps(result))
        sys.exit(0 if result["status"] in ["stopped", "not_running"] else 1)

    # Auto-discover or start server if URL not provided
    if args.url is None:
        server_manager = ServerManager()
        try:
            url = server_manager.get_server_url()
        except Exception as e:
            print(json.dumps({
                "error": "Failed to start server",
                "details": str(e)
            }), file=sys.stderr)
            sys.exit(1)
    else:
        url = args.url

    client = TerminalClient(base_url=url)

    try:
        if args.command == "create":
            env = json.loads(args.env) if args.env else None
            session_id = client.create_session(
                command=args.cmd,
                rows=args.rows,
                cols=args.cols,
                env=env
            )
            print(json.dumps({"session_id": session_id}))

        elif args.command == "list":
            sessions = client.list_sessions()
            print(json.dumps({"sessions": sessions}))

        elif args.command == "info":
            info = client.get_session_info(args.session_id)
            print(json.dumps(info))

        elif args.command == "delete":
            client.delete_session(args.session_id)
            print(json.dumps({"status": "deleted"}))

        elif args.command == "send":
            # Process escape sequences (\n, \r, \t, \x1b, etc.)
            import codecs
            try:
                # Decode escape sequences (handles \n, \r, \t, \xNN, etc.)
                text = codecs.decode(args.text, 'unicode_escape')
            except Exception:
                # If decoding fails, use text as-is
                text = args.text
            client.write_input(args.session_id, text)
            print(json.dumps({"status": "sent"}))

        elif args.command == "get-output":
            output = client.get_output(args.session_id, clear=not args.no_clear)
            print(output, end="")

        elif args.command == "get-text":
            text = client.get_text(
                args.session_id,
                strip_ansi_codes=not args.no_strip_ansi,
                source=args.source
            )
            print(text, end="")

        elif args.command == "get-screen":
            screen = client.get_screen(args.session_id)
            print(json.dumps(screen))

        elif args.command == "wait-text":
            found = client.wait_for_text(
                args.session_id,
                args.text,
                timeout=args.timeout,
                poll_interval=args.poll_interval
            )
            print(json.dumps({"found": found}))

        elif args.command == "wait-quiet":
            stable = client.wait_for_quiet(
                args.session_id,
                duration=args.duration,
                timeout=args.timeout
            )
            print(json.dumps({"stable": stable}))

        elif args.command == "attach":
            # This needs async
            asyncio.run(attach_interactive(client, args.session_id))

        elif args.command == "web":
            # Check if session_or_command is a session ID (UUID format)
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

            if re.match(uuid_pattern, args.session_or_command):
                # It's a session ID - open existing session
                session_id = args.session_or_command
            else:
                # It's a command - create new session and open
                command = [args.session_or_command] + args.cmd_args if args.cmd_args else [args.session_or_command]
                session_id = client.create_session(
                    command=command,
                    rows=args.rows,
                    cols=args.cols
                )
                print(json.dumps({"session_id": session_id, "command": command}))

            # Open session in browser
            web_url = f"{url}/?session={session_id}"
            print(json.dumps({"url": web_url, "session_id": session_id}))
            webbrowser.open(web_url)

    except TimeoutError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except httpx.ConnectError as e:
        print(json.dumps({
            "error": f"Cannot connect to term-wrapper server at {client.base_url}",
            "details": str(e)
        }), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


async def attach_interactive(client: TerminalClient, session_id: str):
    """Attach to a session interactively."""
    try:
        print(f"Attaching to session {session_id}...")
        print("(Press Ctrl+C to detach)\n")
        await client.interactive_session(session_id)
    except KeyboardInterrupt:
        print("\n\nDetached from session")


async def main():
    """Main entry point for backwards compatibility."""
    sync_main()


if __name__ == "__main__":
    sync_main()
