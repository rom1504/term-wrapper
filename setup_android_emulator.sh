#!/bin/bash
# Setup Android SDK and Emulator for testing
# Based on: https://github.com/LabCIF-Tutorials/AndroidStudioEmulator-cmdConfig
# and: https://developer.android.com/studio/run/emulator-commandline

set -e

echo "=== Setting up Android SDK and Emulator ==="

# Configuration
ANDROID_HOME="${HOME}/Android/Sdk"
CMDLINE_TOOLS_VERSION="11076708"  # Latest as of 2025
CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip"
SYSTEM_IMAGE="system-images;android-33;google_apis;x86_64"  # Android 13
AVD_NAME="Pixel_5_API_33"

# Create directories
mkdir -p "${ANDROID_HOME}/cmdline-tools"
cd "${ANDROID_HOME}"

# Download command-line tools if not exists
if [ ! -d "${ANDROID_HOME}/cmdline-tools/latest" ]; then
    echo "Downloading Android command-line tools..."
    curl -o cmdline-tools.zip "${CMDLINE_TOOLS_URL}"
    unzip -q cmdline-tools.zip
    mv cmdline-tools latest
    mv latest cmdline-tools/
    rm cmdline-tools.zip
    echo "✓ Command-line tools installed"
else
    echo "✓ Command-line tools already installed"
fi

# Set up environment (MUST be done before using sdkmanager)
export ANDROID_HOME
export ANDROID_SDK_ROOT="${ANDROID_HOME}"
export PATH="${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/emulator:${PATH}"

# Verify sdkmanager is available
if ! command -v sdkmanager &> /dev/null; then
    echo "ERROR: sdkmanager not found in PATH"
    echo "PATH=${PATH}"
    exit 1
fi

# Accept licenses
echo "Accepting Android SDK licenses..."
yes | sdkmanager --licenses > /dev/null 2>&1 || true

# Install required packages
echo "Installing SDK packages (this may take 5-10 minutes)..."
sdkmanager --install \
    "platform-tools" \
    "emulator" \
    "platforms;android-33" \
    "${SYSTEM_IMAGE}" \
    "build-tools;33.0.2"

echo "✓ SDK packages installed"

# Create AVD if it doesn't exist
if ! avdmanager list avd | grep -q "${AVD_NAME}"; then
    echo "Creating Android Virtual Device: ${AVD_NAME}..."
    echo "no" | avdmanager create avd \
        -n "${AVD_NAME}" \
        -k "${SYSTEM_IMAGE}" \
        -d "pixel_5" \
        --force
    echo "✓ AVD created"
else
    echo "✓ AVD already exists"
fi

# Check if emulator dependencies are installed
echo ""
echo "Checking emulator dependencies..."
MISSING_LIBS=()

# Check for required libraries
for lib in libcairo.so.2 libpng16.so.16 libfontconfig.so.1 libfreetype.so.6; do
    if ! ldconfig -p | grep -q "$lib"; then
        MISSING_LIBS+=("$lib")
    fi
done

if [ ${#MISSING_LIBS[@]} -gt 0 ]; then
    echo "⚠️  Missing libraries detected: ${MISSING_LIBS[*]}"
    echo "Installing required libraries..."

    # Detect package manager and install
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y libcairo2 libpng16-16 fontconfig libfreetype6 \
            libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 libxcb1
    elif command -v yum &> /dev/null; then
        sudo yum install -y cairo libpng fontconfig freetype \
            mesa-libGL glib2 libX11 libXext libXrender libxcb
    else
        echo "⚠️  Please manually install: libcairo2 libpng fontconfig libfreetype"
    fi
fi

# Add environment variables to shell profile
SHELL_RC="${HOME}/.bashrc"
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="${HOME}/.zshrc"
fi

if ! grep -q "ANDROID_HOME" "${SHELL_RC}"; then
    echo "" >> "${SHELL_RC}"
    echo "# Android SDK" >> "${SHELL_RC}"
    echo "export ANDROID_HOME=\"${ANDROID_HOME}\"" >> "${SHELL_RC}"
    echo "export PATH=\"\${ANDROID_HOME}/cmdline-tools/latest/bin:\${ANDROID_HOME}/platform-tools:\${ANDROID_HOME}/emulator:\${PATH}\"" >> "${SHELL_RC}"
    echo "✓ Environment variables added to ${SHELL_RC}"
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Android SDK location: ${ANDROID_HOME}"
echo "AVD name: ${AVD_NAME}"
echo ""
echo "To start the emulator, run:"
echo "  export ANDROID_HOME=\"${ANDROID_HOME}\""
echo "  export PATH=\"\${ANDROID_HOME}/cmdline-tools/latest/bin:\${ANDROID_HOME}/platform-tools:\${ANDROID_HOME}/emulator:\${PATH}\""
echo "  emulator -avd ${AVD_NAME} -no-window -no-audio &"
echo ""
echo "To check if emulator is running:"
echo "  adb devices"
echo ""
echo "Then run the Playwright Android test:"
echo "  uv run --python 3.12 python tests/test_android_real.py"
