from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import tomllib

from .core import (
    ENVIRONMENT_KEY,
    SHELLS,
    Context,
    DotfilesError,
    Plan,
    atomic_write,
    expand_home,
)

COMPILER_VERSION = 7
SHORTCUT_NAME = re.compile(r"^[A-Za-z0-9_.:-]+$")
INTEGRATION_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
POSIX_SHELLS = ("bash", "zsh")
PROTECTED_NU_NAMES = {"jj", "ls"}
POSIX_NATIVE_COMMAND = re.compile(
    r"^\s*(?:function\s+)?([A-Za-z0-9_.:-]+)\s*\(\)", re.MULTILINE
)
NU_NATIVE_COMMAND = re.compile(
    r"^\s*(?:(?:export\s+)?def(?:\s+--[A-Za-z0-9_-]+)*|(?:export\s+)?alias)"
    r"\s+([A-Za-z0-9_.:-]+)\b",
    re.MULTILINE,
)
ShellCheck = tuple[str, str, str]


@dataclass(frozen=True)
class Shortcut:
    name: str
    shells: tuple[str, ...]
    expansion: str


@dataclass(frozen=True)
class Forwarder:
    name: str
    shells: tuple[str, ...]
    description: str
    arguments: tuple[str, ...]


@dataclass(frozen=True)
class GeneratorRecipe:
    integration: str
    shell: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class GeneratorResult:
    integration: str
    shell: str
    command: tuple[str, ...]
    executable: str
    version: str
    output: str


@dataclass(frozen=True)
class ShellConfig:
    environment: dict[str, str]
    paths: tuple[str, ...]
    required_commands: tuple[str, ...]
    editor_local: str
    editor_ssh: str
    shortcuts: tuple[Shortcut, ...]
    forwarders: tuple[Forwarder, ...]
    generators: tuple[GeneratorRecipe, ...]


@dataclass(frozen=True)
class ShellImage:
    digest: str
    public_digest: str
    private_digest: str
    public_files: dict[str, str]
    private_files: dict[str, str]
    manifest: str


def _load_toml(path: Path, *, required: bool) -> dict[str, object]:
    if not path.is_file():
        if required:
            raise DotfilesError(f"missing shell manifest: {path}")
        return {}
    try:
        return tomllib.loads(path.read_text())
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise DotfilesError(f"invalid TOML in {path}: {error}") from error


def _reject_unknown(
    values: dict[str, object], allowed: set[str], *, location: str
) -> None:
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise DotfilesError(f"{location}: unknown key: {unknown[0]}")


def _string_list(
    value: object, *, location: str, allow_empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DotfilesError(f"{location}: expected a list of strings")
    if not allow_empty and not value:
        raise DotfilesError(f"{location}: must not be empty")
    if len(value) != len(set(value)):
        raise DotfilesError(f"{location}: duplicate value")
    return value


def _parse_shells(value: object, *, location: str) -> tuple[str, ...]:
    requested = _string_list(value, location=location)
    invalid = sorted(set(requested) - set(SHELLS))
    if invalid:
        raise DotfilesError(f"{location}: invalid shell: {invalid[0]}")
    return tuple(shell for shell in SHELLS if shell in requested)


def _validate_home_expression(value: str, *, location: str) -> None:
    remaining = value.replace("${HOME}", "")
    if "${" in remaining:
        raise DotfilesError(f"{location}: only ${{HOME}} interpolation is supported")


def _native_command_names(context: Context, shell: str) -> set[str]:
    if shell in POSIX_SHELLS:
        path = context.native_dir / f"{shell}.{shell}"
        return (
            set(POSIX_NATIVE_COMMAND.findall(path.read_text()))
            if path.is_file()
            else set()
        )
    if shell == "nu":
        path = context.native_dir / "nu" / "config.nu"
        return (
            set(NU_NATIVE_COMMAND.findall(path.read_text()))
            if path.is_file()
            else set()
        )
    directory = context.native_dir / "fish" / "functions"
    return (
        {path.stem for path in directory.glob("*.fish")}
        if directory.is_dir()
        else set()
    )


def _reject_native_collisions(
    context: Context,
    shortcuts: list[Shortcut],
    forwarders: list[Forwarder],
) -> None:
    native = {shell: _native_command_names(context, shell) for shell in SHELLS}
    for command in (*shortcuts, *forwarders):
        for shell in command.shells:
            if command.name in native[shell]:
                raise DotfilesError(
                    f"shared command conflicts with native {shell}: {command.name}"
                )


def load_shell_config(context: Context) -> ShellConfig:
    path = context.shell_manifest
    data = _load_toml(path, required=True)
    _reject_unknown(
        data,
        {
            "schema",
            "paths",
            "required_commands",
            "environment",
            "editor",
            "shortcuts",
            "forwarders",
            "integrations",
        },
        location=str(path),
    )
    if type(data.get("schema")) is not int or data["schema"] != 1:
        raise DotfilesError(f"{path}: schema must be 1")

    paths = _string_list(data.get("paths"), location=f"{path}: paths")
    for value in paths:
        _validate_home_expression(value, location=f"{path}: paths")
        if (
            not value.startswith("/")
            and value != "${HOME}"
            and not value.startswith("${HOME}/")
        ):
            raise DotfilesError(f"{path}: paths: expected an absolute path: {value}")

    required_commands = _string_list(
        data.get("required_commands"), location=f"{path}: required_commands"
    )
    for command in required_commands:
        if not SHORTCUT_NAME.fullmatch(command):
            raise DotfilesError(f"{path}: required_commands: invalid name: {command}")

    raw_environment = data.get("environment")
    if not isinstance(raw_environment, dict):
        raise DotfilesError(f"{path}: environment must be a table")
    environment: dict[str, str] = {}
    for key, value in raw_environment.items():
        if not ENVIRONMENT_KEY.fullmatch(key):
            raise DotfilesError(f"{path}: environment: invalid name: {key}")
        if not isinstance(value, str):
            raise DotfilesError(f"{path}: environment.{key}: expected a string")
        _validate_home_expression(value, location=f"{path}: environment.{key}")
        environment[key] = value

    raw_editor = data.get("editor")
    if not isinstance(raw_editor, dict):
        raise DotfilesError(f"{path}: editor must be a table")
    _reject_unknown(raw_editor, {"local", "ssh"}, location=f"{path}: editor")
    if set(raw_editor) != {"local", "ssh"}:
        raise DotfilesError(f"{path}: editor requires local and ssh")
    if not all(
        isinstance(raw_editor[key], str) and raw_editor[key] for key in raw_editor
    ):
        raise DotfilesError(f"{path}: editor values must be non-empty strings")

    raw_shortcuts = data.get("shortcuts")
    if not isinstance(raw_shortcuts, dict):
        raise DotfilesError(f"{path}: shortcuts must be a table")
    shortcuts: list[Shortcut] = []
    for name, value in raw_shortcuts.items():
        location = f"{path}: shortcuts.{name}"
        if not SHORTCUT_NAME.fullmatch(name):
            raise DotfilesError(f"{location}: invalid name")
        if isinstance(value, str):
            expansion = value
            shells = SHELLS
        elif isinstance(value, dict):
            _reject_unknown(value, {"expansion", "shells"}, location=location)
            expansion = value.get("expansion")
            if not isinstance(expansion, str):
                raise DotfilesError(f"{location}.expansion: expected a string")
            shells = _parse_shells(value.get("shells"), location=f"{location}.shells")
        else:
            raise DotfilesError(f"{location}: expected a string or table")
        if not expansion.strip():
            raise DotfilesError(f"{location}: empty expansion")
        if "nu" in shells and name in PROTECTED_NU_NAMES:
            raise DotfilesError(f"{location}: refusing to shadow Nushell {name}")
        shortcuts.append(Shortcut(name, tuple(shells), expansion))

    raw_forwarders = data.get("forwarders")
    if not isinstance(raw_forwarders, dict):
        raise DotfilesError(f"{path}: forwarders must be a table")
    forwarders: list[Forwarder] = []
    for name, value in raw_forwarders.items():
        location = f"{path}: forwarders.{name}"
        if not SHORTCUT_NAME.fullmatch(name):
            raise DotfilesError(f"{location}: invalid name")
        if not isinstance(value, dict):
            raise DotfilesError(f"{location}: expected a table")
        _reject_unknown(value, {"argv", "description", "shells"}, location=location)
        arguments = tuple(_string_list(value.get("argv"), location=f"{location}.argv"))
        description = value.get("description")
        if not isinstance(description, str):
            raise DotfilesError(f"{location}.description: expected a string")
        shells = (
            _parse_shells(value["shells"], location=f"{location}.shells")
            if "shells" in value
            else SHELLS
        )
        if "nu" in shells and name in PROTECTED_NU_NAMES:
            raise DotfilesError(f"{location}: refusing to shadow Nushell {name}")
        forwarders.append(Forwarder(name, tuple(shells), description, arguments))

    raw_integrations = data.get("integrations")
    if not isinstance(raw_integrations, dict):
        raise DotfilesError(f"{path}: integrations must be a table")
    generators: list[GeneratorRecipe] = []
    for integration, value in raw_integrations.items():
        location = f"{path}: integrations.{integration}"
        if not INTEGRATION_NAME.fullmatch(integration):
            raise DotfilesError(f"{location}: invalid name")
        if not isinstance(value, dict) or not value:
            raise DotfilesError(f"{location}: expected a non-empty table")
        _reject_unknown(value, set(SHELLS), location=location)
        for shell in SHELLS:
            if shell not in value:
                continue
            command = tuple(_string_list(value[shell], location=f"{location}.{shell}"))
            generators.append(GeneratorRecipe(integration, shell, command))

    _reject_native_collisions(context, shortcuts, forwarders)
    return ShellConfig(
        environment=environment,
        paths=tuple(paths),
        required_commands=tuple(required_commands),
        editor_local=raw_editor["local"],
        editor_ssh=raw_editor["ssh"],
        shortcuts=tuple(shortcuts),
        forwarders=tuple(forwarders),
        generators=tuple(generators),
    )


def load_private_secrets(context: Context) -> dict[str, str]:
    path = context.private_shell_manifest
    if not path.exists():
        return {}
    if path.is_symlink():
        raise DotfilesError(f"private shell manifest must not be a symlink: {path}")
    if path.stat().st_mode & 0o777 != 0o600:
        raise DotfilesError(f"private shell manifest must be mode 0600: {path}")
    if path.parent.stat().st_mode & 0o077:
        raise DotfilesError(f"private shell directory must be mode 0700: {path.parent}")
    data = _load_toml(path, required=True)
    _reject_unknown(data, {"schema", "secrets"}, location=str(path))
    if type(data.get("schema")) is not int or data["schema"] != 1:
        raise DotfilesError(f"{path}: schema must be 1")
    raw_secrets = data.get("secrets")
    if not isinstance(raw_secrets, dict):
        raise DotfilesError(f"{path}: secrets must be a table")
    secrets: dict[str, str] = {}
    for key, value in raw_secrets.items():
        if not ENVIRONMENT_KEY.fullmatch(key):
            raise DotfilesError(f"{path}: secrets: invalid name: {key}")
        if not isinstance(value, str) or not value:
            raise DotfilesError(f"{path}: secrets.{key}: expected a non-empty string")
        secrets[key] = value
    return secrets


def serialize_private_shell_config(secrets: dict[str, str]) -> str:
    lines = ["schema = 1", "", "[secrets]"]
    lines.extend(
        f"{key} = {json.dumps(value, ensure_ascii=True)}"
        for key, value in sorted(secrets.items())
    )
    return "\n".join(lines) + "\n"


def write_private_shell_config(context: Context, secrets: dict[str, str]) -> None:
    for key, value in secrets.items():
        if not ENVIRONMENT_KEY.fullmatch(key) or not value:
            raise DotfilesError(f"invalid private secret: {key}")
    parent = context.private_shell_manifest.parent
    parent.mkdir(parents=True, exist_ok=True)
    parent.chmod(0o700)
    atomic_write(
        context.private_shell_manifest,
        serialize_private_shell_config(secrets),
        mode=0o600,
    )


def _fish_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _home_expression(value: str, shell: str) -> str:
    parts = value.split("${HOME}")
    if shell in POSIX_SHELLS:
        return '"${HOME}"'.join(shlex.quote(part) for part in parts)
    if shell == "fish":
        return "$HOME".join(_fish_quote(part) for part in parts)
    raise DotfilesError(f"home expression is not supported for {shell}")


def _render_environment(config: ShellConfig, shell: str) -> str:
    lines: list[str] = []
    for key, value in config.environment.items():
        if shell in POSIX_SHELLS:
            lines.append(f"export {key}={_home_expression(value, shell)}")
        elif shell == "fish":
            lines.append(f"set -gx {key} {_home_expression(value, shell)}")
        else:
            lines.append(
                f"$env.{key} = ({json.dumps(value)} | str replace --all '${{HOME}}' $env.HOME)"
            )
    return "\n".join(lines)


def _render_paths(config: ShellConfig, shell: str) -> str:
    entries = config.paths
    if shell == "bash":
        values = " ".join(_home_expression(entry, shell) for entry in entries)
        return f"""_dotfiles_managed_paths=({values})
_dotfiles_unique_paths=()
for _dotfiles_path in "${{_dotfiles_managed_paths[@]}}"; do
  [ -d "$_dotfiles_path" ] && _dotfiles_unique_paths+=("$_dotfiles_path")
done
IFS=: read -r -a _dotfiles_inherited_paths <<< "${{PATH-}}"
for _dotfiles_path in "${{_dotfiles_inherited_paths[@]}}"; do
  [ -n "$_dotfiles_path" ] || continue
  _dotfiles_seen=false
  for _dotfiles_existing in "${{_dotfiles_unique_paths[@]}}"; do
    if [ "$_dotfiles_existing" = "$_dotfiles_path" ]; then
      _dotfiles_seen=true
      break
    fi
  done
  $_dotfiles_seen || _dotfiles_unique_paths+=("$_dotfiles_path")
done
_dotfiles_joined=
for _dotfiles_path in "${{_dotfiles_unique_paths[@]}}"; do
  _dotfiles_joined="${{_dotfiles_joined:+$_dotfiles_joined:}}$_dotfiles_path"
done
export PATH="$_dotfiles_joined"
unset _dotfiles_managed_paths _dotfiles_inherited_paths _dotfiles_unique_paths
unset _dotfiles_path _dotfiles_existing _dotfiles_seen _dotfiles_joined"""
    if shell == "zsh":
        values = " ".join(_home_expression(entry, shell) for entry in entries)
        return f"""typeset -a _dotfiles_managed_paths
typeset -a _dotfiles_valid_paths
_dotfiles_managed_paths=({values})
for _dotfiles_path in "${{_dotfiles_managed_paths[@]}}"; do
  [[ -d "$_dotfiles_path" ]] && _dotfiles_valid_paths+=("$_dotfiles_path")
done
path=("${{_dotfiles_valid_paths[@]}}" "${{path[@]}}")
typeset -U path PATH
export PATH
unset _dotfiles_managed_paths _dotfiles_valid_paths _dotfiles_path"""
    if shell == "fish":
        values = " ".join(_home_expression(entry, shell) for entry in entries)
        return f"""set -l _dotfiles_managed_paths {values}
set -l _dotfiles_paths
for _dotfiles_path in $_dotfiles_managed_paths $PATH
    test -d $_dotfiles_path; or contains -- $_dotfiles_path $PATH; or continue
    contains -- $_dotfiles_path $_dotfiles_paths; or set -a _dotfiles_paths $_dotfiles_path
end
set -gx PATH $_dotfiles_paths
set -e _dotfiles_managed_paths _dotfiles_paths _dotfiles_path"""
    values = " ".join(json.dumps(entry) for entry in entries)
    return f"""let _dotfiles_managed_paths = ([{values}]
    | each {{|entry| $entry | str replace --all '${{HOME}}' $env.HOME }}
    | where {{|entry| $entry | path exists }})
$env.PATH = ($_dotfiles_managed_paths | append $env.PATH | uniq)"""


def _render_editor(config: ShellConfig, shell: str) -> str:
    local = config.editor_local
    ssh = config.editor_ssh
    if shell == "bash":
        return f"""if [ -n "${{SSH_CONNECTION:-}}" ]; then
  export EDITOR={shlex.quote(ssh)} VISUAL={shlex.quote(ssh)}
else
  export EDITOR={shlex.quote(local)} VISUAL={shlex.quote(local)}
fi"""
    if shell == "zsh":
        return f"""if [[ -n "${{SSH_CONNECTION:-}}" ]]; then
  export EDITOR={shlex.quote(ssh)} VISUAL={shlex.quote(ssh)}
else
  export EDITOR={shlex.quote(local)} VISUAL={shlex.quote(local)}
fi"""
    if shell == "fish":
        return f"""if set -q SSH_CONNECTION
    set -gx EDITOR {_fish_quote(ssh)}
else
    set -gx EDITOR {_fish_quote(local)}
end
set -gx VISUAL $EDITOR"""
    return f"""let _dotfiles_editor = if (($env | get -i SSH_CONNECTION | default '') | is-empty) {{ {json.dumps(local)} }} else {{ {json.dumps(ssh)} }}
$env.EDITOR = $_dotfiles_editor
$env.VISUAL = $_dotfiles_editor"""


def _generator_environment(context: Context, config: ShellConfig) -> dict[str, str]:
    entries = [expand_home(entry, context.home) for entry in config.paths]
    stable = [entry for entry in entries if Path(entry).is_dir()] + [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ]
    return {
        "HOME": str(context.home),
        "LOGNAME": context.home.name,
        "PATH": ":".join(dict.fromkeys(stable)),
        "SHELL": "/bin/zsh",
        "TERM": "xterm-256color",
        "USER": context.home.name,
    }


def _run_generator(
    context: Context, config: ShellConfig, recipe: GeneratorRecipe
) -> GeneratorResult:
    environment = _generator_environment(context, config)
    executable = shutil.which(recipe.command[0], path=environment["PATH"])
    if executable is None:
        raise DotfilesError(
            f"generator is not installed ({recipe.integration}.{recipe.shell}): "
            f"{recipe.command[0]}"
        )
    resolved = (executable, *recipe.command[1:])
    outputs: list[str] = []
    for _ in range(2):
        result = subprocess.run(
            resolved,
            cwd=context.home,
            env=environment,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            raise DotfilesError(
                f"generator failed ({recipe.integration}.{recipe.shell}): {detail}"
            )
        outputs.append(result.stdout)
    if outputs[0] != outputs[1]:
        raise DotfilesError(
            f"generator output is not deterministic: "
            f"{recipe.integration}.{recipe.shell}"
        )
    version_result = subprocess.run(
        [executable, "--version"],
        cwd=context.home,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    version = (version_result.stdout or version_result.stderr).strip().splitlines()
    return GeneratorResult(
        integration=recipe.integration,
        shell=recipe.shell,
        command=recipe.command,
        executable=str(Path(executable).resolve()),
        version=version[0] if version else "unknown",
        output=outputs[0],
    )


def _guard_generated(result: GeneratorResult) -> str:
    output = result.output.rstrip()
    if result.shell == "nu":
        return output
    if result.shell == "bash":
        body = "\n".join(f"  {line}" for line in output.splitlines())
        return f"if [[ $- == *i* ]]; then\n{body}\nfi"
    if result.shell == "zsh":
        body = "\n".join(f"  {line}" for line in output.splitlines())
        return f"if [[ -o interactive ]]; then\n{body}\nfi"
    body = "\n".join(f"    {line}" for line in output.splitlines())
    return f"if status is-interactive\n{body}\nend"


def _integration_content(
    context: Context, config: ShellConfig, shell: str
) -> tuple[str, tuple[GeneratorResult, ...]]:
    chunks: list[str] = []
    generated: list[GeneratorResult] = []
    for recipe in config.generators:
        if recipe.shell != shell:
            continue
        result = _run_generator(context, config, recipe)
        chunks.append(f"# {recipe.integration} (prebuilt)\n{_guard_generated(result)}")
        generated.append(result)
    return "\n\n".join(chunks), tuple(generated)


def _render_forwarders(forwarders: tuple[Forwarder, ...], shell: str) -> str:
    chunks: list[str] = []
    for forwarder in forwarders:
        if shell not in forwarder.shells:
            continue
        executable, *fixed = forwarder.arguments
        if shell in POSIX_SHELLS:
            arguments = " ".join(shlex.quote(value) for value in (executable, *fixed))
            chunks.append(f'{forwarder.name}() {{\n  command {arguments} "$@"\n}}')
        elif shell == "fish":
            fixed_arguments = " ".join(_fish_quote(value) for value in fixed)
            suffix = f" {fixed_arguments}" if fixed_arguments else ""
            chunks.append(
                f"function {forwarder.name} --wraps={executable} "
                f"--description={_fish_quote(forwarder.description)}\n"
                f"    command {_fish_quote(executable)}{suffix} $argv\nend"
            )
        else:
            fixed_arguments = " ".join(json.dumps(value) for value in fixed)
            suffix = f" {fixed_arguments}" if fixed_arguments else ""
            chunks.append(
                f"def --wrapped {forwarder.name} [...rest: string] {{\n"
                f"    ^{executable}{suffix} ...$rest\n}}"
            )
    return "\n\n".join(chunks)


def _render_shortcuts(shortcuts: tuple[Shortcut, ...], shell: str) -> str:
    lines: list[str] = []
    for shortcut in shortcuts:
        if shell not in shortcut.shells:
            continue
        if shell in POSIX_SHELLS:
            lines.append(f"alias {shortcut.name}={shlex.quote(shortcut.expansion)}")
        elif shell == "fish":
            lines.append(
                f"abbr --add -- {shortcut.name} {_fish_quote(shortcut.expansion)}"
            )
        else:
            lines.append(f"alias {shortcut.name} = {shortcut.expansion}")
    return "\n".join(lines)


def _render_secrets(secrets: dict[str, str], shell: str) -> str:
    lines: list[str] = []
    for key, value in sorted(secrets.items()):
        if shell in POSIX_SHELLS:
            lines.append(f"export {key}={shlex.quote(value)}")
        elif shell == "fish":
            lines.append(f"set -gx {key} {_fish_quote(value)}")
    return "\n".join(lines)


def _native_text(context: Context, shell: str) -> str:
    path = context.native_dir / f"{shell}.{shell}"
    return path.read_text().rstrip() if path.is_file() else ""


def _nu_native_text(context: Context, kind: str) -> str:
    path = context.native_dir / "nu" / f"{kind}.nu"
    return path.read_text().rstrip() if path.is_file() else ""


def _source_fingerprints(context: Context) -> dict[str, str]:
    paths = [context.shell_manifest]
    if context.native_dir.exists():
        paths.extend(path for path in context.native_dir.rglob("*") if path.is_file())
    return {
        str(path.relative_to(context.shell_root)): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(paths)
    }


def _digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _portable_path(context: Context, value: str) -> str:
    home = str(context.home)
    if value == home:
        return "${HOME}"
    if value.startswith(f"{home}/"):
        return "${HOME}" + value[len(home) :]
    return value


def compile_shell_image(context: Context) -> ShellImage:
    config = load_shell_config(context)
    secrets = load_private_secrets(context)
    integrations: dict[str, str] = {}
    generators: list[GeneratorResult] = []
    for shell in SHELLS:
        content, results = _integration_content(context, config, shell)
        integrations[shell] = content
        generators.extend(results)

    private_files: dict[str, str] = {}
    for shell in ("bash", "zsh", "fish"):
        chunks = [_render_secrets(secrets, shell), integrations[shell]]
        private_files[f"{shell}/init.{shell}"] = (
            "# Generated private machine-local shell state.\n"
            + "\n\n".join(chunk for chunk in chunks if chunk).rstrip()
            + "\n"
        )
    private_files["nu/secrets.nuon"] = (
        json.dumps(secrets, indent=2, sort_keys=True) + "\n"
    )
    private_files["nu/config.nu"] = (
        "# Generated private machine-local shell integrations.\n"
        + integrations["nu"].rstrip()
        + "\n"
    )

    bash_chunks = [
        "# Generated by `dotfiles shell apply`; do not edit.",
        _render_environment(config, "bash"),
        _render_paths(config, "bash"),
        _render_editor(config, "bash"),
        (
            '[ -r "$DOTFILES_SHELL_RELEASE_ROOT/private/bash/init.bash" ] && '
            '. "$DOTFILES_SHELL_RELEASE_ROOT/private/bash/init.bash"'
        ),
        _native_text(context, "bash"),
        _render_forwarders(config.forwarders, "bash"),
        _render_shortcuts(config.shortcuts, "bash"),
        "unset DOTFILES_SHELL_RELEASE_ROOT",
    ]
    zsh_chunks = [
        "# Generated by `dotfiles shell apply`; do not edit.",
        _render_environment(config, "zsh"),
        _render_paths(config, "zsh"),
        _render_editor(config, "zsh"),
        (
            '[[ -r "$DOTFILES_SHELL_RELEASE_ROOT/private/zsh/init.zsh" ]] && '
            'source "$DOTFILES_SHELL_RELEASE_ROOT/private/zsh/init.zsh"'
        ),
        _native_text(context, "zsh"),
        _render_forwarders(config.forwarders, "zsh"),
        _render_shortcuts(config.shortcuts, "zsh"),
        "unset DOTFILES_SHELL_RELEASE_ROOT",
    ]
    fish_chunks = [
        "# Generated by `dotfiles shell apply`; do not edit.",
        _render_environment(config, "fish"),
        _render_paths(config, "fish"),
        _render_editor(config, "fish"),
        (
            "contains -- $DOTFILES_SHELL_RELEASE_ROOT/public/fish/functions "
            "$fish_function_path; or set -p fish_function_path "
            "$DOTFILES_SHELL_RELEASE_ROOT/public/fish/functions"
        ),
        (
            'test -r "$DOTFILES_SHELL_RELEASE_ROOT/private/fish/init.fish"; and '
            'source "$DOTFILES_SHELL_RELEASE_ROOT/private/fish/init.fish"'
        ),
        _render_shortcuts(config.shortcuts, "fish"),
        "set -e DOTFILES_SHELL_RELEASE_ROOT",
    ]

    nu_env_chunks = [
        "# Generated by `dotfiles shell apply`; do not edit.",
        _render_environment(config, "nu"),
        _render_paths(config, "nu"),
        _render_editor(config, "nu"),
        _nu_native_text(context, "env"),
    ]
    nu_config_chunks = [
        "# Generated by `dotfiles shell apply`; do not edit.",
        _nu_native_text(context, "config"),
        _render_forwarders(config.forwarders, "nu"),
        _render_shortcuts(config.shortcuts, "nu"),
    ]

    public_files = {
        "bash/init.bash": "\n\n".join(chunk for chunk in bash_chunks if chunk).rstrip()
        + "\n",
        "zsh/init.zsh": "\n\n".join(chunk for chunk in zsh_chunks if chunk).rstrip()
        + "\n",
        "fish/init.fish": "\n\n".join(chunk for chunk in fish_chunks if chunk).rstrip()
        + "\n",
        "nu/env.nu": "\n\n".join(chunk for chunk in nu_env_chunks if chunk).rstrip()
        + "\n",
        "nu/config.nu": "\n\n".join(
            chunk for chunk in nu_config_chunks if chunk
        ).rstrip()
        + "\n",
    }
    fish_functions = context.native_dir / "fish" / "functions"
    if fish_functions.exists():
        for path in sorted(fish_functions.glob("*.fish")):
            public_files[f"fish/functions/{path.name}"] = path.read_text()
    for forwarder in config.forwarders:
        if "fish" not in forwarder.shells:
            continue
        name = f"fish/functions/{forwarder.name}.fish"
        if name in public_files:
            raise DotfilesError(
                f"Fish forwarder conflicts with native function: {forwarder.name}"
            )
        public_files[name] = _render_forwarders((forwarder,), "fish") + "\n"
    _check_public_files(context, secrets, public_files)
    source_hashes = _source_fingerprints(context)
    private_source_hash = (
        hashlib.sha256(context.private_shell_manifest.read_bytes()).hexdigest()
        if context.private_shell_manifest.is_file()
        else hashlib.sha256(b"").hexdigest()
    )
    generator_fingerprints = [
        {
            "integration": item.integration,
            "shell": item.shell,
            "command": list(item.command),
            "executable": _portable_path(context, item.executable),
            "version": item.version,
            "output_sha256": hashlib.sha256(item.output.encode()).hexdigest(),
        }
        for item in generators
    ]
    public_payload = {
        "compiler_version": COMPILER_VERSION,
        "sources": source_hashes,
        "files": public_files,
    }
    public_digest = _digest(public_payload)
    private_payload = {
        "compiler_version": COMPILER_VERSION,
        "source_sha256": private_source_hash,
        "files": private_files,
        "generators": generator_fingerprints,
    }
    private_digest = _digest(private_payload)
    digest = _digest(
        {
            "compiler_version": COMPILER_VERSION,
            "public_digest": public_digest,
            "private_digest": private_digest,
        }
    )
    manifest = (
        json.dumps(
            {
                "schema": 2,
                "compiler_version": COMPILER_VERSION,
                "digest": digest,
                "public_digest": public_digest,
                "private_digest": private_digest,
                "public_sources": source_hashes,
                "private_source_sha256": private_source_hash,
                "public_files": {
                    name: hashlib.sha256(content.encode()).hexdigest()
                    for name, content in sorted(public_files.items())
                },
                "private_files": {
                    name: hashlib.sha256(content.encode()).hexdigest()
                    for name, content in sorted(private_files.items())
                },
                "generators": generator_fingerprints,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return ShellImage(
        digest=digest,
        public_digest=public_digest,
        private_digest=private_digest,
        public_files=public_files,
        private_files=private_files,
        manifest=manifest,
    )


def _check_public_files(
    context: Context, secrets: dict[str, str], files: dict[str, str]
) -> None:
    forbidden = {"home path": str(context.home), "repository path": str(context.repo)}
    forbidden.update(
        {f"secret {key}": value for key, value in secrets.items() if value}
    )
    for name, content in files.items():
        for label, value in forbidden.items():
            if value in content:
                raise DotfilesError(f"public shell file contains {label}: {name}")


def _write_files(root: Path, files: dict[str, str], mode: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    for name, content in files.items():
        atomic_write(root / name, content, mode=mode)
    for directory in (path for path in root.rglob("*") if path.is_dir()):
        directory.chmod(0o700)


def _write_release(root: Path, image: ShellImage) -> None:
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    _write_files(root / "public", image.public_files, 0o644)
    _write_files(root / "private", image.private_files, 0o600)
    atomic_write(root / "manifest.json", image.manifest, mode=0o600)


def _validate_tree(root: Path, image: ShellImage) -> None:
    expected = {
        **{
            f"public/{name}": (content, 0o644)
            for name, content in image.public_files.items()
        },
        **{
            f"private/{name}": (content, 0o600)
            for name, content in image.private_files.items()
        },
        "manifest.json": (image.manifest, 0o600),
    }
    actual = {
        str(path.relative_to(root)): path for path in root.rglob("*") if path.is_file()
    }
    if set(actual) != set(expected):
        raise DotfilesError(f"existing shell release has unexpected files: {root}")
    unsafe_directories = [
        path
        for path in (root, *root.rglob("*"))
        if path.is_dir() and path.stat().st_mode & 0o777 != 0o700
    ]
    if unsafe_directories:
        raise DotfilesError(
            f"existing shell release has unsafe directory mode: {unsafe_directories[0]}"
        )
    for name, (content, mode) in expected.items():
        path = actual[name]
        if path.read_text() != content:
            raise DotfilesError(f"existing shell release has drifted: {path}")
        if path.stat().st_mode & 0o777 != mode:
            raise DotfilesError(f"existing shell release has unsafe mode: {path}")


def _validate_release(
    context: Context, root: Path, expected_digest: str | None = None
) -> None:
    manifest = _release_manifest(root, expected_digest)
    public_hashes = manifest.get("public_files")
    private_hashes = manifest.get("private_files")
    compiler_version = manifest.get("compiler_version")
    public_sources = manifest.get("public_sources")
    private_source_hash = manifest.get("private_source_sha256")
    generators = manifest.get("generators")
    if (
        not isinstance(compiler_version, int)
        or not isinstance(public_hashes, dict)
        or not isinstance(private_hashes, dict)
        or not isinstance(public_sources, dict)
        or not isinstance(private_source_hash, str)
        or not isinstance(generators, list)
        or not all(
            isinstance(name, str) and isinstance(digest, str)
            for hashes in (public_hashes, private_hashes)
            for name, digest in hashes.items()
        )
    ):
        raise DotfilesError(f"invalid shell release metadata: {root}")
    expected_modes = {
        **{f"public/{name}": 0o644 for name in public_hashes},
        **{f"private/{name}": 0o600 for name in private_hashes},
        "manifest.json": 0o600,
    }
    actual = {
        str(path.relative_to(root)): path for path in root.rglob("*") if path.is_file()
    }
    if set(actual) != set(expected_modes) or root.is_symlink():
        raise DotfilesError(f"shell release has unexpected files: {root}")
    unsafe_directories = [
        path
        for path in (root, *root.rglob("*"))
        if path.is_dir() and (path.is_symlink() or path.stat().st_mode & 0o777 != 0o700)
    ]
    if unsafe_directories:
        raise DotfilesError(
            f"shell release has unsafe directory: {unsafe_directories[0]}"
        )
    contents: dict[str, str] = {}
    for name, mode in expected_modes.items():
        path = actual[name]
        if path.is_symlink() or path.stat().st_mode & 0o777 != mode:
            raise DotfilesError(f"shell release has unsafe mode: {path}")
        if name == "manifest.json":
            continue
        try:
            content = path.read_text()
        except UnicodeDecodeError as error:
            raise DotfilesError(
                f"shell release contains invalid text: {path}"
            ) from error
        expected_hash = (
            public_hashes[name.removeprefix("public/")]
            if name.startswith("public/")
            else private_hashes[name.removeprefix("private/")]
        )
        if hashlib.sha256(content.encode()).hexdigest() != expected_hash:
            raise DotfilesError(f"shell release has drifted: {path}")
        contents[name] = content
    public_files = {
        name.removeprefix("public/"): content
        for name, content in contents.items()
        if name.startswith("public/")
    }
    private_files = {
        name.removeprefix("private/"): content
        for name, content in contents.items()
        if name.startswith("private/")
    }
    public_digest = _digest(
        {
            "compiler_version": compiler_version,
            "sources": public_sources,
            "files": public_files,
        }
    )
    private_digest = _digest(
        {
            "compiler_version": compiler_version,
            "source_sha256": private_source_hash,
            "files": private_files,
            "generators": generators,
        }
    )
    digest = _digest(
        {
            "compiler_version": compiler_version,
            "public_digest": public_digest,
            "private_digest": private_digest,
        }
    )
    if (
        manifest.get("public_digest") != public_digest
        or manifest.get("private_digest") != private_digest
        or manifest.get("digest") != digest
        or (expected_digest or root.name) != digest
    ):
        raise DotfilesError(f"shell release digest has drifted: {root}")

    with tempfile.TemporaryDirectory(prefix="dotfiles-shell-validate-") as temporary:
        validation_home = Path(temporary)
        environment = {**os.environ, "HOME": str(validation_home)}
        commands = [
            (
                "bash public",
                ["/bin/bash", "-n", str(root / "public/bash/init.bash")],
            ),
            (
                "bash private",
                ["/bin/bash", "-n", str(root / "private/bash/init.bash")],
            ),
            ("zsh public", ["zsh", "-n", str(root / "public/zsh/init.zsh")]),
            ("zsh private", ["zsh", "-n", str(root / "private/zsh/init.zsh")]),
            (
                "fish public",
                ["fish", "--no-execute", str(root / "public/fish/init.fish")],
            ),
            (
                "fish private",
                ["fish", "--no-execute", str(root / "private/fish/init.fish")],
            ),
            (
                "nu complete",
                [
                    "nu",
                    "--no-config-file",
                    "-c",
                    (
                        f"source {json.dumps(str(root / 'public/nu/env.nu'))}; "
                        f"open {json.dumps(str(root / 'private/nu/secrets.nuon'))} "
                        "| load-env; "
                        f"source {json.dumps(str(root / 'public/nu/config.nu'))}; "
                        f"source {json.dumps(str(root / 'private/nu/config.nu'))}"
                    ),
                ],
            ),
        ]
        for label, command in commands:
            if shutil.which(command[0]) is None and not Path(command[0]).is_file():
                continue
            result = subprocess.run(
                command,
                cwd=validation_home,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                raise DotfilesError(f"generated {label} syntax failed: {detail}")
    for path in sorted((root / "public/fish/functions").glob("*.fish")):
        result = subprocess.run(
            ["fish", "--no-execute", str(path)],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            raise DotfilesError(
                f"generated Fish function syntax failed ({path.name}): "
                f"{result.stderr.strip()}"
            )


def _publish_release(context: Context, image: ShellImage) -> Path:
    root = context.shell_v2_dir / "releases"
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    target = root / image.digest
    if target.exists():
        if not (target / "private").exists():
            expected = {
                **{
                    f"public/{name}": (content, 0o644)
                    for name, content in image.public_files.items()
                },
                "manifest.json": (image.manifest, 0o600),
            }
            actual = {
                str(path.relative_to(target)): path
                for path in target.rglob("*")
                if path.is_file()
            }
            if set(actual) != set(expected):
                raise DotfilesError(
                    f"pruned shell release has unexpected files: {target}"
                )
            for name, (content, mode) in expected.items():
                path = actual[name]
                if (
                    path.is_symlink()
                    or path.read_text() != content
                    or path.stat().st_mode & 0o777 != mode
                ):
                    raise DotfilesError(f"pruned shell release has drifted: {path}")
            stage = Path(tempfile.mkdtemp(prefix=".private-", dir=target))
            try:
                _write_files(stage / "private", image.private_files, 0o600)
                (stage / "private").replace(target / "private")
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
        _validate_tree(target, image)
        _validate_release(context, target)
        return target
    stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=root))
    try:
        _write_release(stage, image)
        _validate_release(context, stage, image.digest)
        stage.replace(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return target


def _release_manifest(
    release: Path, expected_digest: str | None = None
) -> dict[str, object]:
    try:
        manifest = json.loads((release / "manifest.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise DotfilesError(f"invalid shell release: {release}") from error
    if manifest.get("schema") != 2 or manifest.get("digest") != (
        expected_digest or release.name
    ):
        raise DotfilesError(f"invalid shell release manifest: {release}")
    return manifest


def _activation_digest(active: str, rollback: str | None) -> str:
    return _digest({"active_release": active, "rollback_release": rollback})


def _activation_public_files(active: str) -> dict[str, str]:
    release = f"$HOME/.local/state/dotfiles/shell/v2/releases/{active}"
    nu_release = f"~/.local/state/dotfiles/shell/v2/releases/{active}"
    return {
        "bash/init.bash": (
            f'DOTFILES_SHELL_RELEASE_ROOT="{release}"\n'
            '. "$DOTFILES_SHELL_RELEASE_ROOT/public/bash/init.bash"\n'
        ),
        "zsh/init.zsh": (
            f'DOTFILES_SHELL_RELEASE_ROOT="{release}"\n'
            'source "$DOTFILES_SHELL_RELEASE_ROOT/public/zsh/init.zsh"\n'
        ),
        "fish/init.fish": (
            f"set -g DOTFILES_SHELL_RELEASE_ROOT {release}\n"
            "source $DOTFILES_SHELL_RELEASE_ROOT/public/fish/init.fish\n"
        ),
        "nu/env.nu": (
            f"source {nu_release}/public/nu/env.nu\n"
            "let _dotfiles_secrets = "
            f"('{nu_release}/private/nu/secrets.nuon' | path expand)\n"
            "if ($_dotfiles_secrets | path exists) { "
            "open $_dotfiles_secrets | load-env }\n"
            f"source {nu_release}/public/nu/config.nu\n"
            f"source {nu_release}/private/nu/config.nu\n"
        ),
        "nu/config.nu": f"# Release {active} was loaded from env.nu.\n",
    }


def _create_activation(context: Context, active: Path, rollback: Path | None) -> Path:
    _validate_release(context, active)
    if rollback is not None:
        _validate_release(context, rollback)
    root = context.shell_v2_dir / "activations"
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    digest = _activation_digest(active.name, rollback.name if rollback else None)
    target = root / digest
    payload = {
        "schema": 1,
        "digest": digest,
        "active_release": active.name,
        "rollback_release": rollback.name if rollback else None,
    }
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if not target.exists():
        stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=root))
        try:
            stage.chmod(0o700)
            _write_files(stage / "public", _activation_public_files(active.name), 0o644)
            (stage / "private").symlink_to(
                Path("../../releases") / active.name / "private",
                target_is_directory=True,
            )
            atomic_write(stage / "manifest.json", content, mode=0o600)
            stage.replace(target)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    _validate_activation(context, target)
    return target


def _validate_activation(
    context: Context, activation: Path
) -> tuple[Path, Path | None]:
    try:
        manifest = json.loads((activation / "manifest.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise DotfilesError(f"invalid shell activation: {activation}") from error
    if manifest.get("schema") != 1 or manifest.get("digest") != activation.name:
        raise DotfilesError(f"invalid shell activation manifest: {activation}")
    active_name = manifest.get("active_release")
    rollback_name = manifest.get("rollback_release")
    if not isinstance(active_name, str) or not (
        rollback_name is None or isinstance(rollback_name, str)
    ):
        raise DotfilesError(f"invalid shell activation releases: {activation}")
    releases = context.shell_v2_dir / "releases"
    active = releases / active_name
    rollback = releases / rollback_name if rollback_name else None
    _release_manifest(active)
    if rollback is not None:
        _release_manifest(rollback)
    public = activation / "public"
    private = activation / "private"
    if not public.is_dir() or not private.is_symlink():
        raise DotfilesError(f"invalid shell activation links: {activation}")
    if private.resolve() != (active / "private").resolve():
        raise DotfilesError(f"shell activation links have drifted: {activation}")
    expected = _activation_public_files(active.name)
    actual = {
        str(path.relative_to(public)): path
        for path in public.rglob("*")
        if path.is_file()
    }
    if set(actual) != set(expected):
        raise DotfilesError(
            f"shell activation has unexpected public files: {activation}"
        )
    for name, content in expected.items():
        path = actual[name]
        if path.read_text() != content or path.stat().st_mode & 0o777 != 0o644:
            raise DotfilesError(f"shell activation public file has drifted: {path}")
    unsafe_directories = [
        path
        for path in (activation, public, *public.rglob("*"))
        if path.is_dir() and path.stat().st_mode & 0o777 != 0o700
    ]
    if unsafe_directories:
        raise DotfilesError(
            f"shell activation has unsafe directory mode: {unsafe_directories[0]}"
        )
    return active, rollback


def _selected_activation(context: Context) -> tuple[Path, Path, Path | None] | None:
    pointer = context.shell_v2_dir / "current"
    if not pointer.is_symlink():
        return None
    activation = pointer.resolve()
    active, rollback = _validate_activation(context, activation)
    return activation, active, rollback


def _replace_current(context: Context, activation: Path) -> None:
    root = context.shell_v2_dir
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    temporary = root / ".current.new"
    if temporary.exists() or temporary.is_symlink():
        temporary.unlink()
    temporary.symlink_to(activation.resolve().relative_to(root.resolve()))
    temporary.replace(root / "current")


def _prune_state(context: Context) -> tuple[int, int]:
    selected = _selected_activation(context)
    if selected is None:
        return 0, 0
    selected_activation, active, rollback = selected
    retained_releases = {active.name}
    if rollback is not None:
        retained_releases.add(rollback.name)

    removed_activations = 0
    activations = context.shell_v2_dir / "activations"
    if activations.is_dir():
        for path in activations.iterdir():
            if not path.is_dir() or path.resolve() == selected_activation.resolve():
                continue
            try:
                manifest = json.loads((path / "manifest.json").read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            if manifest.get("active_release") not in retained_releases:
                shutil.rmtree(path)
                removed_activations += 1

    removed_private_releases = 0
    releases = context.shell_v2_dir / "releases"
    if releases.is_dir():
        for path in releases.iterdir():
            private = path / "private"
            if (
                path.is_dir()
                and path.name not in retained_releases
                and private.is_dir()
                and not private.is_symlink()
            ):
                shutil.rmtree(private)
                removed_private_releases += 1
    return removed_activations, removed_private_releases


def check_shell_image(context: Context) -> Plan:
    image = compile_shell_image(context)
    with tempfile.TemporaryDirectory(prefix="dotfiles-shell-check-") as temporary:
        root = Path(temporary) / image.digest
        _write_release(root, image)
        _validate_release(context, root)
    return Plan(f"Shell image {image.digest} is valid")


def stage_shell_image(context: Context) -> ShellImage:
    image = compile_shell_image(context)
    _publish_release(context, image)
    return image


def activate_shell_image(context: Context, image: ShellImage) -> tuple[int, int]:
    target = context.shell_v2_dir / "releases" / image.digest
    if not target.is_dir():
        raise DotfilesError("shell image must be staged before activation")
    current = _selected_activation(context)
    if current is not None and current[1].resolve() == target.resolve():
        return _prune_state(context)
    rollback = current[1] if current is not None else None
    activation = _create_activation(context, target, rollback)
    _replace_current(context, activation)
    return _prune_state(context)


def apply_shell_image(context: Context) -> Plan:
    image = compile_shell_image(context)
    target = context.shell_v2_dir / "releases" / image.digest
    current = _selected_activation(context)
    plan = Plan(f"Apply shell image {image.digest}")
    if not target.exists():
        plan.add("stage-release", target, f"{len(image.public_files)} public files")
    if current is None or current[1].resolve() != target.resolve():
        plan.add("activate-release", context.shell_v2_dir / "current", image.digest)
    _publish_release(context, image)
    removed_activations, removed_private_releases = activate_shell_image(context, image)
    if removed_activations:
        plan.add(
            "prune-activation-history",
            context.shell_v2_dir / "activations",
            f"{removed_activations} obsolete activation(s)",
        )
    if removed_private_releases:
        plan.add(
            "prune-private-history",
            context.shell_v2_dir / "releases",
            f"{removed_private_releases} obsolete private release(s)",
        )
    return plan


def rollback_shell_image(context: Context) -> Plan:
    current = _selected_activation(context)
    if current is None:
        raise DotfilesError("no active shell image")
    _, active, rollback = current
    if rollback is None:
        raise DotfilesError("no previous shell image to roll back to")
    activation = _create_activation(context, rollback, active)
    plan = Plan(f"Roll back shell image to {rollback.name}")
    plan.add("activate-release", context.shell_v2_dir / "current", rollback.name)
    _replace_current(context, activation)
    removed_activations, removed_private_releases = _prune_state(context)
    if removed_activations:
        plan.add(
            "prune-activation-history",
            context.shell_v2_dir / "activations",
            f"{removed_activations} obsolete activation(s)",
        )
    if removed_private_releases:
        plan.add(
            "prune-private-history",
            context.shell_v2_dir / "releases",
            f"{removed_private_releases} obsolete private release(s)",
        )
    return plan


def selected_shell_releases(context: Context) -> tuple[str, str | None] | None:
    selected = _selected_activation(context)
    if selected is None:
        return None
    _, active, rollback = selected
    return active.name, rollback.name if rollback is not None else None


def collect_shell_image_checks(context: Context) -> list[ShellCheck]:
    checks: list[ShellCheck] = []
    root = context.shell_v2_dir
    private = context.private_shell_manifest
    if private.exists():
        private_ok = (
            not private.is_symlink()
            and private.stat().st_mode & 0o777 == 0o600
            and not (private.parent.stat().st_mode & 0o077)
        )
        checks.append(
            (
                "pass" if private_ok else "fail",
                "shell private source",
                "mode 0600 in a private directory"
                if private_ok
                else "expected a regular mode-0600 file in a mode-0700 directory",
            )
        )
    else:
        checks.append(("pass", "shell private source", "no private values configured"))
    if not root.is_dir():
        checks.append(("fail", "shell image", "run dotfiles shell apply"))
        return checks
    checks.append(
        (
            "pass" if not (root.stat().st_mode & 0o077) else "fail",
            "shell image permissions",
            "state directory is private"
            if not (root.stat().st_mode & 0o077)
            else "expected mode 0700",
        )
    )
    try:
        selected = _selected_activation(context)
    except DotfilesError as error:
        checks.append(("fail", "shell image activation", str(error)))
        return checks
    if selected is None:
        checks.append(("fail", "shell image activation", "run dotfiles shell apply"))
        return checks
    _, active, rollback = selected
    checks.append(
        (
            "pass",
            "shell image activation",
            f"release {active.name}"
            + (f", rollback {rollback.name}" if rollback is not None else ""),
        )
    )
    try:
        expected = compile_shell_image(context)
    except DotfilesError as error:
        checks.append(("fail", "shell image sources", str(error)))
        return checks
    checks.append(
        (
            "pass" if active.name == expected.digest else "fail",
            "shell image sources",
            "active image matches source"
            if active.name == expected.digest
            else f"run dotfiles shell apply ({expected.digest})",
        )
    )
    try:
        _validate_tree(active, expected)
    except DotfilesError as error:
        checks.append(("fail", "shell image integrity", str(error)))
    else:
        checks.append(("pass", "shell image integrity", "release files match manifest"))
    return checks
