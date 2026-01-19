"""Server manager for auto-starting the term-wrapper server."""

import os
import subprocess
import sys
import time
import httpx
from pathlib import Path


class ServerManager:
    """Manages the term-wrapper server lifecycle."""

    def __init__(self):
        """Initialize server manager."""
        self.state_dir = Path.home() / ".term-wrapper"
        self.port_file = self.state_dir / "port"
        self.pid_file = self.state_dir / "pid"
        self.log_file = self.state_dir / "server.log"

        # Create state directory if it doesn't exist
        self.state_dir.mkdir(exist_ok=True)

    def get_server_url(self) -> str:
        """Get the server URL, starting server if needed.

        Returns:
            Server URL (e.g., "http://localhost:12345")
        """
        # Try to read existing port
        if self.port_file.exists():
            try:
                port = int(self.port_file.read_text().strip())
                url = f"http://localhost:{port}"

                # Verify server is actually running
                if self._is_server_running(url):
                    return url
            except (ValueError, OSError):
                pass

        # Server not running, start it
        return self._start_server()

    def _is_server_running(self, url: str) -> bool:
        """Check if server is running at the given URL.

        Args:
            url: Server URL to check

        Returns:
            True if server is responding
        """
        try:
            response = httpx.get(f"{url}/health", timeout=1.0)
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def _start_server(self) -> str:
        """Start the server in background.

        Returns:
            Server URL
        """
        # Start server with port 0 (auto-select)
        log_file = open(self.log_file, "w")

        # Use python -m to run the server module
        process = subprocess.Popen(
            [sys.executable, "-m", "term_wrapper.server", "--port", "0"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # Detach from parent
        )

        # Save PID
        self.pid_file.write_text(str(process.pid))

        # Wait for server to start and parse port from log
        port = self._wait_for_server_start()

        # Save port
        self.port_file.write_text(str(port))

        return f"http://localhost:{port}"

    def _wait_for_server_start(self, timeout: float = 5.0) -> int:
        """Wait for server to start and extract the port.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Port number the server is listening on

        Raises:
            RuntimeError: If server doesn't start within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.log_file.exists():
                try:
                    log_content = self.log_file.read_text()

                    # Look for "Uvicorn running on http://0.0.0.0:PORT" in log
                    for line in log_content.splitlines():
                        if "Uvicorn running on" in line:
                            # Extract port from "http://0.0.0.0:PORT"
                            if "http://" in line:
                                url_part = line.split("http://")[1].split()[0]
                                port_str = url_part.split(":")[-1]
                                port = int(port_str)

                                # Verify server is responding
                                if self._is_server_running(f"http://localhost:{port}"):
                                    return port
                except (OSError, ValueError, IndexError):
                    pass

            time.sleep(0.1)

        raise RuntimeError(
            f"Server failed to start within {timeout}s. "
            f"Check log file: {self.log_file}"
        )
