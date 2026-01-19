# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Auto-start server functionality in CLI client
  - Server automatically starts when running any `term-wrapper` command
  - No manual server startup required
  - Server picks an available port (port 0) automatically
  - Port saved to `~/.term-wrapper/port` for subsequent commands
  - Improved UX - single command to get started

### Changed
- CLI now auto-discovers or starts server if `--url` not specified
- README and skill documentation updated to reflect auto-start behavior
- Web frontend documentation updated with auto-start instructions

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
