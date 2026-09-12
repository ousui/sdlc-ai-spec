# SDLC: resources resolve from this file, projects NEVER resolve from this file.
_sdlc_plugin_root() {
    local dir
    dir="$(CDPATH="" cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)" || return 1
    printf '%s\n' "$dir"
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
    local root
    if [[ -n "${SPECIFY_INIT_DIR:-}" ]]; then
        root=$(resolve_specify_init_dir) || return 1
    elif ! root=$(find_specify_root); then
        echo 'ERROR: No initialized .sdlc project found; run sdlc-000-init in the selected project first' >&2
        return 1
    fi
    _sdlc_validate_paths "$root" || return 1
    printf '%s\n' "$root"
}
