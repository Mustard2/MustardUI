#!/usr/bin/env bash
# Run the MustardUI test suite headless.
# Usage: tests/run_blender.sh /path/to/blender [-k test_name_pattern]
set -euo pipefail

BLENDER="${1:?Usage: $0 /path/to/blender [-k pattern]}"
shift
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Throwaway user resources, with the checkout linked as a user extension
RESOURCES="$(mktemp -d)"
trap 'rm -rf "$RESOURCES"' EXIT
mkdir -p "$RESOURCES/extensions/user_default"
ln -s "$REPO" "$RESOURCES/extensions/user_default/MustardUI"

BLENDER_USER_RESOURCES="$RESOURCES" "$BLENDER" \
  --background --factory-startup --python-exit-code 1 \
  --python "$REPO/tests/run.py" -- "$@"
