"""PTY-based terminal emulator."""

import asyncio
import os
import pty
import select
import signal
import struct
import fcntl
import termios
from typing import Callable, Optional


class Terminal:
    """A pseudo-terminal that can run TUI applications."""

    def __init__(self, rows: int = 24, cols: int = 80):
        """Initialize terminal with specified dimensions.

        Args:
            rows: Number of terminal rows
            cols: Number of terminal columns
        """
        self.rows = rows
        self.cols = cols
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.output_callback: Optional[Callable[[bytes], None]] = None
        self._running = False
        self._read_task: Optional[asyncio.Task] = None

    def spawn(self, command: list[str], env: Optional[dict] = None) -> None:
        """Spawn a process in the terminal.

        Args:
            command: Command and arguments to execute
            env: Optional environment variables
        """
        if self._running:
            raise RuntimeError("Terminal already has a running process")

        # Create PTY
        self.pid, self.master_fd = pty.fork()

        if self.pid == 0:
            # Child process
            if env:
                os.environ.update(env)
            os.execvp(command[0], command)
        else:
            # Parent process
            self._set_terminal_size(self.rows, self.cols)
            self._running = True

            # Set non-blocking mode
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def _set_terminal_size(self, rows: int, cols: int) -> None:
        """Set the terminal window size.

        Args:
            rows: Number of rows
            cols: Number of columns
        """
        if self.master_fd is None:
            return

        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)

    def resize(self, rows: int, cols: int) -> None:
        """Resize the terminal.

        Args:
            rows: New number of rows
            cols: New number of columns
        """
        self.rows = rows
        self.cols = cols
        self._set_terminal_size(rows, cols)

        # Send SIGWINCH to the child process
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGWINCH)
            except ProcessLookupError:
                pass

    async def start_reading(self) -> None:
        """Start asynchronously reading from the terminal."""
        if not self._running or self.master_fd is None:
            raise RuntimeError("No process running in terminal")

        self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Continuously read output from the terminal."""
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                # Use select to wait for data
                ready, _, _ = await loop.run_in_executor(
                    None, select.select, [self.master_fd], [], [], 0.1
                )

                if ready:
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        # EOF - process has terminated
                        self._running = False
                        break

                    if self.output_callback:
                        self.output_callback(data)

            except OSError:
                # Process terminated
                self._running = False
                break

    def write(self, data: bytes) -> None:
        """Write data to the terminal input.

        Args:
            data: Bytes to write to terminal
        """
        if not self._running or self.master_fd is None:
            raise RuntimeError("No process running in terminal")

        os.write(self.master_fd, data)

    def is_alive(self) -> bool:
        """Check if the terminal process is still running.

        Returns:
            True if process is running, False otherwise
        """
        if not self._running or self.pid is None:
            return False

        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid == 0:
                return True
            self._running = False
            return False
        except ChildProcessError:
            self._running = False
            return False

    def kill(self) -> None:
        """Terminate the terminal process."""
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass

        self._running = False

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()

    async def wait(self) -> int:
        """Wait for the terminal process to complete.

        Returns:
            Exit code of the process
        """
        if not self.pid:
            return -1

        loop = asyncio.get_event_loop()
        _, status = await loop.run_in_executor(None, os.waitpid, self.pid, 0)

        self._running = False
        return os.WEXITSTATUS(status)
