# PATH exports
typeset -U path PATH
path=(
    $HOME/.local/bin
    /opt/homebrew/bin
    /usr/local/share/dotnet
    $HOME/.dotnet/tools
    /opt/homebrew/opt/ruby/bin
    /Library/TeX/texbin
    /usr/local/sbin
    $HOME/.modular/bin
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
