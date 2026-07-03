#!/usr/bin/env bash

# Find the project root.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

# Launch using the project venv while truly removing GTK_MODULES.
exec env \
    -u GTK_MODULES \
    -u LD_LIBRARY_PATH \
    -u LD_PRELOAD \
    RSYNC_HELPER_USE_GTK=1 \
    PYTHONFAULTHANDLER=1 \
    "$PROJECT_DIR/.venv/bin/python" \
    -m debugpy \
    --listen 5678 \
    --wait-for-client \
    -m rsync_helper.rsync_helper