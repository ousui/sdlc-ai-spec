# SDLC: resources resolve from this file, projects NEVER resolve from this file.
_sdlc_plugin_root() {
    local dir
    dir="$(CDPATH="" cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)" || return 1
    printf '%s\n' "$dir"
}

_sdlc_store() {
    command -v python3 >/dev/null 2>&1 || {
        echo 'ERROR: Python 3.9+ is required for SDLC path validation' >&2
        return 1
    }
    python3 -I -B "$(_sdlc_plugin_root)/scripts/python/sdlc_store.py" "$@"
}

_sdlc_state_dir() {
    _sdlc_store resolve --project "$1" --field SDLC_DIR
}

_sdlc_feature_json() {
    _sdlc_store resolve --project "$1" --field FEATURE_JSON
}

_sdlc_feature_path() {
    _sdlc_store feature --project "$1" --value "$2" --field FEATURE_DIR
}

_sdlc_validate_paths() {
    local root
    root=$(_sdlc_plugin_root) || return 1
    command -v python3 >/dev/null 2>&1 || {
        echo 'ERROR: Python 3.9+ is required for SDLC path validation' >&2
        return 1
    }
    if [[ $# -gt 1 ]]; then
        python3 -I -B "$root/scripts/python/path_guard.py" --plugin-root "$root" --project-root "$1" --feature "$2"
    else
        python3 -I -B "$root/scripts/python/path_guard.py" --plugin-root "$root" --project-root "$1"
    fi
}

get_repo_root() {
    _sdlc_store resolve --field PROJECT_ROOT
}
