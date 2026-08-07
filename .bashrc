case $- in
  *i*) ;;
  *) return ;;
esac

[ -r "$HOME/.config/shell/adapters/bash.bash" ] &&
  . "$HOME/.config/shell/adapters/bash.bash"
