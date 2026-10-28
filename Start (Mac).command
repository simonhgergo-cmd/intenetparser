#!/bin/bash
# Double-click to start. Needs Python 3.11 or newer from https://www.python.org/downloads/
cd "$(dirname "$0")" || exit 1
for PY in python3.13 python3.12 python3.11 python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
  if command -v "$PY" >/dev/null 2>&1 && "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    exec "$PY" -m iparse app
  fi
done
echo
echo " Python 3.11 or newer is needed and wasn't found."
echo " 1. Download it from https://www.python.org/downloads/ and install it."
echo " 2. Double-click this file again."
echo
open https://www.python.org/downloads/ 2>/dev/null
read -r -p "Press Enter to close."
