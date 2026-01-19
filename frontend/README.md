# Web Frontend

Universal web-based terminal emulator for accessing any TUI application through your browser.

## Features

- **Full xterm.js integration** - Complete ANSI escape sequence support
- **Mobile-friendly** - Touch controls and responsive design
- **Real-time interaction** - WebSocket-based live terminal
- **Universal** - Works with any terminal application (vim, htop, bash, etc.)

## Quick Start

### 1. Start the Server

```bash
uv run python main.py
```

Server starts on `http://localhost:8000`

### 2. Open in Browser

The frontend is automatically available at:

```
http://localhost:8000/
```

### 3. Launch Any Application

Use URL parameters to launch specific applications:

```bash
# Launch htop
http://localhost:8000/?cmd=htop

# Launch vim with a file
http://localhost:8000/?cmd=vim&args=/tmp/myfile.txt

# Launch Python REPL
http://localhost:8000/?cmd=python3

# Launch bash
http://localhost:8000/?cmd=bash

# Launch Claude CLI
http://localhost:8000/?cmd=claude
```

## URL Parameters

- `cmd` - Command to run (required, default: `vim`)
- `args` - Arguments to pass to the command (optional)

**Examples:**

```bash
# Simple command
?cmd=htop

# Command with arguments
?cmd=vim&args=/tmp/test.txt

# Complex arguments
?cmd=bash&args=-c%20%22ls%20-la%22
```

## Convenience Commands

### One-line Launch Commands

Launch server and open browser in one command:

```bash
# Launch with htop
uv run python main.py & sleep 2 && open "http://localhost:8000/?cmd=htop"

# Launch with vim
uv run python main.py & sleep 2 && xdg-open "http://localhost:8000/?cmd=vim&args=/tmp/test.txt"
```

### Shell Function (Add to ~/.bashrc or ~/.zshrc)

```bash
# Launch term-wrapper frontend with any command
tweb() {
    local cmd="${1:-bash}"
    local args="${2:-}"

    # Start server in background if not running
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Starting term-wrapper server..."
        cd /path/to/term_wrapper
        uv run python main.py > /tmp/term-wrapper.log 2>&1 &
        sleep 2
    fi

    # Build URL
    local url="http://localhost:8000/?cmd=${cmd}"
    if [ -n "$args" ]; then
        url="${url}&args=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$args'))")"
    fi

    # Open in browser
    if command -v open > /dev/null; then
        open "$url"  # macOS
    elif command -v xdg-open > /dev/null; then
        xdg-open "$url"  # Linux
    else
        echo "Open in browser: $url"
    fi
}
```

**Usage:**

```bash
tweb htop                    # Launch htop
tweb vim /tmp/test.txt      # Launch vim with file
tweb python3                 # Launch Python REPL
tweb bash                    # Launch bash shell
```

## Mobile Support

The frontend includes mobile-specific features:

- **Virtual keyboard controls** - ESC, TAB, Ctrl+C, Ctrl+D, arrow keys
- **Touch-optimized** - Large buttons for easy tapping
- **Responsive design** - Adapts to phone/tablet screens
- **Full-screen mode** - Maximum screen real estate

Access from your phone:

```
http://<your-server-ip>:8000/?cmd=htop
```

## Architecture

```
Browser (xterm.js)
    ↕ WebSocket
FastAPI Server
    ↕ PTY
Terminal Application
```

The frontend:
1. Connects to the FastAPI backend via WebSocket
2. Creates a terminal session with your specified command
3. Renders output using xterm.js with full ANSI support
4. Sends keyboard input back to the terminal
5. Handles terminal resize events

## Development

### File Structure

```
frontend/
├── README.md          # This file
├── index.html         # Main HTML page
├── app.js            # JavaScript application logic
└── style.css         # Styles and responsive design
```

### Customization

**Change default command:**

Edit `app.js` line 29:
```javascript
const cmd = params.get('cmd') || 'bash';  // Change 'bash' to your preferred default
```

**Modify appearance:**

Edit `style.css` to customize colors, fonts, and layout.

**Add custom buttons:**

Edit `index.html` to add more mobile control buttons in the `#mobile-controls` section.

## Troubleshooting

**Frontend shows "Connecting to terminal..." forever:**

- Check server is running: `curl http://localhost:8000/health`
- Check browser console for WebSocket errors
- Verify firewall allows port 8000

**Application doesn't render properly:**

- Some apps require specific terminal size - refresh page
- Check app works via CLI first: `term-wrapper create <app>`
- View terminal output: `term-wrapper get-output <session_id>`

**Mobile controls not working:**

- Ensure you're using a touch device or mobile browser
- Try refreshing the page
- Check browser console for JavaScript errors

## Examples

### System Monitoring

```bash
# Monitor system with htop
http://localhost:8000/?cmd=htop

# Monitor with custom refresh
http://localhost:8000/?cmd=htop&args=-d%2050
```

### Text Editing

```bash
# Create new file
http://localhost:8000/?cmd=vim&args=/tmp/newfile.txt

# Edit existing file
http://localhost:8000/?cmd=nano&args=/etc/hosts
```

### Interactive Shells

```bash
# Python REPL
http://localhost:8000/?cmd=python3

# Node.js REPL
http://localhost:8000/?cmd=node

# Bash shell
http://localhost:8000/?cmd=bash
```

### Development Tools

```bash
# Run tests interactively
http://localhost:8000/?cmd=pytest&args=-v

# Interactive git
http://localhost:8000/?cmd=git&args=status
```

## Tips

1. **Bookmark frequently used apps** - Save URLs with your most-used commands
2. **Use keyboard shortcuts** - xterm.js supports standard terminal shortcuts
3. **Fullscreen mode** - Press F11 in most browsers for fullscreen
4. **Multiple tabs** - Open different apps in separate browser tabs
5. **Mobile access** - Access from your phone when away from desk

## See Also

- [Main README](../README.md) - Project overview and API documentation
- [CLI Documentation](../README.md#cli-subcommands) - Command-line interface
- [API Reference](../docs/API.md) - REST and WebSocket API details
