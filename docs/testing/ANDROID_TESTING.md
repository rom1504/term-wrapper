# Android Emulator Testing Guide

This guide explains how to test mobile touch scrolling on a **real Android emulator** using Playwright and ADB.

## Why Real Android Emulator?

Browser device emulation (Playwright mobile profiles) simulates mobile viewport and touch events, but may not catch all Android-specific issues. A real Android emulator runs actual Android Chrome and provides higher fidelity testing.

## Prerequisites

- Linux system (Debian/Ubuntu recommended)
- ~5GB free disk space for Android SDK and system image
- Hardware virtualization enabled (KVM)

## Setup (One-Time)

### Step 1: Install Android SDK and Emulator

Run the setup script:

```bash
./setup_android_emulator.sh
```

This will:
- Download Android SDK command-line tools (~200MB)
- Install Android 13 (API 33) system image (~1.5GB)
- Create a Pixel 5 AVD (Android Virtual Device)
- Install required system libraries
- Set up environment variables

**Time required:** 5-10 minutes (depending on download speed)

### Step 2: Reload Shell

After setup completes, reload your shell to pick up environment variables:

```bash
source ~/.bashrc  # or ~/.zshrc if using zsh
```

Or open a new terminal window.

### Step 3: Verify Installation

Check that Android tools are available:

```bash
which adb
which emulator
adb --version
```

You should see paths like `/home/USER/Android/Sdk/...`

## Running Tests

### Step 1: Start the Android Emulator

Start the emulator in headless mode (no GUI window):

```bash
emulator -avd Pixel_5_API_33 -no-window -no-audio &
```

**Note:** First boot takes 1-2 minutes. Subsequent boots are faster.

Wait for the emulator to finish booting:

```bash
adb wait-for-device
adb shell getprop sys.boot_completed  # Should output "1" when ready
```

### Step 2: Check Emulator Status

Verify the emulator is connected:

```bash
adb devices
```

You should see output like:
```
List of devices attached
emulator-5554   device
```

### Step 3: Run the Touch Scrolling Test

```bash
uv run --python 3.12 python tests/test_android_real.py
```

The test will:
1. Connect to the Android emulator via ADB
2. Launch Chrome on the Android device
3. Navigate to the terminal web UI
4. Perform touch swipe gestures
5. Verify that scrolling worked
6. Save a screenshot to `/tmp/android_test.png`

### Expected Output

If touch scrolling works:
```
✅ SUCCESS: Touch scrolling worked! Viewport changed from 80 to 70
```

If it fails:
```
❌ FAILED: Touch scrolling did NOT work. Viewport stayed at 80
```

## Troubleshooting

### "No Android devices found via ADB"

- Make sure the emulator is running: `adb devices`
- Restart ADB: `adb kill-server && adb start-server`
- Check emulator status: `adb shell getprop sys.boot_completed`

### "Chrome not found" or Browser Launch Fails

Install Chrome on the emulator:
```bash
adb install /path/to/chrome.apk
```

Or use the emulator with Google Play to install Chrome.

### Emulator Won't Start

Check for missing libraries:
```bash
ldd ~/Android/Sdk/emulator/lib64/libQt5Core.so.5 | grep "not found"
```

Install missing libraries (Ubuntu/Debian):
```bash
sudo apt-get install libcairo2 libpng16-16 fontconfig libfreetype6 libgl1
```

### Emulator is Slow

The emulator requires hardware acceleration (KVM). Check if it's enabled:
```bash
ls -la /dev/kvm  # Should exist and be accessible
```

If not available, you may need to:
1. Enable virtualization in BIOS
2. Install KVM: `sudo apt-get install qemu-kvm`
3. Add user to kvm group: `sudo usermod -aG kvm $USER`
4. Reboot

## Stopping the Emulator

```bash
adb emu kill
```

Or find the process and kill it:
```bash
pkill -f "emulator.*Pixel_5_API_33"
```

## References

Based on official Android documentation and community guides:
- [Android Emulator Command Line](https://developer.android.com/studio/run/emulator-commandline)
- [Playwright Android API](https://playwright.dev/docs/api/class-android)
- [Setup Guide](https://github.com/LabCIF-Tutorials/AndroidStudioEmulator-cmdConfig)
- [Minimal Android Emulator on Linux](https://blogs.igalia.com/jaragunde/2023/12/setting-up-a-minimal-command-line-android-emulator-on-linux/)

## Architecture

```
┌─────────────────────────────────────────┐
│  Playwright Test (Python)               │
│  tests/test_android_real.py             │
└───────────────┬─────────────────────────┘
                │
                │ Playwright Android API
                ▼
┌─────────────────────────────────────────┐
│  ADB (Android Debug Bridge)             │
└───────────────┬─────────────────────────┘
                │
                │ TCP Connection (port 5555)
                ▼
┌─────────────────────────────────────────┐
│  Android Emulator (AVD)                 │
│  - Android 13 (API 33)                  │
│  - Pixel 5 device profile               │
│  - Chrome browser                       │
└───────────────┬─────────────────────────┘
                │
                │ Chrome DevTools Protocol
                ▼
┌─────────────────────────────────────────┐
│  Terminal Web UI                        │
│  - xterm.js                             │
│  - Touch event handlers                 │
│  - WebSocket connection to backend      │
└─────────────────────────────────────────┘
```

## Next Steps

If tests pass on the emulator but fail on your real device (Xiaomi 13):
1. Connect your real device via USB
2. Enable USB debugging on your phone
3. Authorize the ADB connection
4. Run the same test - it will automatically detect the real device

The benefit of the emulator is that it's reproducible and can run in CI/CD pipelines.
