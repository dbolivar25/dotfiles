# PATH exports
typeset -U path PATH
path=(
    $HOME/.npm-global/bin
    $HOME/.local/bin
    /opt/homebrew/bin
    /usr/local/bin
    /usr/local/sbin
    $HOME/.cargo/bin
    /Users/danielbolivar/.local/share/solana/install/active_release/bin
    /Users/danielbolivar/.avm/bin
    /usr/local/go/bin
    /Applications/Postgres.app/Contents/Versions/latest/bin
    $HOME/.ghcup/bin
    $HOME/.cabal/bin
    $HOME/.modular/bin
    /Library/TeX/texbin
    /opt/homebrew/opt/ruby/bin
    $HOME/.dotnet/tools
    /usr/local/share/dotnet
    $path
)
export PATH

# Development tools exports
export DOTNET_ROOT="/usr/local/share/dotnet"
export XDG_CONFIG_HOME="$HOME/.config"

# Ruby exports
export LDFLAGS="-L/opt/homebrew/opt/ruby/lib"
export CPPFLAGS="-I/opt/homebrew/opt/ruby/include"

# Source cargo environment
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# Source Haskell environment
[[ -f "$HOME/.ghcup/env" ]] && source "$HOME/.ghcup/env"

# pnpm
export PNPM_HOME="/Users/danielbolivar/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end

export NVM_DIR="$HOME/.config/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
