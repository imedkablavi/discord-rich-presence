# Source this file from ~/.zshrc.
if [[ -n "${__DRP_ZSH_HOOK_LOADED:-}" ]]; then
    return 0
fi
__DRP_ZSH_HOOK_LOADED=1

__drp_cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/discord-rich-presence"
__drp_command_dir="$__drp_cache_dir/commands"
mkdir -p "$__drp_command_dir"

__drp_preexec() {
    local cmd="$1"
    [[ -n "$cmd" ]] || return
    case "$cmd" in
        *rp_last_cmd*|*__drp_*|*__DRP_*) return ;;
    esac
    printf '%s\n' "$cmd" > "$__drp_command_dir/$$.txt"
    # Compatibility with older service versions.
    printf '%s\n' "$cmd" > "$__drp_cache_dir/rp_last_cmd"
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec __drp_preexec
