# Shared environment and tool hooks for Bash.
_dotfiles_load_bash() {
  local dotfiles_shell_root="$HOME/.config/shell"
  local value_file key value entry existing editor_profile editor integration
  local seen joined
  local -a managed_paths inherited_paths combined_paths unique_paths

  for value_file in \
    "$dotfiles_shell_root"/environment.d/* \
    "$dotfiles_shell_root"/secrets.d/*; do
    [ -f "$value_file" ] || continue
    key=${value_file##*/}
    value=$(<"$value_file")
    value=${value//\$\{HOME\}/$HOME}
    export "$key=$value"
  done

  while IFS= read -r entry || [ -n "$entry" ]; do
    [[ "$entry" =~ ^[[:space:]]*(#|$) ]] && continue
    entry=${entry//\$\{HOME\}/$HOME}
    [ -d "$entry" ] && managed_paths+=("$entry")
  done < "$dotfiles_shell_root/paths"

  IFS=: read -r -a inherited_paths <<< "${PATH-}"
  combined_paths=("${managed_paths[@]}" "${inherited_paths[@]}")
  for entry in "${combined_paths[@]}"; do
    [ -n "$entry" ] || continue
    seen=false
    for existing in "${unique_paths[@]}"; do
      if [ "$existing" = "$entry" ]; then
        seen=true
        break
      fi
    done
    $seen || unique_paths+=("$entry")
  done

  joined=""
  for entry in "${unique_paths[@]}"; do
    joined="${joined:+$joined:}$entry"
  done
  export PATH="$joined"

  editor_profile=local
  [ -n "${SSH_CONNECTION:-}" ] && editor_profile=ssh
  editor=$(<"$dotfiles_shell_root/behavior/editor/$editor_profile")
  export EDITOR="$editor"
  export VISUAL="$editor"

  for integration in "$dotfiles_shell_root"/integrations/*/bash.bash; do
    [ -f "$integration" ] || continue
    case "$integration" in
      */mise/bash.bash) continue ;;
    esac
    . "$integration"
  done

  # Runtime selection must run after compatibility integrations.
  integration="$dotfiles_shell_root/integrations/mise/bash.bash"
  [ -f "$integration" ] && . "$integration"
}

_dotfiles_load_bash
unset -f _dotfiles_load_bash
