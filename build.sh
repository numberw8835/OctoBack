#!/usr/bin/env bash

set -e

echo "Building standalone binary using PyInstaller..."

# 1. Compile with PyInstaller
pyinstaller --onefile --name octoback octoback.py

# 2. Copy binary to ~/.local/bin
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
echo "Installing binary to $BIN_DIR/octoback..."
cp dist/octoback "$BIN_DIR/octoback"

# 3. Clean up build artifacts to keep repository clean
echo "Cleaning up build artifacts..."
rm -rf build dist octoback.spec

echo "Build and installation complete!"
echo "You can now run 'octoback' directly from your terminal."
