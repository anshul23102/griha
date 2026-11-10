#!/usr/bin/env bash
cd "$(dirname "$0")"
for f in .data/pids/*; do [ -f "$f" ] || continue; pid=$(cat "$f"); kill "$pid" 2>/dev/null && echo "stopped $(basename "$f")"; rm -f "$f"; done
pkill -f "uvicorn griha.api" 2>/dev/null; pkill -f "temporal server start-dev" 2>/dev/null; true
