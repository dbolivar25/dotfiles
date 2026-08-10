# Dotfiles

Personal macOS configuration managed as one GNU Stow package. The repository
lives at `~/dotfiles`; Stow links its contents into `~` without turning the home
directory into a Git repository.

## Bootstrap

```sh
brew install stow uv
cd "$HOME/dotfiles"
uv tool install --editable ./tools/dotfiles-cli
dotfiles stow --apply
dotfiles doctor
```

Preview-oriented commands remain dry by default. `dotfiles shell apply` and
`dotfiles shell rollback` are deliberately explicit verbs and run immediately.

## Shared shell configuration

Zsh is the login shell, Fish is the primary interactive shell, Bash is the
fallback, and Nushell keeps its structured native behavior. Human-edited shell
source has one shared manifest and a small native escape hatch:

```text
.config/shell/
├── shell.toml             # PATH, env, editor, shortcuts, wrappers, generators
└── native/
    ├── bash.bash
    ├── zsh.zsh
    ├── nu/config.nu
    └── fish/functions/    # Fish-native autoload files
```

`dotfiles shell apply` parses the TOML, copies the native files, prebuilds the
Starship and Zoxide hooks, syntax-checks every shell, and atomically
selects one immutable release pair under
`~/.local/state/dotfiles/shell/v2/`. Shell startup follows one fixed symlink and
does no discovery, TOML parsing, or code generation. `dotfiles shell rollback`
atomically swaps the active and rollback releases; running it again moves
forward again.

Machine-private values have one source file:
`~/.config/dotfiles/shell.local.toml`. It and its generated state are mode
`0600`; their directories are mode `0700`. Public generated files are scanned
for home paths, repository paths, and private values before activation. Nothing
generated is tracked in Git. Active and rollback releases keep complete private
state; older releases keep only public Fish autoloads needed by running shells.

Fish gets native abbreviations and autoloaded functions. Bash and Zsh get
aliases and functions. Nushell keeps its default prompt, structured `ls`, and
native state-changing commands. The external `jj` command is not shadowed. Bun
stays on PATH without startup completion work, and Mise is used through shims
without an activation hook. Mise also reads Node version files and pnpm
`packageManager` pins, so projects can override the global defaults.

Use `[shortcuts]` in `shell.toml` for textual expansion and `[forwarders]` when
the behavior is exactly “external executable + fixed arguments + forwarded
arguments.” Put caller-state behavior such as `cd`, environment mutation,
virtual-environment activation, prompts, or structured Nu commands in
`native/`. Put deterministic third-party initialization in `[integrations]`.

## Common operations

```sh
# Edit public behavior, then validate and activate it.
nvim ~/.config/shell/shell.toml
dotfiles shell check
dotfiles shell apply

# Manage private values without printing them.
dotfiles secret set EXAMPLE_TOKEN
dotfiles secret set EXAMPLE_TOKEN --apply
dotfiles secret unset EXAMPLE_TOKEN
dotfiles secret unset EXAMPLE_TOKEN --apply

# Roll back the active shell image. Run it again to move forward.
dotfiles shell rollback

# Preview or repair Stow links.
dotfiles stow
dotfiles stow --apply

# Verify source, state, startup, and cross-shell behavior.
dotfiles doctor
```

Use global `--json` for automation:

```sh
dotfiles --json doctor
dotfiles --json status
```

## Installing programs

Prefer installers that can skip shell modification. When an installer may
write to shell configuration, start with a clean repository and capture it:

```sh
dotfiles capture -- brew install example
dotfiles capture --apply -- brew install example
```

Translate installer changes into `shell.toml` or `native/` instead of retaining
inline blocks:

- PATH, public value, shortcut, wrapper, or generator: `shell.toml`
- Private value: `dotfiles secret set`
- Shell-specific behavior: the corresponding file under `native/`

Generated Bash remains compatible with macOS Bash 3.2. Secret changes rebuild
an already-active shell image automatically. After a public or native source
edit, run `dotfiles shell check` and `dotfiles shell apply`.

## Development

The CLI is a dependency-free Python package run by UV's isolated interpreter:

```sh
uv run --project tools/dotfiles-cli ruff check tools/dotfiles-cli
uv run --project tools/dotfiles-cli ruff format --check tools/dotfiles-cli
uv run --project tools/dotfiles-cli \
  python -m unittest discover -s tools/dotfiles-cli/tests -v
```

## Update workflow

1. Change the linked file normally in `~` or edit it in `~/dotfiles`.
2. Run `dotfiles shell check` and `dotfiles shell apply` after shell-source edits.
3. Review `git status` and `git diff`.
4. Run `dotfiles doctor` before committing.

## Local state and secrets

Shell credentials live in the mode-`0600` file
`~/.config/dotfiles/shell.local.toml`. Generated releases live outside Git under
`~/.local/state/dotfiles/shell/v2/`. The doctor compares private behavior across
shells by hash and never prints values.
