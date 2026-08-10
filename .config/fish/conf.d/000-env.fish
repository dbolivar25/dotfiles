set -l dotfiles_shell_image ~/.local/state/dotfiles/shell/v2/current/public/fish/init.fish
if test -r $dotfiles_shell_image
    source $dotfiles_shell_image
else
    echo 'dotfiles: shell image missing; run `dotfiles shell apply`' >&2
end
