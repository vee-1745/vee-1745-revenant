# Revenant bash hook. Add to ~/.bashrc:  eval "$(python3 /path/to/revenant/ghost.py hook bash)"
export REVENANT_ROOT="__REVENANT_ROOT__"
ghost() { python3 "$REVENANT_ROOT/ghost.py" "$@"; }

__revenant_last_hist="$(HISTTIMEFORMAT= builtin history 1 | awk '{print $1}')"

__revenant_precmd() {
  local ec=$?
  local num cmd
  read -r num cmd <<< "$(HISTTIMEFORMAT= builtin history 1)"
  [[ "$num" == "$__revenant_last_hist" ]] && return $ec
  __revenant_last_hist="$num"
  case "$cmd" in ghost*|"") return $ec ;; esac
  python3 "$REVENANT_ROOT/ghost.py" whisper --exit "$ec" -- "$cmd" 2>/dev/null
  return $ec
}

case ";${PROMPT_COMMAND};" in
  *";__revenant_precmd;"*) ;;
  *) PROMPT_COMMAND="__revenant_precmd${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac

# preload the spirit's model in the background so the first whisper isn't a cold start
( python3 "$REVENANT_ROOT/ghost.py" warm >/dev/null 2>&1 & )
