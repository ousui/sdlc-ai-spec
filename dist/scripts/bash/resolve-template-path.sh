#!/usr/bin/env bash
# Local adapter for SPEC's file-path contract (REV-007).
# resolve-template.sh remains unchanged: it emits content for its other callers.
# The accepted profile has project replace overrides + bundled core templates;
# optional presets/extensions remain outside the product's supported profile.
set -e
SCRIPT_DIR="$(CDPATH="" cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
if [[ $# -ne 1 || -z "$1" ]]; then
    echo 'Usage: resolve-template-path.sh <template-name>' >&2
    exit 1
fi
case "$1" in *[!a-z0-9-]*) echo 'ERROR: Invalid template name' >&2; exit 1 ;; esac
project=$(get_repo_root) || exit 1
if ! template=$(resolve_template "$1" "$project"); then
    echo "ERROR: Required template path could not be resolved: $1" >&2
    exit 1
fi
# Emit only the selected existing file path: never write temporary template files,
# select a different template, persist a feature or treat its content as a path.
[[ -f "$template" ]] || { echo 'ERROR: Resolved template is not a file' >&2; exit 1; }
printf '%s\n' "$template"
