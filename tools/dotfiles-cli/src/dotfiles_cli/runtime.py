from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import tomllib

from .core import (
    SHELLS,
    Context,
    DotfilesError,
    Plan,
    adapter_command,
    atomic_write,
    clean_shell_environment,
    expand_home,
)

RUNTIME_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
COMMAND_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._-]*$")
PHASES = {"shadow", "retained"}


@dataclass(frozen=True)
class Owner:
    name: str
    path_prefixes: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeDeclaration:
    name: str
    commands: tuple[str, ...]
    owner: str
    phase: str
    global_version: str | None
    idiomatic_version_file: bool
    legacy_owners: tuple[str, ...]
    gates: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeOwnership:
    version: int
    mode: str
    shells: tuple[str, ...]
    owners: dict[str, Owner]
    runtimes: tuple[RuntimeDeclaration, ...]


@dataclass(frozen=True)
class Resolution:
    path: str | None
    owner: str | None


@dataclass(frozen=True)
class CommandReport:
    command: str
    shells: dict[str, Resolution]
    cross_shell_disagreement: bool


@dataclass(frozen=True)
class RuntimeReport:
    name: str
    phase: str
    owner: str
    status: str
    commands: tuple[CommandReport, ...]
    cross_shell_disagreement: bool
    unknown_ownership: bool
    unexpected_owners: tuple[str, ...]
    legacy_shadowing: bool
    unresolved_gates: tuple[str, ...]


@dataclass(frozen=True)
class OwnershipReport:
    schema_version: int
    mode: str
    consolidated: bool
    ok: bool
    warnings: tuple[str, ...]
    runtimes: tuple[RuntimeReport, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render(self, as_json: bool = False) -> str:
        if as_json:
            return json.dumps(self.as_dict(), indent=2, sort_keys=True)
        lines = [
            "Runtime ownership: shadow validation (no activation changes)",
            "This report is observational; ownership is not yet consolidated.",
        ]
        for runtime in self.runtimes:
            flags = []
            if runtime.cross_shell_disagreement:
                flags.append("shell disagreement")
            if runtime.unknown_ownership:
                flags.append("unknown ownership")
            if runtime.unexpected_owners:
                flags.append("unexpected owner")
            if runtime.legacy_shadowing:
                flags.append("legacy shadowing")
            suffix = f" — {', '.join(flags)}" if flags else ""
            lines.append(
                f"{runtime.name}: {runtime.status} (target {runtime.owner}){suffix}"
            )
            for command in runtime.commands:
                observed = ", ".join(
                    f"{shell}={resolution.path or '<missing>'}"
                    f" [{resolution.owner or 'unknown'}]"
                    for shell, resolution in command.shells.items()
                )
                lines.append(f"  {command.command}: {observed}")
            if runtime.unresolved_gates:
                lines.append(f"  gates: {len(runtime.unresolved_gates)} unresolved")
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
            lines.extend(f"- {warning}" for warning in self.warnings)
        return "\n".join(lines)


def _strings(
    value: object, field: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise DotfilesError(f"runtime ownership {field} must be a list of strings")
    if not allow_empty and not value:
        raise DotfilesError(f"runtime ownership {field} cannot be empty")
    return tuple(value)


def load_runtime_ownership(path: Path) -> RuntimeOwnership:
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError as error:
        raise DotfilesError(f"runtime ownership file is missing: {path}") from error
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise DotfilesError(f"invalid runtime ownership file: {error}") from error

    if data.get("version") != 1:
        raise DotfilesError("runtime ownership version must be 1")
    if data.get("mode") != "shadow-validation":
        raise DotfilesError("runtime ownership mode must be shadow-validation")
    shells = _strings(data.get("shells"), "shells")
    if shells != SHELLS:
        raise DotfilesError("runtime ownership shells must be fish, zsh, and nu")

    raw_owners = data.get("owners")
    if not isinstance(raw_owners, dict) or not raw_owners:
        raise DotfilesError("runtime ownership owners must be a non-empty table")
    owners: dict[str, Owner] = {}
    for name, raw_owner in raw_owners.items():
        if not RUNTIME_NAME.fullmatch(name) or not isinstance(raw_owner, dict):
            raise DotfilesError(f"invalid runtime owner declaration: {name}")
        prefixes = _strings(raw_owner.get("path_prefixes"), f"owner {name} paths")
        if any(
            not prefix.startswith(("/", "${HOME}/")) or ".." in Path(prefix).parts
            for prefix in prefixes
        ):
            raise DotfilesError(f"owner {name} has a non-portable path prefix")
        owners[name] = Owner(name, prefixes)

    raw_runtimes = data.get("runtimes")
    if not isinstance(raw_runtimes, list) or not raw_runtimes:
        raise DotfilesError("runtime ownership runtimes must be a non-empty array")
    runtimes: list[RuntimeDeclaration] = []
    seen: set[str] = set()
    for raw_runtime in raw_runtimes:
        if not isinstance(raw_runtime, dict):
            raise DotfilesError("invalid runtime declaration")
        name = raw_runtime.get("name")
        owner = raw_runtime.get("owner")
        phase = raw_runtime.get("phase")
        if not isinstance(name, str) or not RUNTIME_NAME.fullmatch(name):
            raise DotfilesError("runtime name is invalid")
        if name in seen:
            raise DotfilesError(f"duplicate runtime declaration: {name}")
        seen.add(name)
        if not isinstance(owner, str) or owner not in owners:
            raise DotfilesError(f"runtime {name} references unknown owner: {owner}")
        if phase not in PHASES:
            raise DotfilesError(f"runtime {name} has invalid phase: {phase}")
        global_version = raw_runtime.get("global_version")
        if global_version is not None and (
            not isinstance(global_version, str)
            or not global_version.strip()
            or any(character in global_version for character in "\r\n\0")
        ):
            raise DotfilesError(f"runtime {name} has an invalid global version")
        idiomatic_version_file = raw_runtime.get("idiomatic_version_file", False)
        if not isinstance(idiomatic_version_file, bool):
            raise DotfilesError(
                f"runtime {name} idiomatic version-file flag must be boolean"
            )
        if (global_version is not None or idiomatic_version_file) and owner != "mise":
            raise DotfilesError(
                f"runtime {name} cannot configure mise when its owner is {owner}"
            )
        commands = _strings(raw_runtime.get("commands"), f"runtime {name} commands")
        if any(not COMMAND_NAME.fullmatch(command) for command in commands):
            raise DotfilesError(f"runtime {name} has an invalid command")
        legacy = _strings(
            raw_runtime.get("legacy_owners", []),
            f"runtime {name} legacy owners",
            allow_empty=True,
        )
        unknown = sorted(set(legacy) - owners.keys())
        if unknown:
            raise DotfilesError(
                f"runtime {name} references unknown legacy owners: {', '.join(unknown)}"
            )
        gates = _strings(
            raw_runtime.get("gates"),
            f"runtime {name} gates",
            allow_empty=phase == "retained",
        )
        runtimes.append(
            RuntimeDeclaration(
                name,
                commands,
                owner,
                phase,
                global_version,
                idiomatic_version_file,
                legacy,
                gates,
            )
        )

    return RuntimeOwnership(1, "shadow-validation", shells, owners, tuple(runtimes))


def _render_mise_config(ownership: RuntimeOwnership) -> str:
    versions = sorted(
        (runtime.name, runtime.global_version)
        for runtime in ownership.runtimes
        if runtime.global_version is not None
    )
    idiomatic_tools = sorted(
        runtime.name for runtime in ownership.runtimes if runtime.idiomatic_version_file
    )
    lines = ["# Managed by the dotfiles runtime ownership policy."]
    if versions:
        lines.extend(
            [
                "[tools]",
                *(f"{name} = {json.dumps(version)}" for name, version in versions),
            ]
        )
    if idiomatic_tools:
        rendered_tools = ", ".join(json.dumps(name) for name in idiomatic_tools)
        if versions:
            lines.append("")
        lines.extend(
            [
                "[settings]",
                f"idiomatic_version_file_enable_tools = [{rendered_tools}]",
            ]
        )
    return "\n".join(lines) + "\n"


def configure_runtime(context: Context, *, apply: bool = False) -> Plan:
    ownership = load_runtime_ownership(context.runtime_ownership_file)
    content = _render_mise_config(ownership)
    target = context.mise_config_file
    plan = Plan("Configure approved mise runtime policy")
    if not target.is_file() or target.read_text() != content:
        plan.add("write", target, "render approved runtime declarations")
        if apply:
            atomic_write(target, content, mode=0o644)
    return plan


def _probe_shell(
    context: Context, shell: str, commands: tuple[str, ...]
) -> dict[str, str | None]:
    if shell == "nu":
        names = " ".join(json.dumps(command) for command in commands)
        body = (
            f"[{names}] | each {{|name| {{name: $name, path: "
            '((which $name | get -i 0.path | default ""))}} | to json --raw'
        )
    elif shell == "fish":
        names = " ".join(commands)
        body = (
            f"for name in {names}; set -l resolved (command -s -- $name 2>/dev/null); "
            'printf \'%s\\t%s\\n\' "$name" "$resolved"; end'
        )
    else:
        names = " ".join(commands)
        body = (
            f"for name in {names}; do resolved=$(whence -p -- $name 2>/dev/null); "
            'printf \'%s\\t%s\\n\' "$name" "$resolved"; done'
        )
    try:
        result = subprocess.run(
            adapter_command(context, shell, body),
            cwd=context.repo,
            env=clean_shell_environment(context),
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {command: None for command in commands}
    if result.returncode != 0:
        return {command: None for command in commands}
    try:
        output = result.stdout.decode()
        if shell == "nu":
            values = json.loads(output)
            found = {item["name"]: item["path"] or None for item in values}
        else:
            found = dict(line.split("\t", 1) for line in output.splitlines())
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError, TypeError):
        return {command: None for command in commands}
    return {command: found.get(command) or None for command in commands}


def _classify_path(
    path: str | None, ownership: RuntimeOwnership, home: Path
) -> str | None:
    if path is None:
        return None
    candidates = (path, str(Path(path).resolve(strict=False)))
    matches = [
        (len(expanded), owner.name)
        for owner in ownership.owners.values()
        for prefix in owner.path_prefixes
        if any(
            candidate.startswith(expanded := expand_home(prefix, home))
            for candidate in candidates
        )
    ]
    return max(matches, default=(0, None))[1]


def collect_runtime_report(context: Context) -> OwnershipReport:
    ownership = load_runtime_ownership(context.runtime_ownership_file)
    commands = tuple(
        dict.fromkeys(
            command for runtime in ownership.runtimes for command in runtime.commands
        )
    )
    observed = {
        shell: _probe_shell(context, shell, commands) for shell in ownership.shells
    }
    reports: list[RuntimeReport] = []
    warnings: list[str] = []
    for runtime in ownership.runtimes:
        command_reports: list[CommandReport] = []
        runtime_owners: set[str] = set()
        missing = False
        disagreement = False
        for command in runtime.commands:
            resolutions = {
                shell: Resolution(
                    observed[shell][command],
                    _classify_path(observed[shell][command], ownership, context.home),
                )
                for shell in ownership.shells
            }
            paths = {
                resolution.path
                for resolution in resolutions.values()
                if resolution.path is not None
            }
            command_disagreement = len(paths) > 1
            disagreement = disagreement or command_disagreement
            missing = missing or any(
                resolution.path is None for resolution in resolutions.values()
            )
            runtime_owners.update(
                resolution.owner
                for resolution in resolutions.values()
                if resolution.owner is not None
            )
            command_reports.append(
                CommandReport(command, resolutions, command_disagreement)
            )
        legacy_shadowing = bool(runtime_owners.intersection(runtime.legacy_owners))
        unknown_ownership = any(
            resolution.path is not None and resolution.owner is None
            for command_report in command_reports
            for resolution in command_report.shells.values()
        )
        unexpected_owners = tuple(sorted(runtime_owners - {runtime.owner}))
        all_candidate = (
            not missing
            and not disagreement
            and not unknown_ownership
            and runtime_owners == {runtime.owner}
        )
        status = (
            "retained"
            if runtime.phase == "retained"
            else "provisional"
            if all_candidate
            else "shadow"
        )
        if disagreement:
            warnings.append(f"{runtime.name}: shells resolve different paths")
        if missing:
            warnings.append(f"{runtime.name}: at least one command is unresolved")
        if unknown_ownership:
            warnings.append(f"{runtime.name}: resolved path ownership is unknown")
        if unexpected_owners:
            warnings.append(
                f"{runtime.name}: observed owner differs from target: "
                f"{', '.join(unexpected_owners)}"
            )
        if legacy_shadowing:
            warnings.append(f"{runtime.name}: a legacy owner still shadows the target")
        reports.append(
            RuntimeReport(
                runtime.name,
                runtime.phase,
                runtime.owner,
                status,
                tuple(command_reports),
                disagreement,
                unknown_ownership,
                unexpected_owners,
                legacy_shadowing,
                runtime.gates,
            )
        )
    return OwnershipReport(
        ownership.version,
        ownership.mode,
        False,
        True,
        tuple(warnings),
        tuple(reports),
    )
