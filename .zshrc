# Shared environment and commands compiled by `dotfiles shell apply`.
_dotfiles_shell_image="$HOME/.local/state/dotfiles/shell/v2/current/public/zsh/init.zsh"
if [[ -r "$_dotfiles_shell_image" ]]; then
  source "$_dotfiles_shell_image"
else
  print -u2 'dotfiles: shell image missing; run `dotfiles shell apply`'
fi
unset _dotfiles_shell_image

# Keep Fish as the interactive shell for SSH sessions while Zsh remains the
# POSIX-compatible login shell.
if [[ -o interactive && -n "$SSH_CONNECTION" && -x /opt/homebrew/bin/fish ]]; then
  exec /opt/homebrew/bin/fish -l
fi
