from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .core import (
    ENVIRONMENT_KEY,
    SHELLS,
    Context,
    expand_home,
    integration_coverage,
    read_data_lines,
    source_line_for_nu,
)


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    detail: str


@dataclass
class DoctorReport:
    checks: list[Check]

    @property
    def failed(self) -> bool:
        return any(check.status == "fail" for check in self.checks)

    def render(self, as_json: bool = False) -> str:
        if as_json:
            return json.dumps(
                {
                    "ok": not self.failed,
                    "checks": [asdict(check) for check in self.checks],
                },
                indent=2,
                sort_keys=True,
            )
        labels = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
        return "\n".join(
            f"{labels[check.status]:4} {check.name}: {check.detail}"
            for check in self.checks
        )


def _run(
    arguments: list[str],
    *,
    environment: dict[str, str],
    cwd: Path,
    timeout: int = 20,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _clean_environment(context: Context, ssh: bool = False) -> dict[str, str]:
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


def _adapter_command(context: Context, shell: str, body: str) -> list[str]:
    adapter = (
        context.shell_root
        / "adapters"
        / {"fish": "fish.fish", "zsh": "zsh.zsh", "nu": "nu.nu"}[shell]
    )
    quoted = shlex.quote(str(adapter))
    if shell == "fish":
        return ["fish", "--no-config", "-c", f"source {quoted}; {body}"]
    if shell == "zsh":
        return ["zsh", "-dfc", f"source {quoted}; {body}"]
    return ["nu", "--no-config-file", "-c", f"source {quoted}; {body}"]


def _environment_values(
    context: Context, shell: str, keys: list[str]
) -> list[str] | None:
    if not keys:
        return []
    if shell == "zsh":
        joined = " ".join(keys)
        body = (
            f"for key in {joined}; do print -rn -- \"${{(P)key}}\"; printf '\\0'; done"
        )
    elif shell == "fish":
        joined = " ".join(keys)
        body = f"for key in {joined}; set -q $key; and printf '%s' $$key; printf '\\0'; end"
    else:
        quoted_keys = " ".join(json.dumps(key) for key in keys)
        body = (
            f"[{quoted_keys}] | each {{|key| $env | get -i $key | default '' }} "
            "| to json --raw"
        )
    result = _run(
        _adapter_command(context, shell, body),
        environment=_clean_environment(context),
        cwd=context.repo,
    )
    if result.returncode != 0:
        return None
    if shell == "nu":
        try:
            return json.loads(result.stdout.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    values = result.stdout.decode().split("\0")
    return values[:-1] if values and values[-1] == "" else values


def _path_values(context: Context, shell: str) -> list[str] | None:
    body = {
        "zsh": "printf '%s\\0' $path",
        "fish": "printf '%s\\0' $PATH",
        "nu": "$env.PATH | to json --raw",
    }[shell]
    result = _run(
        _adapter_command(context, shell, body),
        environment=_clean_environment(context),
        cwd=context.repo,
    )
    if result.returncode != 0:
        return None
    if shell == "nu":
        try:
            return json.loads(result.stdout.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    values = result.stdout.decode().split("\0")
    return values[:-1] if values and values[-1] == "" else values


def _check_startup(context: Context, shell: str) -> Check:
    commands = {
        "zsh": ["zsh", "-lic", "exit 0"],
        "fish": ["fish", "-lc", "exit 0"],
        "nu": ["nu", "--login", "-c", "exit 0"],
    }
    result = _run(
        commands[shell],
        environment=_clean_environment(context),
        cwd=context.repo,
    )
    if result.returncode == 0:
        return Check("pass", f"{shell} startup", "clean login startup succeeded")
    error = result.stderr.decode(errors="replace").strip().splitlines()
    return Check("fail", f"{shell} startup", error[-1] if error else "startup failed")


def _check_editor(context: Context, shell: str, ssh: bool) -> Check:
    body = {
        "zsh": "print -r -- $EDITOR",
        "fish": "echo $EDITOR",
        "nu": "print $env.EDITOR",
    }[shell]
    result = _run(
        _adapter_command(context, shell, body),
        environment=_clean_environment(context, ssh=ssh),
        cwd=context.repo,
    )
    profile = "ssh" if ssh else "local"
    expected = (
        (context.shell_root / "behavior" / "editor" / profile).read_text().strip()
    )
    actual = result.stdout.decode().strip()
    if result.returncode == 0 and actual == expected:
        return Check("pass", f"{shell} editor ({profile})", actual)
    return Check(
        "fail",
        f"{shell} editor ({profile})",
        f"expected {expected}, got {actual or '<none>'}",
    )


def _check_required_command(context: Context, shell: str, command: str) -> Check:
    body = {
        "zsh": f"command -v {shlex.quote(command)} >/dev/null",
        "fish": f"command -q {shlex.quote(command)}",
        "nu": f"if ((which {json.dumps(command)}) | is-empty) {{ exit 1 }}",
    }[shell]
    result = _run(
        _adapter_command(context, shell, body),
        environment=_clean_environment(context),
        cwd=context.repo,
    )
    status = "pass" if result.returncode == 0 else "fail"
    detail = "resolves" if status == "pass" else "does not resolve"
    return Check(status, f"{shell} command {command}", detail)


def _check_shared_environment(context: Context, checks: list[Check]) -> None:
    public_files = sorted(
        path for path in context.environment_dir.glob("*") if path.is_file()
    )
    secret_files = sorted(
        path for path in context.secrets_dir.glob("*") if path.is_file()
    )
    files = public_files + secret_files
    keys = [path.name for path in files]
    expected = [
        path.read_text().rstrip("\n").replace("${HOME}", str(context.home))
        for path in files
    ]
    expected_hashes = [hashlib.sha256(value.encode()).hexdigest() for value in expected]
    for shell in SHELLS:
        values = _environment_values(context, shell, keys)
        if values is None or len(values) != len(keys):
            checks.append(
                Check(
                    "fail",
                    f"{shell} shared environment",
                    "could not read all managed values",
                )
            )
            continue
        hashes = [hashlib.sha256(value.encode()).hexdigest() for value in values]
        mismatches = [
            key
            for key, wanted, actual in zip(keys, expected_hashes, hashes)
            if wanted != actual
        ]
        if mismatches:
            checks.append(
                Check(
                    "fail",
                    f"{shell} shared environment",
                    f"mismatch: {', '.join(mismatches)}",
                )
            )
        else:
            checks.append(
                Check(
                    "pass", f"{shell} shared environment", f"{len(keys)} values match"
                )
            )


def run_doctor(context: Context) -> DoctorReport:
    checks: list[Check] = []

    required_files = [
        context.paths_file,
        context.shell_root / "required-commands",
        context.shell_root / "adapters" / "fish.fish",
        context.shell_root / "adapters" / "zsh.zsh",
        context.shell_root / "adapters" / "nu.nu",
    ]
    missing = [
        str(path.relative_to(context.repo))
        for path in required_files
        if not path.is_file()
    ]
    checks.append(
        Check(
            "fail" if missing else "pass",
            "shell module",
            f"missing: {', '.join(missing)}" if missing else "required files exist",
        )
    )
    if missing:
        return DoctorReport(checks)

    invalid_keys = [
        path.name
        for path in context.environment_dir.glob("*")
        if path.is_file() and not ENVIRONMENT_KEY.fullmatch(path.name)
    ]
    checks.append(
        Check(
            "fail" if invalid_keys else "pass",
            "environment keys",
            f"invalid: {', '.join(invalid_keys)}"
            if invalid_keys
            else "all names are valid",
        )
    )

    entries = read_data_lines(context.paths_file)
    duplicates = sorted({entry for entry in entries if entries.count(entry) > 1})
    checks.append(
        Check(
            "fail" if duplicates else "pass",
            "PATH duplicates",
            f"duplicate: {', '.join(duplicates)}" if duplicates else "none",
        )
    )
    absent = [
        entry
        for entry in entries
        if not Path(expand_home(entry, context.home)).is_dir()
    ]
    checks.append(
        Check(
            "warn" if absent else "pass",
            "PATH directories",
            f"missing: {', '.join(absent)}" if absent else "all exist",
        )
    )

    ignored_probe = context.secrets_dir / "_doctor_probe"
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", str(ignored_probe)],
            cwd=context.repo,
            check=False,
        ).returncode
        == 0
    )
    checks.append(
        Check(
            "pass" if ignored else "fail",
            "secret Git ignore",
            "secrets.d is ignored" if ignored else "secrets.d is not ignored",
        )
    )
    insecure = [
        path.name
        for path in context.secrets_dir.glob("*")
        if path.is_file() and (path.stat().st_mode & 0o077)
    ]
    checks.append(
        Check(
            "fail" if insecure else "pass",
            "secret permissions",
            f"not mode 0600: {', '.join(insecure)}" if insecure else "private",
        )
    )
    if context.secrets_dir.exists():
        directory_private = (context.secrets_dir.stat().st_mode & 0o077) == 0
        checks.append(
            Check(
                "pass" if directory_private else "fail",
                "secret directory permissions",
                "private" if directory_private else "expected mode 0700",
            )
        )

    nu_adapter_text = context.nu_adapter.read_text()
    for directory in sorted(
        path for path in context.integrations_dir.glob("*") if path.is_dir()
    ):
        coverage = integration_coverage(directory)
        missing_shells = [
            shell for shell, state in coverage.items() if state == "missing"
        ]
        status = "fail" if missing_shells else "pass"
        detail = ", ".join(f"{shell}={state}" for shell, state in coverage.items())
        checks.append(Check(status, f"integration {directory.name}", detail))
        if coverage["nu"] == "adapter":
            source_line = source_line_for_nu(directory.name)
            checks.append(
                Check(
                    "pass" if source_line in nu_adapter_text else "fail",
                    f"integration {directory.name} Nushell load",
                    "registered"
                    if source_line in nu_adapter_text
                    else "source line missing",
                )
            )

    for shell in SHELLS:
        checks.append(_check_startup(context, shell))
        checks.append(_check_editor(context, shell, ssh=False))
        checks.append(_check_editor(context, shell, ssh=True))

        actual_paths = _path_values(context, shell)
        wanted_paths = [
            expand_home(entry, context.home)
            for entry in entries
            if Path(expand_home(entry, context.home)).is_dir()
        ]
        if actual_paths is None:
            checks.append(Check("fail", f"{shell} PATH", "could not read PATH"))
        else:
            duplicate_paths = sorted(
                {entry for entry in actual_paths if actual_paths.count(entry) > 1}
            )
            managed_in_actual = [
                entry for entry in actual_paths if entry in wanted_paths
            ]
            if duplicate_paths:
                checks.append(
                    Check(
                        "fail",
                        f"{shell} PATH",
                        f"duplicates: {', '.join(duplicate_paths)}",
                    )
                )
            elif managed_in_actual != wanted_paths:
                checks.append(
                    Check("fail", f"{shell} PATH", "managed entries are out of order")
                )
            else:
                checks.append(
                    Check(
                        "pass",
                        f"{shell} PATH",
                        f"{len(wanted_paths)} managed entries ordered and unique",
                    )
                )

    _check_shared_environment(context, checks)

    for command in read_data_lines(context.shell_root / "required-commands"):
        for shell in SHELLS:
            checks.append(_check_required_command(context, shell, command))

    return DoctorReport(checks)
