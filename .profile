# Source cargo environment
[[ -f "/users/danielbolivar/.cargo/env" ]] && source "/users/danielbolivar/.cargo/env"

# Source Haskell environment
[[ -f "/users/danielbolivar/.ghcup/env" ]] && source "/users/danielbolivar/.ghcup/env"

export NVM_DIR="$HOME/.config/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm

export PATH="/Users/danielbolivar/.local/share/solana/install/active_release/bin:$PATH"
