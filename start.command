#!/bin/bash
# Double-clickable launcher for macOS (Finder)
cd "$(dirname "$0")"

# Find Python
PYTHON=""
for candidate in python3 python ~/.pyenv/shims/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display alert "AI Quota Monitor" message "Python not found. Please install Python 3." as critical'
    exit 1
fi

# Launch app in background so this Terminal window can close
"$PYTHON" main.py &

# Close the Terminal window that opened due to double-click
sleep 0.8
osascript -e 'tell application "Terminal"
    close (every window whose name contains "start.command")
end tell' &>/dev/null || true
