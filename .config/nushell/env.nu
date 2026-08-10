# Keep inherited PATH compatible before the compiled image adds managed entries.
$env.ENV_CONVERSIONS = {
    "PATH": {
        from_string: { |value| $value | split row (char esep) | path expand --no-symlink }
        to_string: { |value| $value | path expand --no-symlink | str join (char esep) }
    }
}

source ~/.local/state/dotfiles/shell/v2/current/public/nu/env.nu
