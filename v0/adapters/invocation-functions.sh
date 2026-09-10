get_invoke_separator() {
    printf '%s\n' '-'
}

format_speckit_command() {
    local name="$1" prefix
    case "${SDLC_HOST:-}" in
        codex) prefix='$sdlc-' ;;
        claude) prefix='/sdlc:sdlc-' ;;
        cursor|'') prefix='/sdlc-' ;;
        *) echo 'ERROR: Unsupported SDLC_HOST' >&2; return 1 ;;
    esac
    name="${name#/}"
    name="${name#speckit.}"
    name="${name#speckit-}"
    name="${name//./-}"
    printf '%s%s\n' "$prefix" "$name"
}
