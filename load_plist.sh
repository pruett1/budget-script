#!/bin/bash
if [ -z "$1" ]; then
  echo "Error: $0 requires <plist_name>"
  exit 1
fi

PLIST_NAME="$(echo "$1" | xargs)"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SRC="$DIR/job/$PLIST_NAME"

if [ ! -f "$SRC" ]; then
    echo "Error: $SRC does not exist"
    exit 1
fi

if [ ! -f "$DIR/job/run_script.sh" ]; then
    echo "Error: job requires run_script.sh to exist"
    exit 1
fi

DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

ln -sf "$SRC" "$DEST"
launchctl bootout gui/$(id -u) "$DEST" 2>/dev/null

if ! launchctl bootstrap gui/$(id -u) "$DEST"; then
    echo "Failed to load $PLIST_NAME"
    exit 1
fi

echo "$PLIST_NAME installed and loaded"