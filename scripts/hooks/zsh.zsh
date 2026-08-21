# Source this file from ~/.zshrc.
if [[ -n "${__DRP_ZSH_HOOK_LOADED:-}" ]]; then
    return 0
fi
__DRP_ZSH_HOOK_LOADED=1

__drp_cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/discord-rich-presence"
__drp_command_dir="$__drp_cache_dir/commands"
mkdir -p "$__drp_command_dir"
command chmod 700 "$__drp_cache_dir" "$__drp_command_dir" 2>/dev/null || true

__drp_preexec() {
    local cmd="$1"
    local pid_file="$__drp_command_dir/$$.txt"
    local legacy_file="$__drp_cache_dir/rp_last_cmd"
    [[ -n "$cmd" ]] || return
    case "$cmd" in
        *rp_last_cmd*|*__drp_*|*__DRP_*) return ;;
    esac
    (
        umask 077
        printf '%s\n' "$cmd" > "$pid_file"
        # Compatibility with older service versions.
        printf '%s\n' "$cmd" > "$legacy_file"
    )
    command chmod 600 "$pid_file" "$legacy_file" 2>/dev/null || true
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec __drp_preexec
