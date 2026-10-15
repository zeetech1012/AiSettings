#!/bin/bash
cd "$(dirname "$0")"
if command -v node >/dev/null 2>&1; then
    node server.js
else
    echo "Error: Node.js is not installed."
    exit 1
fi
