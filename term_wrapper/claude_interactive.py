"""Interactive Claude CLI helper using term-wrapper."""

import time
from typing import Optional
from .cli import TerminalClient


class ClaudeInteractive:
    """Helper for running Claude CLI interactively via term-wrapper."""

    def __init__(self, work_dir: str = "/tmp", base_url: str = "http://localhost:8000"):
        """Initialize Claude interactive session.

        Args:
            work_dir: Working directory for Claude
            base_url: Term-wrapper API URL
        """
        self.work_dir = work_dir
        self.client = TerminalClient(base_url=base_url)
        self.session_id: Optional[str] = None

    def start(self):
        """Start Claude CLI session."""
        self.session_id = self.client.create_session(
            command=["bash", "-c", f"cd {self.work_dir} && claude --dangerously-skip-permissions"],
            rows=40,
            cols=120
        )
        time.sleep(3)

    def send_request(self, request: str, wait_time: int = 20) -> str:
        """Send request to Claude and wait for completion.

        Args:
            request: Request text to send to Claude
            wait_time: Maximum seconds to wait for completion

        Returns:
            Screen content after completion
        """
        if not self.session_id:
            raise RuntimeError("Session not started. Call start() first.")

        # Type the request
        self.client.write_input(self.session_id, request)
        time.sleep(0.5)

        # Try multiple submission methods
        for key in ["\n", "\t", "\r"]:
            self.client.write_input(self.session_id, key)
            time.sleep(1)

        # Monitor for completion
        for _ in range(wait_time):
            time.sleep(1)
            screen_data = self.client.get_screen(self.session_id)
            lines = screen_data['lines']
            screen_text = '\n'.join(lines)

            # Auto-confirm prompts
            if 'Do you want to create' in screen_text or 'Yes' in screen_text:
                self.client.write_input(self.session_id, "\n")
                time.sleep(1)

            # Check if done (idle prompt returned)
            if '❯ Try' in screen_text[-1000:]:
                # Check if no active operations
                if 'interrupt' not in screen_text.lower():
                    return screen_text

        return '\n'.join(lines)

    def get_screen(self) -> str:
        """Get current screen content."""
        if not self.session_id:
            raise RuntimeError("Session not started")
        screen_data = self.client.get_screen(self.session_id)
        return '\n'.join(screen_data['lines'])

    def close(self):
        """Close Claude session."""
        if self.session_id:
            self.client.delete_session(self.session_id)
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()
