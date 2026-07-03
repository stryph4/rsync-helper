#!/usr/bin/env bash

# Find the folder containing this script.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# The Python project root is one directory above.
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Run from the project root so Python can locate the package.
cd "$PROJECT_DIR" || exit 1

# Launch the GTK app while removing variables that may cause
# Snap libraries or incompatible GTK modules to be loaded.
exec env \
    -u GTK_MODULES \
    -u GTK_PATH \
    -u GIO_EXTRA_MODULES \
    -u GI_TYPELIB_PATH \
    -u LD_LIBRARY_PATH \
    -u LD_PRELOAD \
    -u SNAP \
    -u SNAP_NAME \
    -u SNAP_REVISION \
    -u SNAP_ARCH \
    -u SNAP_LIBRARY_PATH \
    RSYNC_HELPER_USE_GTK=1 \
    "$PROJECT_DIR/.venv/bin/python" \
    -m rsync_helper.rsync_helper -- "$@"