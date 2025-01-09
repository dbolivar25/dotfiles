# Editor Configuration
if set -q SSH_CONNECTION
    set -gx EDITOR vim
    set -gx VISUAL vim
else
    set -gx EDITOR nvim
    set -gx VISUAL nvim
end

# Config directory
set -gx XDG_CONFIG_HOME $HOME/.config

# Ruby exports
set -gx LDFLAGS -L/opt/homebrew/opt/ruby/lib
set -gx CPPFLAGS -I/opt/homebrew/opt/ruby/include

# Key and Token exports
test -f ~/.config/fish/secrets.fish; and source ~/.config/fish/secrets.fish

# FZF Configuration
set -gx FZF_DEFAULT_OPTS "
        --tmux 70%
        --color=fg:#908caa,bg:#191724,hl:#ebbcba
        --color=fg+:#e0def4,bg+:#26233a,hl+:#ebbcba
        --color=border:#403d52,header:#31748f,gutter:#191724
        --color=spinner:#f6c177,info:#9ccfd8
        --color=pointer:#c4a7e7,marker:#eb6f92,prompt:#908caa"

# Bat Configuration
set -gx BAT_THEME base16

# Other Configuration
set -gx USER danielbolivar
set -gx VIRTUAL_ENV_DISABLE_PROMPT 1
set -gx NODE_OPTIONS --max-old-space-size=8192
