export PATH="$PATH:/Users/danielbolivar/.local/bin"

alias claude='~/.local/bin/claude'
# mise activation
if command -v mise &> /dev/null; then
    eval "$(mise activate bash --shims)"
    eval "$(mise activate bash)"
elif [ -f ~/.local/bin/mise ]; then
    export PATH="$HOME/.local/bin:$PATH"
    eval "$(~/.local/bin/mise activate bash --shims)"
    eval "$(~/.local/bin/mise activate bash)"
fi
