# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
