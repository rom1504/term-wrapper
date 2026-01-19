# TUI Skill

Run interactive TUI (Text User Interface) applications like htop, vim, or any terminal program through the term-wrapper API.

## Usage

```
/tui <command> [args...]
```

## Examples

- `/tui htop` - Launch htop system monitor
- `/tui vim myfile.txt` - Open vim editor
- `/tui python` - Start Python REPL
- `/tui bash` - Start interactive bash shell

## How it works

1. Starts the term-wrapper server if not already running
2. Creates a new terminal session with the requested command
3. Provides interactive controls to send input and view output
4. Allows you to interact with the TUI application through Claude

## Instructions for Claude

When the user invokes this skill:

1. Check if term-wrapper server is running on port 8000:
   ```bash
   curl -s http://localhost:8000/health || echo "not running"
   ```

2. If not running, start the server in background:
   ```bash
   uv run python main.py &
   sleep 2
   ```

3. Create a terminal session with the requested command:
   ```bash
   curl -X POST http://localhost:8000/sessions \
     -H "Content-Type: application/json" \
     -d '{
       "command": ["<command>", "<args>"],
       "rows": 24,
       "cols": 80,
       "env": {
         "TERM": "xterm-256color",
         "COLORTERM": "truecolor"
       }
     }'
   ```

4. Extract the session_id from the response

5. Get initial output:
   ```bash
   curl http://localhost:8000/sessions/{session_id}/output
   ```

6. Display the output to the user and explain:
   - What the TUI application is showing
   - Available commands/keys
   - How to interact with it

7. Offer to send input on behalf of the user:
   ```bash
   curl -X POST http://localhost:8000/sessions/{session_id}/input \
     -H "Content-Type: application/json" \
     -d '{"data": "<user_input>"}'
   ```

8. When done, clean up:
   ```bash
   curl -X DELETE http://localhost:8000/sessions/{session_id}
   ```

## Example: htop

When user runs `/tui htop`:

1. Create htop session
2. Show them the system monitoring interface
3. Explain htop controls:
   - Arrow keys to navigate
   - F10/q to quit
   - F6 to sort
   - etc.
4. Offer to navigate (send arrow keys), change sort order, or explore processes
5. Periodically refresh output to show live updates

## Example: vim

When user runs `/tui vim test.txt`:

1. Create vim session
2. Show the vim interface
3. Explain vim modes (Normal, Insert, Command)
4. Help them edit the file:
   - Press 'i' to enter insert mode
   - Type content
   - Press ESC to exit insert mode
   - Type ':wq' to save and quit
5. Send the appropriate key sequences as they request edits

## Tips

- For real-time apps like htop, periodically fetch output to show updates
- Parse ANSI escape sequences to explain what's on screen
- Be helpful in translating user intent to keyboard commands
- Always clean up sessions when done
- Suggest using the web frontend for complex interactions: `http://localhost:8000/static/index.html?cmd=htop`
