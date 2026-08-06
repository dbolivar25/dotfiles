# Dotfiles

Personal configuration for macOS, managed as a single GNU Stow package. The
repository lives at `~/dotfiles`; Stow links its contents into `~` without
turning the home directory into a Git repository.

## Install or repair links

```sh
brew install stow
cd "$HOME/dotfiles"
stow --restow --target="$HOME" .
```

Preview link changes before applying them:

```sh
cd "$HOME/dotfiles"
stow --simulate --verbose=2 --restow --target="$HOME" .
```

## Update workflow

1. Change the linked file normally in `~` or edit it directly in `~/dotfiles`.
2. Review the repository with `git status` and `git diff`.
3. Run the relevant config check before committing.
4. Keep unrelated tools in separate commits so changes remain easy to undo.

## Local state and secrets

Machine-local and generated files are ignored by Git. Shell credentials belong
in `~/dotfiles/secrets.zsh`, `.config/fish/secrets.fish`, or
`.config/nushell/secrets.nu`; committed shell files may source them but must not
contain credential values.
