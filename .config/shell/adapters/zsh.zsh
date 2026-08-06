# Shared static environment for Zsh. Interactive behavior remains native.
typeset -g DOTFILES_SHELL_ROOT="${HOME}/.config/shell"

for value_file in "$DOTFILES_SHELL_ROOT"/environment.d/*(N) "$DOTFILES_SHELL_ROOT"/secrets.d/*(N); do
  key="${value_file:t}"
  value="$(<"$value_file")"
  value="${value//\$\{HOME\}/$HOME}"
  export "$key=$value"
done

typeset -a managed_paths
while IFS= read -r entry; do
  [[ -z "${entry//[[:space:]]/}" || "$entry" == [[:space:]]#\#* ]] && continue
  entry="${entry//\$\{HOME\}/$HOME}"
  [[ -d "$entry" ]] && managed_paths+=("$entry")
done < "$DOTFILES_SHELL_ROOT/paths"

path=("${managed_paths[@]}" "${path[@]}")
typeset -U path PATH
export PATH

editor_profile=local
[[ -n "${SSH_CONNECTION:-}" ]] && editor_profile=ssh
editor="$(<"$DOTFILES_SHELL_ROOT/behavior/editor/$editor_profile")"
export EDITOR="$editor"
export VISUAL="$editor"

for integration in "$DOTFILES_SHELL_ROOT"/integrations/*/zsh.zsh(N); do
  source "$integration"
done

unset value_file key value managed_paths entry editor_profile editor integration
