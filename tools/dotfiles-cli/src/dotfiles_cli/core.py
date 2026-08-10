from __future__ import annotations

import json
import os
import re
import shlex
import stat
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

ENVIRONMENT_KEY = re.compile(r"^[A-Z_][A-Z0-9_]*$")
SHELLS = ("bash", "fish", "zsh", "nu")


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
    def shell_manifest(self) -> Path:
        return self.shell_root / "shell.toml"

    @property
    def native_dir(self) -> Path:
        return self.shell_root / "native"

    @property
    def private_shell_manifest(self) -> Path:
        return self.home / ".config" / "dotfiles" / "shell.local.toml"

    @property
    def shell_state_dir(self) -> Path:
        return self.home / ".local" / "state" / "dotfiles" / "shell"

    @property
    def shell_v2_dir(self) -> Path:
        return self.shell_state_dir / "v2"

    @property
    def active_shell_dir(self) -> Path:
        return self.shell_v2_dir / "current"


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


def expand_home(value: str, home: Path) -> str:
    return value.replace("${HOME}", str(home))


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


def shell_probe_command(context: Context, shell: str, body: str) -> list[str]:
    public = context.active_shell_dir / "public"
    if shell == "bash":
        quoted = shlex.quote(str(public / "bash" / "init.bash"))
        return ["/bin/bash", "--noprofile", "--norc", "-c", f". {quoted}; {body}"]
    if shell == "fish":
        quoted = shlex.quote(str(public / "fish" / "init.fish"))
        return ["fish", "--no-config", "-c", f"source {quoted}; {body}"]
    if shell == "zsh":
        quoted = shlex.quote(str(public / "zsh" / "init.zsh"))
        return ["zsh", "-dfc", f"source {quoted}; {body}"]
    if shell == "nu":
        env = json.dumps(str(public / "nu" / "env.nu"))
        config = json.dumps(str(public / "nu" / "config.nu"))
        return [
            "nu",
            "--no-config-file",
            "-c",
            f"source {env}; source {config}; {body}",
        ]
    raise DotfilesError(f"unsupported shell: {shell}")
