# Homebrew's prefix is stable on this Apple Silicon host. Keep the equivalent
# environment without running `brew shellenv` and `path_helper` on every login.
export HOMEBREW_PREFIX=/opt/homebrew
export HOMEBREW_CELLAR=/opt/homebrew/Cellar
export HOMEBREW_REPOSITORY=/opt/homebrew
[[ -z ${MANPATH-} ]] || export MANPATH=":${MANPATH#:}"
typeset -aT INFOPATH infopath
infopath=(/opt/homebrew/share/info $infopath '')
typeset -U infopath
if [[ -d /opt/homebrew/share/zsh/site-functions ]]; then
  fpath=(/opt/homebrew/share/zsh/site-functions $fpath)
  typeset -U fpath
fi

# Added by OrbStack: command-line tools and integration
# This won't be added again if you remove it.
source ~/.orbstack/shell/init.zsh 2>/dev/null || :
