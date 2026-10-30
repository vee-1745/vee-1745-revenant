# Revenant zsh hook. Add to ~/.zshrc:  eval "$(python3 /path/to/revenant/ghost.py hook zsh)"
export REVENANT_ROOT="__REVENANT_ROOT__"
ghost() { python3 "$REVENANT_ROOT/ghost.py" "$@"; }

autoload -Uz add-zsh-hook
typeset -g __revenant_last_hist=$HISTCMD

__revenant_precmd() {
  local ec=$?
  [[ "$HISTCMD" == "$__revenant_last_hist" ]] && return $ec
  __revenant_last_hist=$HISTCMD
  local cmd="$(fc -ln -1 2>/dev/null)"
  cmd="${cmd## }"
  [[ -z "$cmd" || "$cmd" == ghost* ]] && return $ec
  python3 "$REVENANT_ROOT/ghost.py" whisper --exit "$ec" -- "$cmd" 2>/dev/null
  return $ec
}
add-zsh-hook precmd __revenant_precmd

# preload the spirit's model in the background so the first whisper isn't a cold start
( python3 "$REVENANT_ROOT/ghost.py" warm >/dev/null 2>&1 & )
