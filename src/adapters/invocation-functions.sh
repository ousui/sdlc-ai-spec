get_invoke_separator() {
    printf '%s\n' '-'
}

format_sdlc_command() {
    local name="$1" prefix
    case "${SDLC_HOST:-}" in
        codex) prefix='$' ;;
        claude) prefix='/@PLUGIN_ID@:' ;;
        cursor|'') prefix='/' ;;
        *) echo 'ERROR: Unsupported SDLC_HOST' >&2; return 1 ;;
    esac
    case "$name" in
        @SKILL_CASES@) ;;
        *) echo 'ERROR: Unsupported SDLC AI SPEC capability' >&2; return 1 ;;
    esac
    printf '%s%s\n' "$prefix" "$name"
}
