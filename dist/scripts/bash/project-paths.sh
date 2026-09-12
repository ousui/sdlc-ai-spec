#!/usr/bin/env bash
# Read-only package/project binding. This is deliberately not sdlc-000-init.
set -e
SCRIPT_DIR="$(CDPATH="" cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
feature=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --feature)
            [[ $# -ge 2 && -n "$2" ]] || { echo 'ERROR: --feature needs a value' >&2; exit 1; }
            feature=(--feature "$2"); shift 2 ;;
        --help|-h) echo 'Usage: project-paths.sh [--feature PATH]'; exit 0 ;;
        *) echo "ERROR: Unknown option: $1" >&2; exit 1 ;;
    esac
done
project=$(get_repo_root) || exit 1
python3 -I -B "$(_sdlc_plugin_root)/scripts/python/path_guard.py" \
    --plugin-root "$(_sdlc_plugin_root)" --project-root "$project" "${feature[@]}" --json
