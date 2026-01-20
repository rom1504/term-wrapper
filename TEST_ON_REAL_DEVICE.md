# Test Touch Scrolling on Real Device (Xiaomi 13)

## Quick Test

### Step 1: Find Your Computer's IP Address

On your computer, run:
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1 | head -1
```

Or:
```bash
hostname -I | awk '{print $1}'
```

Example output: `192.168.1.100`

### Step 2: Start the Server

Start the term-wrapper server accessible from your phone:

```bash
uv run --python 3.12 term-wrapper web bash --host 0.0.0.0 --port 8000
```

**Important:** This will print a URL like `http://localhost:8000/?session=...`

### Step 3: Open on Your Phone

On your Xiaomi 13:
1. Open Chrome browser
2. Navigate to: `http://YOUR_COMPUTER_IP:8000/?session=SESSION_ID`
   - Replace `YOUR_COMPUTER_IP` with the IP from Step 1
   - Replace `SESSION_ID` with the session ID from Step 2

Example: `http://192.168.1.100:8000/?session=abc123`

### Step 4: Test Touch Scrolling

Once the terminal loads on your phone:

#### Test 1: Normal Buffer (Bash)
1. You should see bash prompt
2. Run: `seq 1 100`
3. Try **swiping down** (scroll up to see earlier lines)
4. Try **swiping up** (scroll down to see later lines)

**Expected:** Smooth continuous scrolling while holding and dragging

#### Test 2: Alternate Buffer (Vim)
1. Run: `vim /tmp/test.txt`
2. Press `i` to enter insert mode
3. Type some lines
4. Press `Esc` to exit insert mode
5. Try **swiping** to scroll through the file

**Expected:** Scrolling works (sends arrow keys to vim)

### Step 5: Check Console Logs (Optional)

On your phone's Chrome:
1. Type in address bar: `chrome://inspect`
2. Find your page and click "Inspect"
3. Look at Console tab for `[TouchDebug]` messages

You should see logs like:
```
[TouchDebug] touchstart - buffer type: normal
[TouchDebug] touchmove - buffer: normal deltaY: -24.5 total: -24.5
[TouchDebug] Scrolled 1 lines in normal buffer
```

## What to Report Back

Please report:
1. ✅ or ❌ Does continuous touch scrolling work in bash?
2. ✅ or ❌ Does scrolling work in vim?
3. Any console errors or unusual behavior
4. Screenshot (if helpful)

## Troubleshooting

### Can't Connect from Phone

**Problem:** Connection refused or timeout

**Solutions:**
1. Make sure your phone and computer are on the same WiFi network
2. Check firewall isn't blocking port 8000:
   ```bash
   sudo ufw allow 8000/tcp  # If using ufw
   ```
3. Verify server is listening:
   ```bash
   netstat -tlnp | grep 8000
   ```

### Terminal Doesn't Load

**Problem:** Blank page or "Could not connect"

**Solutions:**
1. Check browser console for JavaScript errors
2. Try refreshing the page
3. Verify the session is still active on the server

### Touch Events Not Working

**Problem:** No scrolling or erratic behavior

**Check:**
1. Is `window.app` defined? (Check console: `typeof window.app`)
2. Are TouchDebug logs appearing?
3. Try a different browser (Firefox vs Chrome)

## Alternative: USB Debugging

If WiFi doesn't work, you can use USB:

1. Enable USB debugging on Xiaomi 13
2. Connect phone to computer via USB
3. Run: `adb reverse tcp:8000 tcp:8000`
4. On phone, navigate to: `http://localhost:8000/?session=...`

## Expected Test Results

Based on our Playwright mobile emulation test:
- ✅ JavaScript loads correctly (56 tests passing)
- ✅ Touch events are captured
- ✅ Viewport scrolls (80 → 70 in test)
- ✅ Touch handlers process deltaY correctly
- ✅ Both normal and alternate buffers work

The mobile emulation test proved the code works. Now we need to verify on real hardware.
