from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import stat
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

ENVIRONMENT_KEY = re.compile(r"^[A-Z_][A-Z0-9_]*$")
INTEGRATION_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SHELLS = ("bash", "fish", "zsh", "nu")
SHELL_ADAPTERS = {
    "bash": "bash.bash",
    "fish": "fish.fish",
    "zsh": "zsh.zsh",
    "nu": "nu.nu",
}
SHELL_MARKERS = ("native", "unsupported", "deferred")


class DotfilesError(RuntimeError):
    """A user-actionable dotfiles error."""


@dataclass(frozen=True)
class Context:
    repo: Path
    home: Path
    invocation_dir: Path

    @classmethod
    def discover(cls, repo: str | None = None) -> Context:
        home = Path.home()
        selected = Path(repo or os.environ.get("DOTFILES_REPO", home / "dotfiles"))
        selected = selected.expanduser().resolve()
        if not (selected / ".git").is_dir():
            raise DotfilesError(f"not a dotfiles Git repository: {selected}")
        return cls(repo=selected, home=home, invocation_dir=Path.cwd())

    @property
    def shell_root(self) -> Path:
        return self.repo / ".config" / "shell"

    @property
    def paths_file(self) -> Path:
        return self.shell_root / "paths"

    @property
    def environment_dir(self) -> Path:
        return self.shell_root / "environment.d"

    @property
    def secrets_dir(self) -> Path:
        return self.shell_root / "secrets.d"

    @property
    def integrations_dir(self) -> Path:
        return self.shell_root / "integrations"

    @property
    def nu_adapter(self) -> Path:
        return self.shell_root / "adapters" / "nu.nu"

    @property
    def runtime_ownership_file(self) -> Path:
        return self.shell_root / "runtime-ownership.toml"

    @property
    def mise_config_file(self) -> Path:
        return self.repo / ".config" / "mise" / "config.toml"


@dataclass(frozen=True)
class Action:
    operation: str
    path: str | None = None
    detail: str | None = None


@dataclass
class Plan:
    summary: str
    actions: list[Action] = field(default_factory=list)

    def add(
        self, operation: str, path: Path | str | None = None, detail: str | None = None
    ) -> None:
        self.actions.append(
            Action(operation, str(path) if path is not None else None, detail)
        )

    def render(self, as_json: bool = False, applied: bool = False) -> str:
        payload = {
            "summary": self.summary,
            "changes": bool(self.actions),
            "applied": applied,
            "actions": [asdict(action) for action in self.actions],
        }
        if as_json:
            return json.dumps(payload, indent=2, sort_keys=True)
        lines = [self.summary]
        if not self.actions:
            lines.append("No changes planned.")
        else:
            for action in self.actions:
                target = f" {action.path}" if action.path else ""
                detail = f" — {action.detail}" if action.detail else ""
                lines.append(f"- {action.operation}{target}{detail}")
        return "\n".join(lines)


def validate_environment_key(key: str) -> str:
    if not ENVIRONMENT_KEY.fullmatch(key):
        raise DotfilesError(f"invalid environment key: {key}")
    return key


def validate_integration_name(name: str) -> str:
    if not INTEGRATION_NAME.fullmatch(name):
        raise DotfilesError(f"invalid integration name: {name}")
    return name


def normalize_path_entry(value: str, home: Path) -> str:
    value = value.strip()
    if not value:
        raise DotfilesError("PATH entry cannot be empty")
    home_string = str(home)
    if value == home_string:
        return "${HOME}"
    if value.startswith(f"{home_string}/"):
        return "${HOME}" + value[len(home_string) :]
    if value == "~":
        return "${HOME}"
    if value.startswith("~/"):
        return "${HOME}/" + value[2:]
    if not value.startswith(("/", "${HOME}/")):
        raise DotfilesError("PATH entry must be absolute or home-relative")
    return value.rstrip("/") or "/"


def expand_home(value: str, home: Path) -> str:
    return value.replace("${HOME}", str(home))


def read_data_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def update_data_lines(path: Path, values: list[str]) -> str:
    comments: list[str] = []
    if path.exists():
        for line in path.read_text().splitlines():
            if line.lstrip().startswith("#") or not line.strip():
                comments.append(line)
            else:
                break
    prefix = "\n".join(comments).rstrip()
    body = "\n".join(values)
    return f"{prefix}\n{body}\n" if prefix else f"{body}\n"


def atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
        if mode is not None:
            temporary.chmod(mode)
        elif path.exists():
            temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def integration_coverage(directory: Path) -> dict[str, str]:
    coverage: dict[str, str] = {}
    for shell in SHELLS:
        adapter = directory / SHELL_ADAPTERS[shell]
        if adapter.is_file():
            coverage[shell] = "adapter"
            continue
        for marker in SHELL_MARKERS:
            if (directory / f"{shell}.{marker}").is_file():
                coverage[shell] = marker
                break
        else:
            coverage[shell] = "missing"
    return coverage


def source_line_for_nu(name: str) -> str:
    return f"source ~/.config/shell/integrations/{name}/nu.nu"


def clean_shell_environment(context: Context, ssh: bool = False) -> dict[str, str]:
    path = ":".join(
        [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
            str(context.home / ".local" / "bin"),
            str(context.home / ".cargo" / "bin"),
        ]
    )
    environment = {
        "HOME": str(context.home),
        "LOGNAME": os.environ.get("LOGNAME", context.home.name),
        "PATH": path,
        "SHELL": "/bin/zsh",
        "TERM": "xterm-256color",
        "USER": os.environ.get("USER", context.home.name),
    }
    if ssh:
        environment["SSH_CONNECTION"] = "127.0.0.1 1 127.0.0.1 2"
    return environment


def adapter_command(context: Context, shell: str, body: str) -> list[str]:
    adapter = context.shell_root / "adapters" / SHELL_ADAPTERS[shell]
    quoted = shlex.quote(str(adapter))
    if shell == "bash":
        return ["/bin/bash", "--noprofile", "--norc", "-c", f". {quoted}; {body}"]
    if shell == "fish":
        return ["fish", "--no-config", "-c", f"source {quoted}; {body}"]
    if shell == "zsh":
        return ["zsh", "-dfc", f"source {quoted}; {body}"]
    if shell == "nu":
        return ["nu", "--no-config-file", "-c", f"source {quoted}; {body}"]
    raise DotfilesError(f"unsupported shell: {shell}")
