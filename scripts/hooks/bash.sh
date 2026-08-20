# Source this file from ~/.bashrc to publish the most recent interactive command locally.
# No network access is performed; the Rich Presence service reads these cache files.

if [ -n "${__DRP_BASH_HOOK_LOADED:-}" ]; then
    return 0 2>/dev/null || exit 0
fi
__DRP_BASH_HOOK_LOADED=1

__drp_cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/discord-rich-presence"
__drp_command_dir="$__drp_cache_dir/commands"
mkdir -p "$__drp_command_dir"

__drp_record_command() {
    local cmd="$1"
    [ -n "$cmd" ] || return
    case "$cmd" in
        *rp_last_cmd*|*__drp_*|*__DRP_*) return ;;
    esac

    printf '%s\n' "$cmd" > "$__drp_command_dir/$$.txt"
    # Compatibility with older service versions.
    printf '%s\n' "$cmd" > "$__drp_cache_dir/rp_last_cmd"
}

__drp_prompt_command() {
    local cmd
    # HISTTIMEFORMAT is cleared only for this expansion so parsing remains stable.
    cmd="$(HISTTIMEFORMAT= builtin history 1 2>/dev/null)"
    cmd="${cmd#*[0-9] }"
    cmd="${cmd# }"
    __drp_record_command "$cmd"
}

# Do not replace DEBUG traps owned by debuggers, direnv-like tools, or user
# profiles. PROMPT_COMMAND runs after each completed interactive command and can
# be composed safely with existing prompt hooks.
if declare -p PROMPT_COMMAND 2>/dev/null | grep -q '^declare -a'; then
    PROMPT_COMMAND+=(__drp_prompt_command)
elif [ -n "${PROMPT_COMMAND:-}" ]; then
    PROMPT_COMMAND="${PROMPT_COMMAND};__drp_prompt_command"
else
    PROMPT_COMMAND="__drp_prompt_command"
fi
