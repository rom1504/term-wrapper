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

    def spawn(self, command: list[str], env: Optional[dict] = None, raw_mode: bool = True) -> None:
        """Spawn a process in the terminal.

        Args:
            command: Command and arguments to execute
            env: Optional environment variables
            raw_mode: Whether to set the PTY to raw mode (default True)
        """
        if self._running:
            raise RuntimeError("Terminal already has a running process")

        # Auto-detect scripts without shebangs and wrap in bash
        if command and os.path.exists(command[0]) and os.path.isfile(command[0]):
            try:
                with open(command[0], 'rb') as f:
                    first_bytes = f.read(512)  # Read more to check if it's text
                    # Skip if it's a binary (ELF, compiled executable, etc.)
                    if first_bytes.startswith(b'\x7fELF') or b'\x00' in first_bytes[:256]:
                        pass  # It's binary, let execvp handle it
                    # If file doesn't start with shebang (#!) and looks like text, wrap in bash
                    elif first_bytes[:2] != b'#!' and os.access(command[0], os.X_OK):
                        command = ['bash', command[0]] + command[1:]
            except (OSError, IOError):
                pass  # If we can't read it, let execvp try

        # Create PTY
        self.pid, self.master_fd = pty.fork()

        if self.pid == 0:
            # Child process
            try:
                if env:
                    os.environ.update(env)
                os.execvp(command[0], command)
            except Exception as e:
                # If exec fails, print error and exit child process
                import sys
                print(f"Failed to execute command: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Parent process
            self._set_terminal_size(self.rows, self.cols)
            self._running = True

            # Set the PTY to raw mode if requested (needed for TUI apps)
            if raw_mode:
                try:
                    import tty
                    # Set to raw mode for proper TUI app support
                    tty.setraw(self.master_fd)
                except Exception:
                    # If raw mode fails, continue anyway
                    pass

            # Set non-blocking mode
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Check if child process failed to start
            import time
            time.sleep(0.1)  # Give child a moment to start
            try:
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid != 0:
                    # Child exited immediately
                    exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                    if exit_code != 0:
                        # Non-zero exit = command failed to start
                        self._running = False
                        os.close(self.master_fd)
                        self.master_fd = None
                        raise RuntimeError(
                            f"Command failed to start (exit code {exit_code}). "
                            f"Command: {command}. "
                            f"This may indicate: (1) command not found, (2) exec format error, "
                            f"or (3) missing dependencies. Try wrapping in a shell: "
                            f"['bash', '-c', '{' '.join(command)}']"
                        )
                    # else: exit code 0 means command ran successfully and finished quickly
                    # Let start_reading() handle it normally - don't mark as not running
            except ChildProcessError:
                pass  # Child is still running, which is good

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
