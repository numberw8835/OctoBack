#!/usr/bin/env bash

set -e

# Target directories
INSTALL_DIR="$HOME/.octoback/src"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/octoback"

echo "Installing OctoBack..."

# 1. Ensure directories exist
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 2. Copy code files
echo "Copying source files to $INSTALL_DIR..."
# Clean copy: delete existing src folder first to prevent mixing old files
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r octoback.py modules "$INSTALL_DIR/"

# 3. Create launcher wrapper script
echo "Creating launcher script at $LAUNCHER..."
cat << 'EOF' > "$LAUNCHER"
#!/usr/bin/env bash
# Ensure PyYAML and other standard dependencies can locate modules
export PYTHONPATH="$HOME/.octoback/src:$PYTHONPATH"
exec python3 "$HOME/.octoback/src/octoback.py" "$@"
EOF

# 4. Make launcher executable
chmod +x "$LAUNCHER"

# 5. Check if PyYAML is installed
if ! python3 -c "import yaml" &>/dev/null; then
    echo "Warning: PyYAML python library is missing. Attempting install..."
    pip3 install PyYAML || pip install PyYAML || echo "Failed to automatically install PyYAML. Please run: pip install PyYAML"
fi

echo "OctoBack installed successfully!"
echo "You can now run 'octoback' directly from your terminal."

# 6. Verify PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "============================================================"
    echo "WARNING: $BIN_DIR is not in your PATH."
    echo "To run 'octoback' globally, add this line to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$PATH:\$HOME/.local/bin\""
    echo "============================================================"
fi
