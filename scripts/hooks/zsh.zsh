# Source this file from ~/.zshrc.
__drp_cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/discord-rich-presence"
mkdir -p "$__drp_cache_dir"

__drp_preexec() {
    local cmd="$1"
    case "$cmd" in
        *rp_last_cmd*|*__drp_*) return ;;
    esac
    printf '%s\n' "$cmd" > "$__drp_cache_dir/rp_last_cmd"
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec __drp_preexec
