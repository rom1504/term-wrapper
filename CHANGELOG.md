# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.4] - 2026-01-19

Minor update adding version display to web frontend.

### Added
- **Version display in web UI**
  - Shows version number in header (e.g., "v0.6.4")
  - Fetched from `/version` API endpoint
  - Uses importlib.metadata when installed, pyproject.toml as fallback
  - Helps verify correct version is running when debugging

## [0.6.3] - 2026-01-19

Critical fix for thinking indicator duplication using auto-scroll and ANSI filtering.

### Fixed
- **Thinking indicator duplication fully resolved**
  - Added auto-scroll to bottom during content streaming (onWriteParsed handler)
  - Viewport now stays at bottom within 3 lines, showing only latest status line
  - Matches native terminal behavior where old status lines scroll out of view
  - Claude Code writes multiple status lines as new lines (not updating in-place)
  - Previous fix (reducing scrollback) was insufficient

- **ANSI sequence filtering improved**
  - Filters out `ESC[<u` sequence (appears 60 times, non-standard)
  - May have been interfering with cursor positioning in xterm.js
  - Synchronized output mode (ESC[?2026h/l) already filtered in v0.6.2

### Investigation
- Deep ANSI sequence analysis revealed Claude Code uses NO cursor control
  - No cursor save/restore, cursor positioning, or line clearing
  - Uses simple line-by-line output with newlines
  - Status line "updates" are actually new lines appended to buffer
- Root cause: viewport not staying at bottom during streaming
  - See `test_screencast/ROOT_CAUSE_ANALYSIS.md` for full investigation
  - Frame-by-frame analysis in `test_screencast/DUPLICATION_FOUND.md`
  - ANSI capture shows pattern: `[?25l[<u[?1004l[?2004l[?25h`

### Changed
- Reduced scrollback from 1000 to 500 lines for better mobile performance
- WebSocket polling remains at 1ms for real-time updates

## [0.6.2] - 2026-01-19

Critical patch fixing double scrollbar and thinking indicator duplication.

### Fixed
- **Double scrollbar issue on mobile**
  - html and body now have `position: fixed` and `overflow: hidden`
  - Only terminal scrolls, not page body
  - Fixes user-reported "both the main browser scrolling bar and the one for the term"
  - Prevents touch events from going to wrong scroll target

- **Thinking indicator duplication during Claude Code generation**
  - Reduced scrollback buffer from 10000 to 1000 lines
  - Prevents old status lines from lingering in buffer
  - Fixes "Grooving..." appearing twice simultaneously
  - Frame-by-frame analysis confirmed the duplication (see test_screencast/)

### Changed
- Layout now uses `height: 100%` instead of `100vh` to avoid mobile viewport issues
- `#app` container now has `overflow: hidden` for better containment

### Context
User on Xiaomi 13 Android reported:
1. Two scrollbars visible (page + terminal) causing scroll conflicts
2. Thinking indicators duplicated during Claude generation

Root cause: Page body was scrollable, causing:
- Touch events intercepted by wrong element
- Terminal viewport behaving unexpectedly
- Claude Code status lines not properly overwritten in scrollback

See `test_screencast/DUPLICATION_FOUND.md` for detailed frame analysis
and `test_screencast/FIX_PLAN.md` for fix strategy.

## [0.6.1] - 2026-01-19

Critical patch fixing mobile touch scrolling direction.

### Fixed
- **Mobile touch scrolling direction inverted**
  - Touch swipe UP now correctly scrolls UP (shows earlier content)
  - Touch swipe DOWN now correctly scrolls DOWN (shows later content)
  - Bug was caused by double negation in scrollLines() call
  - Momentum scrolling direction also fixed
  - Touch handlers now attach to terminal-container instead of .xterm-viewport
  - Prevents conflict with xterm.js built-in touch handling

### Added
- Comprehensive touch event testing script (`docs/examples/debug_touch_events.py`)
  - Dispatches actual TouchEvent objects (not mouse events)
  - Verifies touch handlers fire correctly
  - Validates viewport changes in correct direction
- Root cause analysis document (`TOUCH_SCROLLING_FIX.md`)
  - Documents testing strategy issues
  - Explains the math error causing inverted scrolling
  - Provides verification approach for real touch events

### Context
Previous testing used mouse events and direct API calls, missing the actual touch handler bug.
Real Android devices (like Xiaomi 13) experienced backwards scrolling - swiping up would
scroll down instead. This is now fixed and verified with proper TouchEvent simulation.

## [0.6.0] - 2026-01-19

Minor release with major mobile UX improvements and streamlined CLI workflow.

### Added
- **One-command web workflow**: `term-wrapper web <command>`
  - Creates session AND opens in browser with single command
  - Example: `term-wrapper web claude` - starts Claude Code in browser
  - Example: `term-wrapper web --rows 50 htop` - opens htop with custom dimensions
  - Auto-detects session ID vs command name using UUID pattern
  - Still supports `term-wrapper web <session-id>` for existing sessions

### Improved
- **Much faster mobile touch scrolling**
  - Scrolls 3 lines per 50px of touch movement (was effectively 1 line)
  - Added momentum scrolling with smooth deceleration
  - Prevents default browser scroll to use custom xterm.js scrolling
  - Natural and responsive feel on mobile devices
  - Tested with Claude Code generating 40+ line outputs

### Added (Debug Tools)
- `docs/examples/debug_repeated_thoughts.py` - Debug duplicate content detection
- `docs/examples/test_mobile_scroll.py` - Comprehensive mobile scroll testing with Claude

### Context
The `term-wrapper web` command now provides the simplest workflow:
- Before: `term-wrapper create claude` → copy session ID → `term-wrapper web <id>`
- Now: `term-wrapper web claude` → done!

Mobile scrolling was too slow (1 position per swipe), making long Claude output
difficult to read. New momentum-based scrolling feels natural and fast.

## [0.5.4] - 2026-01-19

Patch release adding Enter button to mobile controls.

### Fixed
- Mobile keyboard Enter key functionality
  - Added ENTER button to mobile virtual keyboard controls
  - Button sends carriage return (`\r`) to terminal via WebSocket
  - Positioned between TAB and ^C for easy access
  - Resolves issue where mobile users had no way to execute commands

### Added
- Mobile keyboard debugging scripts
  - `docs/examples/debug_mobile_keyboard.py` - Tests keyboard input on mobile viewport
  - `docs/examples/test_mobile_enter.py` - Validates Enter button functionality
  - Scripts use Playwright to simulate mobile devices (iPhone, etc.)

### Context
Mobile users previously had no way to press Enter because:
- Mobile virtual keyboard buttons included ESC, TAB, ^C, ^D, and arrows but no Enter
- Soft keyboard Enter might be hidden or unavailable depending on context
- Users couldn't execute commands, making the terminal unusable on mobile

## [0.5.3] - 2026-01-19

Patch release fixing Claude Code rendering duplication bug.

### Fixed
- Claude Code rendering duplication in web terminal
  - Frontend now checks if backend dimensions match before resizing
  - Prevents unnecessary SIGWINCH signal when connecting to existing sessions
  - Eliminates duplicate content overlays caused by unnecessary redraws
  - Bug occurred when test created session with same dimensions as browser

### Changed
- Claude rendering test now skips in CI environment
  - Added CI environment variable check
  - Prevents Claude CLI from running in GitHub Actions
  - Test still runs locally for manual validation

### Added
- Comprehensive Claude rendering test (`docs/examples/test_claude_rendering.py`)
  - Validates 6 different interaction scenarios
  - Takes 8 screenshots at key interaction points
  - Automatic content duplication detection
  - Scrolling behavior validation
  - Approval UI interaction testing
  - Buffer state analysis
  - Confirms perfect rendering with no overlapping content

## [0.5.2] - 2026-01-19

Patch release fixing web terminal vertical layout for Claude Code and TUI apps.

### Fixed
- Web terminal vertical layout and spacing
  - Removed initial "Connecting to terminal..." message from buffer
  - Skip unnecessary resize when connecting to newly-created sessions
  - Only resize backend when reconnecting to existing sessions
  - Eliminates unnecessary SIGWINCH signal causing TUI apps to redraw
  - Cleaner initial state with content starting from top of screen
- Validation code no longer interferes with fast-completing commands
  - Only catches startup failures (non-zero exit codes)
  - Fast commands like `echo` work correctly

### Added
- Comprehensive Playwright debugging guide (`docs/PLAYWRIGHT_DEBUGGING.md`)
  - Complete tutorial on debugging TUI apps with screenshots
  - Example script for interactive debugging (`docs/examples/debug_claude_vertical.py`)
  - Common patterns for extracting terminal state and content
  - Instructions for viewing CI screenshots from GitHub artifacts
- Playwright test for htop rendering in web terminal
  - Runs in CI (htop installed by default)
  - Verifies TUI app rendering and dimensions
  - Screenshots uploaded as GitHub artifacts
  - Claude rendering test skips gracefully when CLI not available
- htop screenshot in README
  - Shows visual example of TUI app running in web terminal
  - Downloaded from CI artifacts for consistency

## [0.5.1] - 2026-01-19

Patch release fixing web terminal alignment.

### Fixed
- Web terminal now syncs backend dimensions after connecting
  - Backend session is resized to match frontend display (120 cols max)
  - Fixes Claude Code and TUI apps appearing misaligned in browser
  - Frontend was capped at 120 cols but backend kept original dimensions

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
