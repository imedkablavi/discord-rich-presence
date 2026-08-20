# Source this file from ~/.bashrc to publish the current command locally.
# No network access is performed; the Rich Presence service reads the cache file.

__drp_cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/discord-rich-presence"
mkdir -p "$__drp_cache_dir"

__drp_record_command() {
    local cmd="$1"
    case "$cmd" in
        *rp_last_cmd*|*__drp_*) return ;;
    esac
    printf '%s\n' "$cmd" > "$__drp_cache_dir/rp_last_cmd"
}

__drp_preexec_from_history() {
    local cmd
    cmd="$(history 1 | sed -E 's/^ *[0-9]+ +//')"
    [ -n "$cmd" ] && __drp_record_command "$cmd"
}

# Record the command that just entered history. This is intentionally conservative
# and avoids a DEBUG trap that would also capture internal shell implementation commands.
PROMPT_COMMAND="__drp_preexec_from_history${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
