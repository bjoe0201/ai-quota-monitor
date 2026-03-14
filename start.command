#!/bin/bash
# Double-clickable launcher for macOS (Finder)
cd "$(dirname "$0")"

# Find Python
PYTHON=""
for candidate in /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3 /usr/local/bin/python3 ~/.pyenv/shims/python3 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display alert "AI Quota Monitor" message "Python not found. Please install Python 3." as critical'
    exit 1
fi

# Prevent duplicate instances
if pgrep -f "python.*main\.py" &>/dev/null; then
    osascript -e 'display alert "AI Quota Monitor" message "程式已在執行中。" as warning'
    exit 0
fi

# Launch app in background so this Terminal window can close
# Subshell + nohup fully detaches Python from this Terminal session
( nohup "$PYTHON" main.py > /tmp/ai-quota-monitor.log 2>&1 & )

# Close the Terminal window that opened due to double-click
sleep 0.8
osascript -e 'tell application "Terminal"
    close (every window whose name contains "start.command")
end tell' &>/dev/null || true
