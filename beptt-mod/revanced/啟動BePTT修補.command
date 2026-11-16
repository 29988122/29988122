#!/bin/zsh
set -e
SCRIPT_DIR="${0:A:h}"
exec python3 "$SCRIPT_DIR/launcher.py"
