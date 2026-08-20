# Source this file from ~/.bashrc to publish the current command locally.
# No network access is performed; the Rich Presence service reads these cache files.

# Avoid stacking duplicate DEBUG traps when the profile is re-sourced.
if [ -n "${__DRP_BASH_HOOK_LOADED:-}" ]; then
    return 0 2>/dev/null || exit 0
fi
__DRP_BASH_HOOK_LOADED=1

__drp_cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/discord-rich-presence"
__drp_command_dir="$__drp_cache_dir/commands"
mkdir -p "$__drp_command_dir"
__drp_in_hook=0

__drp_record_command() {
    local cmd="$1"
    [ -n "$cmd" ] || return
    case "$cmd" in
        *rp_last_cmd*|*__drp_*|*__DRP_*) return ;;
    esac

    __drp_in_hook=1
    printf '%s\n' "$cmd" > "$__drp_command_dir/$$.txt"
    # Compatibility with older service versions.
    printf '%s\n' "$cmd" > "$__drp_cache_dir/rp_last_cmd"
    __drp_in_hook=0
}

__drp_debug_trap() {
    [ "$__drp_in_hook" -eq 0 ] || return
    local cmd="$1"
    case "$cmd" in
        __drp_*|trap\ *|PROMPT_COMMAND=*|return\ *|exit\ *) return ;;
    esac
    __drp_record_command "$cmd"
}

# DEBUG fires immediately before the interactive command runs. The guard above
# prevents the hook's own file writes from recursively becoming "the command".
trap '__drp_debug_trap "$BASH_COMMAND"' DEBUG
