// Terminal Wrapper Frontend Application

class TerminalApp {
    constructor() {
        this.term = null;
        this.fitAddon = null;
        this.webLinksAddon = null;
        this.ws = null;
        this.sessionId = null;
        this.apiBase = window.location.origin;

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

        // Auto-connect if URL has session parameter
        const params = new URLSearchParams(window.location.search);
        const sessionId = params.get('session');
        if (sessionId) {
            this.connectToExistingSession(sessionId);
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
            scrollback: 10000,
            tabStopWidth: 8,
        });

        // Load addons
        this.fitAddon = new FitAddon.FitAddon();
        this.term.loadAddon(this.fitAddon);

        this.webLinksAddon = new WebLinksAddon.WebLinksAddon();
        this.term.loadAddon(this.webLinksAddon);

        // Open terminal
        this.term.open(document.getElementById('terminal'));
        this.fitAddon.fit();

        // Welcome message
        this.term.writeln('\x1b[1;32m╔═══════════════════════════════════════╗\x1b[0m');
        this.term.writeln('\x1b[1;32m║     Terminal Wrapper Web Frontend    ║\x1b[0m');
        this.term.writeln('\x1b[1;32m╚═══════════════════════════════════════╝\x1b[0m');
        this.term.writeln('');
        this.term.writeln('Enter a command above and click Connect to start.');
        this.term.writeln('');

        // Handle input from terminal
        this.term.onData(data => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(new TextEncoder().encode(data));
            }
        });

        // Handle terminal resize
        this.term.onResize(({ rows, cols }) => {
            if (this.sessionId) {
                this.resizeSession(rows, cols);
            }
        });

        // Handle touch events for mobile scrolling
        const viewport = document.querySelector('.xterm-viewport');
        if (viewport) {
            viewport.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
            viewport.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
            viewport.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
        }
    }

    setupEventListeners() {
        // Connect button
        document.getElementById('connectBtn').addEventListener('click', () => {
            this.connect();
        });

        // Disconnect button
        document.getElementById('disconnectBtn').addEventListener('click', () => {
            this.disconnect();
        });

        // Enter key in inputs
        document.getElementById('commandInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.connect();
        });
        document.getElementById('argsInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.connect();
        });

        // Window resize
        window.addEventListener('resize', () => {
            if (this.fitAddon) {
                this.fitAddon.fit();
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

    async connect() {
        const command = document.getElementById('commandInput').value.trim();
        if (!command) {
            this.setStatus('Please enter a command', 'error');
            return;
        }

        const args = document.getElementById('argsInput').value.trim();
        const commandArray = args ? [command, ...args.split(' ')] : [command];

        this.setStatus('Creating session...', 'connecting');

        try {
            // Create session
            const response = await fetch(`${this.apiBase}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: commandArray,
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
            document.getElementById('connectBtn').disabled = true;
            document.getElementById('disconnectBtn').disabled = false;
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
            document.getElementById('connectBtn').disabled = false;
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

        document.getElementById('connectBtn').disabled = false;
        document.getElementById('disconnectBtn').disabled = true;
        this.setStatus('Not connected', '');
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
        this.connectWebSocket();
    }

    sendSpecialKey(key) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        const keys = {
            'esc': '\x1b',
            'tab': '\t',
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
        this.touchStartY = e.touches[0].clientY;
        this.isScrolling = false;
    }

    handleTouchMove(e) {
        if (!this.touchStartY) return;

        const touchY = e.touches[0].clientY;
        const diff = this.touchStartY - touchY;

        // Detect if user is scrolling (not typing)
        if (Math.abs(diff) > 10) {
            this.isScrolling = true;
            // Let default scroll behavior work
        }
    }

    handleTouchEnd(e) {
        this.touchStartY = 0;
        this.isScrolling = false;
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
