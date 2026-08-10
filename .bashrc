case $- in
  *i*) ;;
  *) return ;;
esac

_dotfiles_shell_image="$HOME/.local/state/dotfiles/shell/v2/current/public/bash/init.bash"
if [ -r "$_dotfiles_shell_image" ]; then
  . "$_dotfiles_shell_image"
else
  printf 'dotfiles: shell image missing; run `dotfiles shell apply`\n' >&2
fi
unset _dotfiles_shell_image
