# Dotfiles

Personal configuration for macOS, managed as a single GNU Stow package. The
repository lives at `~/dotfiles`; Stow links its contents into `~` without
turning the home directory into a Git repository.

## Bootstrap

```sh
brew install stow uv
cd "$HOME/dotfiles"
uv tool install --editable ./tools/dotfiles-cli
dotfiles stow --apply
dotfiles doctor
```

The CLI runs in dry mode by default. Every state-changing command requires an
explicit `--apply`; read-only commands such as `doctor`, `status`, and `list`
run immediately.

## Shared shell configuration

Zsh remains the login shell, Fish is the primary interactive shell, and
Nushell remains a native secondary shell. They share data and behavior
contracts without sharing shell syntax:

```text
.config/shell/
├── paths                 # Ordered PATH entries
├── required-commands     # Commands that must resolve in every shell
├── environment.d/        # One public value per file
├── secrets.d/            # One ignored private value per file
├── behavior/             # Cross-shell behavior contracts
├── runtime-ownership.toml # Runtime ownership intent and migration gates
├── integrations/         # Tool-local shell adapters and support markers
└── adapters/             # Fish, Zsh, and Nushell loaders
```

Fish and Nushell retain their native prompts; Zsh uses Starship. Editor
selection is shared behavior: `nvim` locally and `vim` over SSH in all three
shells.

## Common operations

```sh
# Preview, then add a PATH entry.
dotfiles path add ~/.example/bin
dotfiles path add ~/.example/bin --apply

# Manage public values.
dotfiles env set EXAMPLE_HOME ~/example
dotfiles env set EXAMPLE_HOME ~/example --apply

# Manage private values without printing them.
dotfiles secret set EXAMPLE_TOKEN
dotfiles secret set EXAMPLE_TOKEN --apply

# Create adapters for a tool.
dotfiles integration init example
dotfiles integration init example --apply

# Preview or repair Stow links.
dotfiles stow
dotfiles stow --apply

# Verify the entire contract.
dotfiles doctor
```

Use global `--json` for automation:

```sh
dotfiles --json doctor
dotfiles --json path add ~/.example/bin
```

## Runtime ownership migration

Runtime consolidation is currently in **shadow validation**. The tracked
ownership file records the intended boundary without changing activation:

- mise is the candidate owner for Node, Ruby, Go, Java, Elixir, and Erlang,
  subject to compatibility and project proof.
- uv, rustup, OPAM, GHCup, Bun, and the Microsoft .NET installation remain the
  specialist owners for their existing runtimes.
- Elixir is retained and is not a pruning candidate. Mise ownership of Elixir
  and its compatible Erlang/OTP version remains provisional until its tooling
  and retained projects pass migration checks.

Inspect what each shell resolves without running the inspected runtime
executables:

```sh
dotfiles runtime status
dotfiles --json runtime status
dotfiles runtime configure
dotfiles runtime configure --apply
```

The report classifies path ownership, cross-shell disagreement, legacy
shadowing, and unresolved migration gates. Existing conflicts are warnings and
data: this command does not claim ownership is consolidated, enable mise,
install versions, edit projects, or remove legacy managers. Those changes come
only after the required versions and representative projects pass parity checks
in Fish, Zsh, and Nushell.

`runtime configure` renders `.config/mise/config.toml` only from explicitly
approved ownership declarations. Node currently approves an ordinary home
default of `lts` and lets project `.nvmrc` files override it. The command is a
dry run unless passed `--apply`; it writes configuration only and does not run
mise, install Node, activate mise, or claim that Node ownership is consolidated.

## Installing programs

Prefer installers that can skip shell modification. When an installer may
write to shell configuration, start with a clean repository and capture it:

```sh
dotfiles capture -- brew install example
dotfiles capture --apply -- brew install example
```

`capture` previews by default. With `--apply`, it runs the command, reports the
resulting Git changes, and runs the doctor. Translate installer changes into
the shared model instead of retaining inline blocks:

- PATH directory: `dotfiles path add`
- Public value: `dotfiles env set`
- Private value: `dotfiles secret set`
- Initialization hook: `dotfiles integration init`

An integration must have an adapter or an explicit `native`, `unsupported`, or
`deferred` marker for Fish, Zsh, and Nushell.

## Development

The CLI is a dependency-free Python package run by UV's isolated interpreter:

```sh
uv run --project tools/dotfiles-cli ruff check tools/dotfiles-cli
uv run --project tools/dotfiles-cli ruff format --check tools/dotfiles-cli
uv run --project tools/dotfiles-cli \
  python -m unittest discover -s tools/dotfiles-cli/tests -v
```

## Update workflow

1. Change the linked file normally in `~` or edit it directly in `~/dotfiles`.
2. Review the repository with `git status` and `git diff`.
3. Run `dotfiles doctor` before committing.
4. Keep unrelated tools in separate commits so changes remain easy to undo.

## Local state and secrets

Machine-local and generated files are ignored by Git. Shell credentials live
as mode `0600` files under `.config/shell/secrets.d/`. The doctor compares their
behavior across shells by hash and never prints their values.
