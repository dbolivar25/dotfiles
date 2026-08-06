# Shared environment, behavior contracts, and registered integrations.
source "$HOME/.config/shell/adapters/zsh.zsh"

# Cargo may add toolchain-specific environment beyond the shared PATH.
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# Keep Fish as the interactive shell for SSH sessions while Zsh remains the
# POSIX-compatible login shell.
if [[ -o interactive && -n "$SSH_CONNECTION" && -x /opt/homebrew/bin/fish ]]; then
  exec /opt/homebrew/bin/fish -l
fi
