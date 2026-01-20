"""Server manager for auto-starting the term-wrapper server."""

import os
import subprocess
import sys
import time
import signal
import httpx
from pathlib import Path
import fcntl


class ServerManager:
    """Manages the term-wrapper server lifecycle."""

    def __init__(self):
        """Initialize server manager."""
        self.state_dir = Path.home() / ".term-wrapper"
        self.port_file = self.state_dir / "port"
        self.pid_file = self.state_dir / "pid"
        self.log_file = self.state_dir / "server.log"
        self.lock_file = self.state_dir / "server.lock"

        # Create state directory if it doesn't exist
        self.state_dir.mkdir(exist_ok=True)

    def get_server_url(self, host: str = None, port: int = None) -> str:
        """Get the server URL, starting server if needed.

        Args:
            host: Host to bind to (default: None = auto-discover existing server or use 127.0.0.1)
            port: Port to bind to (default: None = auto-discover existing server or use 0 for auto-assign)

        Returns:
            Server URL (e.g., "http://localhost:12345")
        """
        # If custom host/port specified, always start new server (don't auto-discover)
        if host is not None or port is not None:
            return self._start_server_with_lock(host=host or "127.0.0.1", port=port or 0)

        # Try to read existing port (auto-discovery mode)
        if self.port_file.exists():
            try:
                port = int(self.port_file.read_text().strip())
                url = f"http://localhost:{port}"

                # Verify server is actually running
                if self._is_server_running(url):
                    return url
            except (ValueError, OSError):
                pass

        # Server not running, start it with file locking
        return self._start_server_with_lock(host="127.0.0.1", port=0)

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

    def _start_server_with_lock(self, host: str, port: int) -> str:
        """Start server with file locking to prevent concurrent starts.

        Args:
            host: Host to bind to
            port: Port to bind to (0 = auto-assign)

        Returns:
            Server URL
        """
        # Use file locking to prevent concurrent server starts
        lock_fd = open(self.lock_file, 'w')
        try:
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Double-check server isn't running (another process might have started it)
            # Only check if using auto-discovery (port 0 and localhost)
            if host == "127.0.0.1" and port == 0 and self.port_file.exists():
                try:
                    existing_port = int(self.port_file.read_text().strip())
                    url = f"http://localhost:{existing_port}"
                    if self._is_server_running(url):
                        return url
                except (ValueError, OSError):
                    pass

            # Start the server
            return self._start_server(host=host, port=port)

        except BlockingIOError:
            # Another process is starting the server, wait for it
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)  # Wait for lock

            # Read the port file that the other process should have created
            for _ in range(50):  # Wait up to 5 seconds
                if self.port_file.exists():
                    try:
                        port = int(self.port_file.read_text().strip())
                        url = f"http://localhost:{port}"
                        if self._is_server_running(url):
                            return url
                    except (ValueError, OSError):
                        pass
                time.sleep(0.1)

            raise RuntimeError("Server started by another process but couldn't connect")
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()

    def _start_server(self, host: str, port: int) -> str:
        """Start the server in background.

        Args:
            host: Host to bind to
            port: Port to bind to (0 = auto-assign)

        Returns:
            Server URL
        """
        # Start server
        log_file = open(self.log_file, "w")

        # Use python -m to run the server module
        process = subprocess.Popen(
            [sys.executable, "-m", "term_wrapper.server", "--host", host, "--port", str(port)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # Detach from parent
        )

        # Save PID
        self.pid_file.write_text(str(process.pid))

        # Wait for server to start and parse port from log
        actual_port, actual_host = self._wait_for_server_start()

        # Save port (for auto-discovery)
        self.port_file.write_text(str(actual_port))

        # Return URL with the appropriate host
        display_host = "localhost" if actual_host in ("127.0.0.1", "0.0.0.0", "localhost") else actual_host
        return f"http://{display_host}:{actual_port}"

    def _wait_for_server_start(self, timeout: float = 5.0) -> tuple[int, str]:
        """Wait for server to start and extract the port and host.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Tuple of (port, host) the server is listening on

        Raises:
            RuntimeError: If server doesn't start within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.log_file.exists():
                try:
                    log_content = self.log_file.read_text()

                    # Look for "Uvicorn running on http://HOST:PORT" in log
                    for line in log_content.splitlines():
                        if "Uvicorn running on" in line:
                            # Extract host and port from "http://HOST:PORT"
                            if "http://" in line:
                                url_part = line.split("http://")[1].split()[0]
                                host_port = url_part.rsplit(":", 1)
                                if len(host_port) == 2:
                                    host, port_str = host_port
                                    port = int(port_str)

                                    # Verify server is responding
                                    check_host = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
                                    if self._is_server_running(f"http://{check_host}:{port}"):
                                        return (port, host)
                except (OSError, ValueError, IndexError):
                    pass

            time.sleep(0.1)

        raise RuntimeError(
            f"Server failed to start within {timeout}s. "
            f"Check log file: {self.log_file}"
        )

    def stop_server(self) -> dict:
        """Stop the running server.

        Returns:
            dict with status information
        """
        # Check if PID file exists
        if not self.pid_file.exists():
            return {"status": "not_running", "message": "No server PID file found"}

        try:
            pid = int(self.pid_file.read_text().strip())
        except (ValueError, OSError) as e:
            return {"status": "error", "message": f"Failed to read PID file: {e}"}

        # Check if process is actually running
        try:
            os.kill(pid, 0)  # Signal 0 just checks if process exists
        except OSError:
            # Process doesn't exist, clean up stale files
            self._cleanup_state_files()
            return {"status": "not_running", "message": "Server was not running (cleaned up stale files)"}

        # Try graceful shutdown first (SIGTERM)
        try:
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit (up to 5 seconds)
            for _ in range(50):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except OSError:
                    # Process has exited
                    self._cleanup_state_files()
                    return {"status": "stopped", "message": f"Server (PID {pid}) stopped successfully"}

            # Force kill if still running
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
            self._cleanup_state_files()
            return {"status": "stopped", "message": f"Server (PID {pid}) force-stopped"}

        except OSError as e:
            return {"status": "error", "message": f"Failed to stop server: {e}"}

    def _cleanup_state_files(self):
        """Clean up state files."""
        for file in [self.port_file, self.pid_file]:
            if file.exists():
                try:
                    file.unlink()
                except OSError:
                    pass
