from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .core import (
    SHELLS,
    Context,
    clean_shell_environment,
    expand_home,
    shell_probe_command,
)
from .shell_image import (
    ShellConfig,
    collect_shell_image_checks,
    load_private_secrets,
    load_shell_config,
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


def _environment_values(
    context: Context, shell: str, keys: list[str]
) -> list[str] | None:
    if not keys:
        return []
    if shell == "bash":
        joined = " ".join(keys)
        body = f"for key in {joined}; do printf '%s\\0' \"${{!key-}}\"; done"
    elif shell == "zsh":
        joined = " ".join(keys)
        body = (
            f"for key in {joined}; do print -rn -- \"${{(P)key}}\"; printf '\\0'; done"
        )
    elif shell == "fish":
        joined = " ".join(keys)
        body = (
            f"for key in {joined}; set -q $key; and printf '%s' $$key; "
            "printf '\\0'; end"
        )
    else:
        quoted_keys = " ".join(json.dumps(key) for key in keys)
        body = (
            f"[{quoted_keys}] | each {{|key| $env | get -i $key | default '' }} "
            "| to json --raw"
        )
    result = _run(
        shell_probe_command(context, shell, body),
        environment=clean_shell_environment(context),
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
        "bash": 'IFS=: read -r -a dotfiles_paths <<< "${PATH-}"; '
        "printf '%s\\0' \"${dotfiles_paths[@]}\"",
        "zsh": "printf '%s\\0' $path",
        "fish": "printf '%s\\0' $PATH",
        "nu": "$env.PATH | to json --raw",
    }[shell]
    result = _run(
        shell_probe_command(context, shell, body),
        environment=clean_shell_environment(context),
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
    if shell == "bash":
        environment = clean_shell_environment(context)
        environment["HISTFILE"] = "/dev/null"
        commands = (
            ["/bin/bash", "--login", "-ic", "exit 0"],
            [
                "/bin/bash",
                "--noprofile",
                "--rcfile",
                str(context.repo / ".bashrc"),
                "-ic",
                "exit 0",
            ],
        )
        results = [
            _run(command, environment=environment, cwd=context.repo)
            for command in commands
        ]
        if all(result.returncode == 0 for result in results):
            return Check(
                "pass", "bash startup", "clean login and non-login startup succeeded"
            )
        errors = [
            line
            for result in results
            for line in result.stderr.decode(errors="replace").strip().splitlines()
        ]
        return Check("fail", "bash startup", errors[-1] if errors else "startup failed")
    commands = {
        "zsh": ["zsh", "-lic", "exit 0"],
        "fish": ["fish", "-lc", "exit 0"],
        "nu": ["nu", "--login", "-c", "exit 0"],
    }
    result = _run(
        commands[shell],
        environment=clean_shell_environment(context),
        cwd=context.repo,
    )
    if result.returncode == 0:
        return Check("pass", f"{shell} startup", "clean login startup succeeded")
    error = result.stderr.decode(errors="replace").strip().splitlines()
    return Check("fail", f"{shell} startup", error[-1] if error else "startup failed")


def _check_editor(
    context: Context, config: ShellConfig, shell: str, ssh: bool
) -> Check:
    body = {
        "bash": "printf '%s\\n' \"$EDITOR\"",
        "zsh": "print -r -- $EDITOR",
        "fish": "echo $EDITOR",
        "nu": "print $env.EDITOR",
    }[shell]
    result = _run(
        shell_probe_command(context, shell, body),
        environment=clean_shell_environment(context, ssh=ssh),
        cwd=context.repo,
    )
    profile = "ssh" if ssh else "local"
    expected = config.editor_ssh if ssh else config.editor_local
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
        "bash": f"command -v {shlex.quote(command)} >/dev/null",
        "zsh": f"command -v {shlex.quote(command)} >/dev/null",
        "fish": f"command -q {shlex.quote(command)}",
        "nu": f"if ((which {json.dumps(command)}) | is-empty) {{ exit 1 }}",
    }[shell]
    result = _run(
        shell_probe_command(context, shell, body),
        environment=clean_shell_environment(context),
        cwd=context.repo,
    )
    status = "pass" if result.returncode == 0 else "fail"
    detail = "resolves" if status == "pass" else "does not resolve"
    return Check(status, f"{shell} command {command}", detail)


def _check_shared_environment(
    context: Context,
    config: ShellConfig,
    secrets: dict[str, str],
    checks: list[Check],
) -> None:
    values = {
        key: expand_home(value, context.home)
        for key, value in config.environment.items()
    }
    values.update(secrets)
    keys = sorted(values)
    expected_hashes = {
        key: hashlib.sha256(values[key].encode()).hexdigest() for key in keys
    }
    for shell in SHELLS:
        actual_values = _environment_values(context, shell, keys)
        if actual_values is None or len(actual_values) != len(keys):
            checks.append(
                Check(
                    "fail",
                    f"{shell} shared environment",
                    "could not read all managed values",
                )
            )
            continue
        actual_hashes = {
            key: hashlib.sha256(value.encode()).hexdigest()
            for key, value in zip(keys, actual_values, strict=True)
        }
        mismatches = [key for key in keys if expected_hashes[key] != actual_hashes[key]]
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
    required_files = [context.shell_manifest, context.native_dir]
    missing = [
        str(path.relative_to(context.repo))
        for path in required_files
        if not path.exists()
    ]
    checks.append(
        Check(
            "fail" if missing else "pass",
            "shell source",
            f"missing: {', '.join(missing)}"
            if missing
            else "manifest and native source exist",
        )
    )
    if missing:
        return DoctorReport(checks)

    config = load_shell_config(context)
    secrets = load_private_secrets(context)
    entries = list(config.paths)
    duplicates = sorted({entry for entry in entries if entries.count(entry) > 1})
    checks.append(
        Check(
            "fail" if duplicates else "pass",
            "PATH source duplicates",
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
    checks.extend(Check(*values) for values in collect_shell_image_checks(context))
    if any(check.status == "fail" for check in checks):
        return DoctorReport(checks)

    wanted_paths = [
        expand_home(entry, context.home)
        for entry in entries
        if Path(expand_home(entry, context.home)).is_dir()
    ]
    for shell in SHELLS:
        checks.append(_check_startup(context, shell))
        checks.append(_check_editor(context, config, shell, ssh=False))
        checks.append(_check_editor(context, config, shell, ssh=True))

        actual_paths = _path_values(context, shell)
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

    _check_shared_environment(context, config, secrets, checks)
    for command in config.required_commands:
        for shell in SHELLS:
            checks.append(_check_required_command(context, shell, command))
    return DoctorReport(checks)
