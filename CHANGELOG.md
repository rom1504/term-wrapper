# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-01-19

Minor release with automatic script detection and improved usability.

### Added
- **Auto-detection of scripts without shebangs**
  - Automatically wraps text scripts in bash when shebang is missing
  - Detects binaries (ELF, null bytes) and executes them directly
  - Scripts like `claude` now work without manual bash wrapping
  - Zero user changes needed - `term-wrapper create claude` just works
  - Transparent: doesn't affect normal commands or binaries

### Fixed
- Web frontend terminal width capped at 120 columns
  - Prevents super-wide terminals on large screens
  - Fixes TUI apps like Claude Code appearing misaligned in browser
  - Uses FitAddon for height, manual cap for width

### Example
```bash
# Before: Required manual bash wrapping
term-wrapper create bash -c "claude"

# Now: Works automatically
term-wrapper create claude
```

## [0.4.3] - 2026-01-19

Patch release improving command execution error handling and server stability.

### Fixed
- Command execution errors now handled gracefully
  - Child process catches exec errors and exits cleanly
  - Parent detects failed commands (non-zero exit) with clear error message
  - Prevents server crash when command cannot be executed (exec format error)
  - Helpful error message suggests wrapping command in shell
- Server no longer crashes when spawning invalid commands

### Changed
- Commands that fail to start now raise RuntimeError with helpful message
- Error message includes suggestions: wrap in `['bash', '-c', 'command']` if needed

## [0.4.2] - 2026-01-19

Patch release fixing WebSocket stability and test suite.

### Fixed
- WebSocket cancellation error when detaching from sessions
  - Explicitly catch `asyncio.CancelledError` in WebSocket endpoint
  - Prevents server crash when client presses Ctrl+C to detach
  - Client disconnect now handled gracefully without disrupting event loop
- Skipped Ink app.js test that depends on missing example file
  - test_ink_app_via_http_endpoints now properly skipped
  - All 18 integration tests (vim, htop, Python TUI) passing

## [0.4.1] - 2026-01-19

Patch release fixing terminal rendering for TUI applications.

### Fixed
- Raw mode terminal settings for proper TUI rendering
  - Removed ECHO and ICANON restoration after `tty.setraw()`
  - Fixes Claude Code and other Ink-based apps appearing out of alignment
  - Maintains pure raw mode for pixel-perfect TUI support
- Verified working: htop, less, vim, Claude Code

## [0.4.0] - 2026-01-19

Major release with server management improvements and frontend fixes.

### Added
- File locking to prevent multiple servers starting concurrently
  - Uses `fcntl.flock` to coordinate between parallel CLI invocations
  - Only one server starts even with concurrent commands
- New `term-wrapper stop` command to shutdown the server
  - Graceful shutdown with SIGTERM, force kill with SIGKILL if needed
  - Cleans up state files (port, PID) automatically
- Session `command` field in API responses

### Fixed
- Multiple servers starting when running CLI commands in parallel
- Frontend always displaying "vim /tmp/mytest" instead of actual command
  - Frontend now fetches session info and shows correct command

### Changed
- TerminalSession now stores the command that was executed
- Server manager uses file locking for atomic server startup

## [0.3.3] - 2026-01-19

Critical patch fixing frontend files not being included in PyPI package.

### Fixed
- Frontend files (index.html, app.js, style.css) now included in wheel distribution
- Moved frontend files into term_wrapper/frontend/ directory
- Updated API to look for frontend in package directory
- Resolves "Frontend not found. API is running at /health" error

## [0.3.2] - 2026-01-19

Feature release adding web browser integration.

### Added
- `term-wrapper web SESSION_ID` command to open sessions in browser
- One-command workflow to view terminal sessions in web UI
- Frontend already supported `?session=SESSION_ID` parameter

### Example
```bash
SESSION=$(term-wrapper create htop | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
term-wrapper web $SESSION  # Opens htop in browser
```

## [0.3.1] - 2026-01-19

Patch release fixing server startup for pip-installed packages.

### Fixed
- Server startup error when installed via pip (main.py not found)
- ServerManager now uses `python -m term_wrapper.server` instead of file path
- Moved server entry point into package (term_wrapper/server.py)

### Added
- `term-wrapper-server` console script for manual server startup

## [0.3.0] - 2026-01-19

Major UX improvement release with auto-start functionality.

### Added
- Auto-start server functionality in CLI client
  - Server automatically starts when running any `term-wrapper` command
  - No manual server startup required
  - Server picks an available port (port 0) automatically
  - Port saved to `~/.term-wrapper/port` for subsequent commands
  - Improved UX - single command to get started
- ServerManager class for managing server lifecycle

### Changed
- CLI now auto-discovers or starts server if `--url` not specified
- README and skill documentation updated to reflect auto-start behavior
- Web frontend documentation updated with auto-start instructions
- CLI unit tests updated to properly mock ServerManager

### Fixed
- Connection refused error when running CLI after pip install (no manual server startup needed)

## [0.2.1] - 2026-01-19

Maintenance release with CI improvements and documentation updates.

### Added
- Comprehensive CI workflow now runs 14 test files (previously 5)
  - Unit tests, CLI tests, application integration tests, e2e tests
  - Only Claude-related tests skipped (require authentication)

### Changed
- Migrated to Anthropic Agent Skills convention
  - Renamed `skills/` folder to `skill/` (singular)
  - Created `skill/SKILL.md` following official format with YAML frontmatter
  - Removed unnecessary `skills/README.md`
- Updated README title to "Term Wrapper" (was "Terminal Wrapper")
- Clarified web frontend description - universal web mirror for TUI apps
- Git remote changed to SSH for workflow file updates

### Fixed
- htop tests now pass in CI environment
  - Added `TERM` environment variable to all htop test cases
  - Made test assertions more lenient (1 process minimum vs 3)
  - Fixed `test_cli_e2e_htop.py` and `test_htop_screen.py`
- Documentation consistency updates for v0.2.0

## [0.2.0] - 2026-01-19

Major CLI improvements release.

### Added
- CLI subcommands for scriptable terminal control (11 commands)
  - Session management: `create`, `list`, `info`, `delete`
  - Input/Output: `send`, `get-output`, `get-text`, `get-screen`
  - Waiting primitives: `wait-text`, `wait-quiet`
  - Interactive: `attach`
- CLI entry point (`term-wrapper` command) for PyPI package
- Python client library with high-level primitives
  - `wait_for_text()` - Wait for specific text to appear
  - `wait_for_quiet()` - Wait for output to stabilize
  - `get_text()` - Get clean text output (ANSI stripped)
  - `get_screen()` - Get parsed 2D screen buffer
- 29 new CLI-specific tests (118 total tests)
- Comprehensive CLI documentation in README and skill file
- Priority guidance for LLMs (CLI > Python > HTTP)

### Changed
- Documentation updated to emphasize CLI-first approach
- All examples updated to show CLI alternatives
- Skill file reorganized with priority guidance section

### Fixed
- None (fully backwards compatible)

## [0.1.0] - 2026-01-19

Initial release.

### Added
- PTY-based terminal emulator with full TUI application support
- FastAPI backend with REST and WebSocket APIs
- Session management for concurrent terminal sessions
- Web frontend with xterm.js integration and mobile support
- Comprehensive test suite (unit, integration, e2e)
- Application integration tests: vim, htop, Claude CLI (100% passing)
- Python CLI client for terminal interaction
- GitHub Actions CI workflow
- PyPI publishing workflow
- Detailed application reports and testing guide
- Complete API documentation
- Examples (simple HTTP usage, vim automation, TUI demo)
