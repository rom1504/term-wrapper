#!/bin/bash
# Demo script for terminal wrapper

set -e

echo "========================================="
echo "  Terminal Wrapper Demo"
echo "========================================="
echo

# Start the server in the background
echo "Starting server..."
uv run python main.py &
SERVER_PID=$!
sleep 2

echo "Server started (PID: $SERVER_PID)"
echo

# Create a session with simple echo command
echo "1. Creating a terminal session with echo command..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"command": ["sh", "-c", "echo Hello from terminal wrapper; sleep 1; echo This is line 2; sleep 1; echo Done"], "rows": 24, "cols": 80}')

SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
echo "Session created: $SESSION_ID"
echo

# Wait for command to execute
sleep 3

# Get output
echo "2. Getting terminal output..."
curl -s http://localhost:8000/sessions/$SESSION_ID/output | jq -r '.output'
echo

# List sessions
echo "3. Listing all sessions..."
curl -s http://localhost:8000/sessions | jq '.'
echo

# Get session info
echo "4. Getting session info..."
curl -s http://localhost:8000/sessions/$SESSION_ID | jq '.'
echo

# Delete session
echo "5. Deleting session..."
curl -s -X DELETE http://localhost:8000/sessions/$SESSION_ID | jq '.'
echo

# Cleanup
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo
echo "========================================="
echo "  Demo Complete!"
echo "========================================="
echo
echo "To run the CLI client with the Python TUI app:"
echo "  1. Start server: uv run python main.py"
echo "  2. In another terminal: uv run python -m term_wrapper.cli python3 test_app/simple_tui.py"
echo
echo "To run tests:"
echo "  uv run pytest tests/ -v"
