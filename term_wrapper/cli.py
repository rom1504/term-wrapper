"""CLI client for terminal wrapper."""

import asyncio
import sys
import termios
import tty
from typing import Optional
import httpx
import websockets
import json


class TerminalClient:
    """Client for interacting with terminal wrapper backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client.

        Args:
            base_url: Base URL of the backend server
        """
        self.base_url = base_url
        self.http_client = httpx.Client(base_url=base_url, timeout=10.0)

    def create_session(
        self, command: list[str], rows: int = 24, cols: int = 80
    ) -> str:
        """Create a new terminal session.

        Args:
            command: Command to run
            rows: Terminal rows
            cols: Terminal columns

        Returns:
            Session ID
        """
        response = self.http_client.post(
            "/sessions",
            json={"command": command, "rows": rows, "cols": cols},
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
