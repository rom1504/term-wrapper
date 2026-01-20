// Terminal Wrapper Frontend Application

class TerminalApp {
    constructor() {
        this.term = null;
        this.fitAddon = null;
        this.webLinksAddon = null;
        this.ws = null;
        this.sessionId = null;
        this.apiBase = window.location.origin;
        this.isNewSession = false;

        // Touch handling
        this.touchStartY = 0;
        this.isScrolling = false;

        this.init();
    }

    init() {
        // Initialize terminal
        this.initTerminal();

        // Setup event listeners
        this.setupEventListeners();

        // Fetch and display version
        this.fetchVersion();

        // Get command from URL or use default
        const params = new URLSearchParams(window.location.search);
        const sessionId = params.get('session');
        const cmd = params.get('cmd') || 'vim';
        const args = params.get('args') || '/tmp/mytest';

        // Update filename display
        const filenameEl = document.getElementById('filename');
        if (filenameEl) {
            filenameEl.textContent = `${cmd} ${args}`;
        }

        // Auto-connect
        if (sessionId) {
            this.connectToExistingSession(sessionId);
        } else {
            // Auto-start command with the specified args
            this.connectToTerminal(cmd, args);
        }
    }

    async fetchVersion() {
        try {
            const response = await fetch(`${this.apiBase}/version`);
            if (response.ok) {
                const data = await response.json();
                const versionEl = document.getElementById('version');
                if (versionEl) {
                    versionEl.textContent = `v${data.version}`;
                }
            }
        } catch (error) {
            console.error('Failed to fetch version:', error);
        }
    }

    initTerminal() {
        // Create terminal instance
        this.term = new Terminal({
            cursorBlink: true,
            fontSize: 14,
            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
            theme: {
                background: '#000000',
                foreground: '#ffffff',
                cursor: '#ffffff',
                selection: 'rgba(255, 255, 255, 0.3)',
                black: '#000000',
                red: '#e06c75',
                green: '#98c379',
                yellow: '#d19a66',
                blue: '#61afef',
                magenta: '#c678dd',
                cyan: '#56b6c2',
                white: '#abb2bf',
            },
            scrollback: 500,  // Reduced from 10000 to 500 lines (balance between history and performance)
            tabStopWidth: 8,
        });

        // Load addons
        this.fitAddon = new FitAddon.FitAddon();
        this.term.loadAddon(this.fitAddon);

        this.webLinksAddon = new WebLinksAddon.WebLinksAddon();
        this.term.loadAddon(this.webLinksAddon);

        // Open terminal
        this.term.open(document.getElementById('terminal'));

        // Fit with reasonable dimensions (max 120 cols for TUI app compatibility)
        this.fitTerminal();

        // Handle input from terminal
        this.term.onData(data => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(new TextEncoder().encode(data));
            }
        });

        // Auto-scroll to bottom during content streaming to prevent duplicate status lines
        // Claude Code writes multiple status lines as new lines (not updating in-place)
        // so we need to keep viewport at bottom to show only the latest one
        this.lastWriteTime = Date.now();
        this.term.onWriteParsed(() => {
            this.lastWriteTime = Date.now();

            // If we're near the bottom (within 3 lines), auto-scroll to bottom
            // This prevents old thinking indicators from staying visible
            const buffer = this.term.buffer.active;
            const distanceFromBottom = buffer.length - (buffer.viewportY + this.term.rows);

            if (distanceFromBottom < 3) {
                this.term.scrollToBottom();
            }
        });

        // Handle terminal resize
        this.term.onResize(({ rows, cols }) => {
            if (this.sessionId) {
                this.resizeSession(rows, cols);
            }
        });

        // Custom touch scrolling for better mobile experience
        // CRITICAL: Use capture phase to intercept BEFORE xterm.js's Gesture system
        // xterm.js registers its own touch handlers that interfere with custom scrolling
        // We must use capture: true to intercept touch events first
        const terminalContainer = document.getElementById('terminal-container');
        if (terminalContainer) {
            terminalContainer.addEventListener('touchstart', this.handleTouchStart.bind(this), {
                passive: false,
                capture: true  // Intercept in capture phase before xterm.js
            });
            terminalContainer.addEventListener('touchmove', this.handleTouchMove.bind(this), {
                passive: false,
                capture: true  // Intercept in capture phase before xterm.js
            });
            terminalContainer.addEventListener('touchend', this.handleTouchEnd.bind(this), {
                passive: false,
                capture: true  // Intercept in capture phase before xterm.js
            });
        }
    }

    fitTerminal() {
        // Use FitAddon to calculate dimensions
        this.fitAddon.fit();

        // Cap columns at 120 for better TUI app compatibility
        // (Claude Code and many TUI apps expect standard terminal widths)
        const MAX_COLS = 120;
        if (this.term.cols > MAX_COLS) {
            // Calculate proportional dimensions
            const charWidth = Math.ceil(this.term.element.offsetWidth / this.term.cols);
            const targetWidth = charWidth * MAX_COLS;

            // Resize terminal with capped columns
            this.term.resize(MAX_COLS, this.term.rows);
        }
    }

    setupEventListeners() {
        // Disconnect button
        document.getElementById('disconnectBtn').addEventListener('click', () => {
            this.disconnect();
        });

        // Window resize
        window.addEventListener('resize', () => {
            if (this.fitAddon) {
                this.fitTerminal();
            }
        });

        // Mobile control buttons
        document.querySelectorAll('.mobile-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const key = btn.getAttribute('data-key');
                this.sendSpecialKey(key);
            });
        });

        // Visibility change (reconnect if needed)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.sessionId && (!this.ws || this.ws.readyState !== WebSocket.OPEN)) {
                this.reconnect();
            }
        });
    }

    async connectToTerminal(cmd, args) {
        this.setStatus('Starting terminal...', 'connecting');

        try {
            // Create terminal session with specified command
            const command = args ? [cmd, args] : [cmd];
            const response = await fetch(`${this.apiBase}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: command,
                    rows: this.term.rows,
                    cols: this.term.cols,
                    env: {
                        TERM: 'xterm-256color',
                        COLORTERM: 'truecolor',
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;

            // Update URL
            const url = new URL(window.location);
            url.searchParams.set('session', this.sessionId);
            window.history.pushState({}, '', url);

            // Clear terminal and connect
            this.term.clear();

            // Mark that this is a new session (no resize needed on connect)
            this.isNewSession = true;
            this.connectWebSocket();

        } catch (error) {
            this.setStatus(`Error: ${error.message}`, 'error');
            console.error('Connection error:', error);
        }
    }

    connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/sessions/${this.sessionId}/ws`;

        this.setStatus('Connecting to terminal...', 'connecting');

        this.ws = new WebSocket(wsUrl);
        this.ws.binaryType = 'arraybuffer';

        this.ws.onopen = () => {
            this.setStatus(`Connected (Session: ${this.sessionId})`, 'connected');
            document.getElementById('disconnectBtn').disabled = false;

            // Only resize if connecting to existing session
            // (new sessions are already created with correct dimensions)
            if (!this.isNewSession) {
                // Sync backend terminal size with frontend display
                // (in case session was created with different dimensions)
                this.resizeSession(this.term.rows, this.term.cols);
            }
            this.isNewSession = false;

            this.term.focus();
        };

        this.ws.onmessage = (event) => {
            if (typeof event.data === 'string') {
                if (event.data === '__TERMINAL_CLOSED__') {
                    this.term.writeln('\r\n\x1b[1;31m[Terminal session closed]\x1b[0m');
                    this.disconnect();
                }
            } else {
                // Binary data (terminal output)
                const text = new TextDecoder().decode(event.data);
                this.term.write(text);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.setStatus('Connection error', 'error');
        };

        this.ws.onclose = () => {
            this.setStatus('Disconnected', 'error');
            document.getElementById('disconnectBtn').disabled = true;
            this.ws = null;
        };
    }

    async disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        if (this.sessionId) {
            try {
                await fetch(`${this.apiBase}/sessions/${this.sessionId}`, {
                    method: 'DELETE'
                });
            } catch (error) {
                console.error('Error deleting session:', error);
            }
            this.sessionId = null;
        }

        // Clear URL parameter
        const url = new URL(window.location);
        url.searchParams.delete('session');
        window.history.pushState({}, '', url);

        document.getElementById('disconnectBtn').disabled = true;
        this.setStatus('Terminal session closed', '');
    }

    async reconnect() {
        if (this.sessionId) {
            this.setStatus('Reconnecting...', 'connecting');
            this.connectWebSocket();
        }
    }

    async resizeSession(rows, cols) {
        if (!this.sessionId) return;

        try {
            await fetch(`${this.apiBase}/sessions/${this.sessionId}/resize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rows, cols })
            });
        } catch (error) {
            console.error('Resize error:', error);
        }
    }

    async connectToExistingSession(sessionId) {
        this.sessionId = sessionId;
        this.term.clear();
        this.setStatus('Connecting to existing session...', 'connecting');

        // Fetch session info to display the command and check dimensions
        try {
            const response = await fetch(`${this.apiBase}/sessions/${sessionId}`);
            if (response.ok) {
                const info = await response.json();
                const filenameEl = document.getElementById('filename');
                if (filenameEl && info.command) {
                    filenameEl.textContent = info.command.join(' ');
                }

                // Check if dimensions already match (avoid unnecessary resize)
                if (info.rows === this.term.rows && info.cols === this.term.cols) {
                    this.isNewSession = true;  // Skip resize on connect
                }
            }
        } catch (error) {
            console.error('Failed to fetch session info:', error);
        }

        this.connectWebSocket();
    }

    sendSpecialKey(key) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        const keys = {
            'esc': '\x1b',
            'tab': '\t',
            'enter': '\r',
            'ctrl-c': '\x03',
            'ctrl-d': '\x04',
            'up': '\x1b[A',
            'down': '\x1b[B',
            'left': '\x1b[D',
            'right': '\x1b[C',
        };

        const keyCode = keys[key];
        if (keyCode) {
            this.ws.send(new TextEncoder().encode(keyCode));
        }
    }

    // Touch handling for mobile scrolling
    handleTouchStart(e) {
        // CRITICAL: Stop propagation to prevent xterm.js's Gesture system from interfering
        e.preventDefault();
        e.stopPropagation();

        console.log('[TouchDebug] touchstart fired');

        // Get viewport element for direct scrolling
        this.viewportElement = document.querySelector('.xterm-viewport');

        this.touchStartY = e.touches[0].clientY;
        this.lastTouchY = e.touches[0].clientY;
        this.isScrolling = false;
        this.scrollVelocity = 0;

        // Store initial scroll position
        if (this.viewportElement) {
            this.initialScrollTop = this.viewportElement.scrollTop;
            console.log('[TouchDebug] Initial scrollTop:', this.initialScrollTop);
        }
    }

    handleTouchMove(e) {
        if (!this.touchStartY || !this.viewportElement) return;

        // CRITICAL: Stop both default behavior AND propagation to block xterm.js's Gesture system
        // (combined with touch-action: none in CSS and capture: true for maximum compatibility)
        e.preventDefault();
        e.stopPropagation();

        const touchY = e.touches[0].clientY;
        const totalDiff = this.touchStartY - touchY;  // Positive = scroll down, negative = scroll up

        console.log('[TouchDebug] touchmove - totalDiff:', totalDiff);

        // Directly set viewport scrollTop for smooth continuous scrolling
        // No threshold, no accumulator - just direct 1:1 mapping
        this.viewportElement.scrollTop = this.initialScrollTop + totalDiff;

        console.log('[TouchDebug] Set scrollTop to:', this.viewportElement.scrollTop);

        // Track velocity for momentum scrolling
        const frameDiff = touchY - this.lastTouchY;
        this.scrollVelocity = -frameDiff;  // Negative because scrolling down moves finger up
        this.lastTouchY = touchY;
    }

    handleTouchEnd(e) {
        // CRITICAL: Stop propagation to prevent xterm.js's Gesture system from interfering
        e.preventDefault();
        e.stopPropagation();

        console.log('[TouchDebug] touchend fired, velocity:', this.scrollVelocity);

        // Apply momentum scrolling if velocity is high enough
        if (this.viewportElement && Math.abs(this.scrollVelocity) > 2) {
            let momentum = this.scrollVelocity;
            const decay = 0.92;

            const momentumScroll = () => {
                if (Math.abs(momentum) > 0.5) {
                    this.viewportElement.scrollTop += momentum;
                    momentum *= decay;
                    requestAnimationFrame(momentumScroll);
                }
            };

            requestAnimationFrame(momentumScroll);
        }

        this.touchStartY = 0;
        this.lastTouchY = 0;
        this.isScrolling = false;
        this.scrollVelocity = 0;
    }

    setStatus(message, type) {
        const statusEl = document.getElementById('status');
        statusEl.textContent = message;
        statusEl.className = 'status';
        if (type) {
            statusEl.classList.add(type);
        }
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new TerminalApp();
    });
} else {
    window.app = new TerminalApp();
}
