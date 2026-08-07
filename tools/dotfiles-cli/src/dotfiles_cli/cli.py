from __future__ import annotations

import argparse
import getpass
import json
import shlex
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from .core import (
    SHELL_ADAPTERS,
    SHELLS,
    Context,
    DotfilesError,
    Plan,
    atomic_write,
    integration_coverage,
    normalize_path_entry,
    read_data_lines,
    remove_path,
    source_line_for_nu,
    update_data_lines,
    validate_environment_key,
    validate_integration_name,
)
from .doctor import run_doctor
from .runtime import collect_runtime_report, configure_runtime


def _print(value: str) -> None:
    if value:
        print(value)


def _apply_message(plan: Plan, apply: bool, as_json: bool) -> None:
    _print(plan.render(as_json=as_json, applied=apply))
    if plan.actions and not apply and not as_json:
        print("Dry run only. Re-run with --apply to make these changes.")


def _path_list(context: Context, as_json: bool) -> int:
    entries = read_data_lines(context.paths_file)
    _print(json.dumps(entries, indent=2) if as_json else "\n".join(entries))
    return 0


def _path_add(
    context: Context, value: str, append: bool, apply: bool, as_json: bool
) -> int:
    normalized = normalize_path_entry(value, context.home)
    entries = read_data_lines(context.paths_file)
    plan = Plan("Add managed PATH entry")
    if normalized not in entries:
        updated = entries + [normalized] if append else [normalized] + entries
        plan.add("write", context.paths_file, f"add {normalized}")
        if apply:
            atomic_write(
                context.paths_file, update_data_lines(context.paths_file, updated)
            )
    _apply_message(plan, apply, as_json)
    return 0


def _path_remove(context: Context, value: str, apply: bool, as_json: bool) -> int:
    normalized = normalize_path_entry(value, context.home)
    entries = read_data_lines(context.paths_file)
    plan = Plan("Remove managed PATH entry")
    if normalized in entries:
        plan.add("write", context.paths_file, f"remove {normalized}")
        if apply:
            atomic_write(
                context.paths_file,
                update_data_lines(
                    context.paths_file,
                    [entry for entry in entries if entry != normalized],
                ),
            )
    _apply_message(plan, apply, as_json)
    return 0


def _value_list(directory: Path, as_json: bool) -> int:
    keys = sorted(path.name for path in directory.glob("*") if path.is_file())
    _print(json.dumps(keys, indent=2) if as_json else "\n".join(keys))
    return 0


def _env_set(context: Context, key: str, value: str, apply: bool, as_json: bool) -> int:
    validate_environment_key(key)
    target = context.environment_dir / key
    wanted = value.replace(str(context.home), "${HOME}")
    content = f"{wanted}\n"
    plan = Plan(f"Set public environment variable {key}")
    if not target.exists() or target.read_text() != content:
        plan.add("write", target, "update public value")
        if apply:
            atomic_write(target, content)
    _apply_message(plan, apply, as_json)
    return 0


def _env_unset(context: Context, key: str, apply: bool, as_json: bool) -> int:
    validate_environment_key(key)
    target = context.environment_dir / key
    plan = Plan(f"Unset public environment variable {key}")
    if target.exists():
        plan.add("delete", target)
        if apply:
            remove_path(target)
    _apply_message(plan, apply, as_json)
    return 0


def _secret_set(
    context: Context,
    key: str,
    apply: bool,
    from_stdin: bool,
    as_json: bool,
) -> int:
    validate_environment_key(key)
    target = context.secrets_dir / key
    plan = Plan(f"Set local secret {key}")
    if target.exists():
        plan.add(
            "backup-private",
            context.home / ".Trash" / "dotfiles-secrets",
            "preserve current value",
        )
    plan.add("write-private", target, "value will not be displayed")
    if apply:
        if from_stdin:
            value = sys.stdin.read().removesuffix("\n")
        elif not sys.stdin.isatty():
            raise DotfilesError(
                "refusing implicit stdin; pass --stdin or use an interactive terminal"
            )
        else:
            value = getpass.getpass(f"{key}: ")
        if not value:
            raise DotfilesError("secret value cannot be empty")
        if target.exists():
            _backup_secret(context, target, move=False)
        atomic_write(target, f"{value}\n", mode=0o600)
    _apply_message(plan, apply, as_json)
    return 0


def _secret_unset(context: Context, key: str, apply: bool, as_json: bool) -> int:
    validate_environment_key(key)
    target = context.secrets_dir / key
    plan = Plan(f"Unset local secret {key}")
    if target.exists():
        plan.add("move-private", target, "preserve in ~/.Trash/dotfiles-secrets")
        if apply:
            _backup_secret(context, target, move=True)
    _apply_message(plan, apply, as_json)
    return 0


def _backup_secret(context: Context, target: Path, *, move: bool) -> Path:
    backup_directory = context.home / ".Trash" / "dotfiles-secrets"
    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_directory / f"{target.name}.{timestamp}"
    if move:
        target.replace(backup)
    else:
        shutil.copy2(target, backup)
    backup.chmod(0o600)
    return backup


def _integration_list(context: Context, as_json: bool) -> int:
    integrations = {
        directory.name: integration_coverage(directory)
        for directory in sorted(context.integrations_dir.glob("*"))
        if directory.is_dir()
    }
    if as_json:
        _print(json.dumps(integrations, indent=2, sort_keys=True))
    else:
        for name, coverage in integrations.items():
            states = " ".join(f"{shell}={coverage[shell]}" for shell in SHELLS)
            print(f"{name}: {states}")
    return 0


def _integration_template(name: str, shell: str) -> str:
    return f"# Configure {name} for {shell} here.\n"


def _integration_init(
    context: Context,
    name: str,
    shells: list[str],
    apply: bool,
    as_json: bool,
) -> int:
    validate_integration_name(name)
    directory = context.integrations_dir / name
    if directory.exists():
        raise DotfilesError(f"integration already exists: {name}")
    requested = set(shells or SHELLS)
    plan = Plan(f"Initialize integration {name}")
    for shell in SHELLS:
        if shell in requested:
            target = directory / SHELL_ADAPTERS[shell]
            plan.add("write", target, f"scaffold {shell} adapter")
            if apply:
                atomic_write(target, _integration_template(name, shell))
        else:
            target = directory / f"{shell}.deferred"
            plan.add("write", target, f"mark {shell} deferred")
            if apply:
                atomic_write(
                    target, "Not requested when this integration was initialized.\n"
                )
    if "nu" in requested:
        source_line = source_line_for_nu(name)
        adapter_text = context.nu_adapter.read_text()
        if source_line not in adapter_text:
            plan.add("write", context.nu_adapter, "register Nushell adapter")
            if apply:
                atomic_write(
                    context.nu_adapter, f"{adapter_text.rstrip()}\n{source_line}\n"
                )
    _apply_message(plan, apply, as_json)
    return 0


def _integration_remove(context: Context, name: str, apply: bool, as_json: bool) -> int:
    validate_integration_name(name)
    directory = context.integrations_dir / name
    plan = Plan(f"Remove integration {name}")
    if directory.exists():
        plan.add("delete", directory)
        if apply:
            remove_path(directory)
    source_line = source_line_for_nu(name)
    adapter_text = context.nu_adapter.read_text()
    updated = (
        "\n".join(line for line in adapter_text.splitlines() if line != source_line)
        + "\n"
    )
    if updated != adapter_text:
        plan.add("write", context.nu_adapter, "unregister Nushell adapter")
        if apply:
            atomic_write(context.nu_adapter, updated)
    _apply_message(plan, apply, as_json)
    return 0


def _stow(context: Context, apply: bool, as_json: bool) -> int:
    simulation = subprocess.run(
        [
            "stow",
            "--simulate",
            "--verbose=1",
            "--restow",
            f"--target={context.home}",
            ".",
        ],
        cwd=context.repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if simulation.returncode != 0:
        if as_json:
            print(json.dumps({"ok": False, "simulation": simulation.stdout}, indent=2))
        else:
            print(simulation.stdout, end="")
        return simulation.returncode
    plan = Plan("Reconcile Stow links")
    plan.add("run", detail=f"stow --restow --target={context.home} .")
    if apply:
        applied = subprocess.run(
            ["stow", "--restow", f"--target={context.home}", "."],
            cwd=context.repo,
            check=False,
        )
        if applied.returncode != 0:
            return applied.returncode
    if as_json:
        print(
            json.dumps(
                {
                    "summary": plan.summary,
                    "changes": True,
                    "simulation": simulation.stdout.splitlines(),
                    "actions": [action.__dict__ for action in plan.actions],
                    "applied": apply,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(simulation.stdout.rstrip())
        _apply_message(plan, apply, as_json=False)
    return 0


def _status(context: Context, as_json: bool) -> int:
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=context.repo,
        text=True,
        stdout=subprocess.PIPE,
        check=False,
    )
    integrations = [
        path.name for path in context.integrations_dir.glob("*") if path.is_dir()
    ]
    if as_json:
        print(
            json.dumps(
                {
                    "repo": str(context.repo),
                    "git": result.stdout.splitlines(),
                    "integrations": sorted(integrations),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"Repository: {context.repo}")
        print(result.stdout.rstrip())
        print(f"Integrations: {len(integrations)}")
    return result.returncode


def _capture(context: Context, command: list[str], apply: bool, as_json: bool) -> int:
    command = command[1:] if command and command[0] == "--" else command
    if not command:
        raise DotfilesError("capture requires a command after --")
    rendered = shlex.join(command)
    plan = Plan("Capture installer shell changes")
    plan.add("run", detail=rendered)
    plan.add("inspect", context.repo, "report resulting Git changes")
    plan.add("run", detail="dotfiles doctor")
    if not apply:
        _apply_message(plan, apply, as_json)
        return 0
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=context.repo,
        text=True,
        stdout=subprocess.PIPE,
        check=False,
    )
    if dirty.stdout.strip():
        raise DotfilesError("capture requires a clean dotfiles working tree")
    result = subprocess.run(command, cwd=context.invocation_dir, check=False)
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=context.repo,
        text=True,
        stdout=subprocess.PIPE,
        check=False,
    )
    report = run_doctor(context)
    if as_json:
        print(
            json.dumps(
                {
                    "command": rendered,
                    "exit_code": result.returncode,
                    "changes": status.stdout.splitlines(),
                    "doctor_ok": not report.failed,
                },
                indent=2,
            )
        )
    else:
        print(f"Command exited {result.returncode}: {rendered}")
        print(status.stdout.rstrip() or "No tracked dotfiles changes detected.")
        print(report.render())
    return result.returncode or (1 if report.failed else 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dotfiles")
    parser.add_argument("--repo", help="dotfiles repository; defaults to ~/dotfiles")
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="validate cross-shell behavior")
    commands.add_parser("status", help="show repository and integration status")
    runtime = commands.add_parser(
        "runtime", help="inspect and configure shadow runtime ownership"
    ).add_subparsers(dest="runtime_command", required=True)
    runtime.add_parser("status", help="resolve runtime paths without running runtimes")
    runtime_configure = runtime.add_parser(
        "configure", help="render approved mise configuration"
    )
    runtime_configure.add_argument("--apply", action="store_true")

    path = commands.add_parser(
        "path", help="manage shared PATH entries"
    ).add_subparsers(dest="path_command", required=True)
    path.add_parser("list")
    path_add = path.add_parser("add")
    path_add.add_argument("value")
    path_add.add_argument("--append", action="store_true")
    path_add.add_argument("--apply", action="store_true")
    path_remove = path.add_parser("remove")
    path_remove.add_argument("value")
    path_remove.add_argument("--apply", action="store_true")

    env = commands.add_parser(
        "env", help="manage public environment values"
    ).add_subparsers(dest="env_command", required=True)
    env.add_parser("list")
    env_set = env.add_parser("set")
    env_set.add_argument("key")
    env_set.add_argument("value")
    env_set.add_argument("--apply", action="store_true")
    env_unset = env.add_parser("unset")
    env_unset.add_argument("key")
    env_unset.add_argument("--apply", action="store_true")

    secret = commands.add_parser(
        "secret", help="manage private local values"
    ).add_subparsers(dest="secret_command", required=True)
    secret.add_parser("list")
    secret_set = secret.add_parser("set")
    secret_set.add_argument("key")
    secret_set.add_argument(
        "--stdin", action="store_true", help="read the value from stdin"
    )
    secret_set.add_argument("--apply", action="store_true")
    secret_unset = secret.add_parser("unset")
    secret_unset.add_argument("key")
    secret_unset.add_argument("--apply", action="store_true")

    integration = commands.add_parser(
        "integration", help="manage shell integrations"
    ).add_subparsers(dest="integration_command", required=True)
    integration.add_parser("list")
    integration_init = integration.add_parser("init")
    integration_init.add_argument("name")
    integration_init.add_argument("--shell", action="append", choices=SHELLS)
    integration_init.add_argument("--apply", action="store_true")
    integration_remove = integration.add_parser("remove")
    integration_remove.add_argument("name")
    integration_remove.add_argument("--apply", action="store_true")

    stow = commands.add_parser("stow", help="preview or reconcile Stow links")
    stow.add_argument("--apply", action="store_true")

    capture = commands.add_parser(
        "capture", help="run an installer and report shell changes"
    )
    capture.add_argument("--apply", action="store_true")
    capture.add_argument("captured_command", nargs=argparse.REMAINDER)
    return parser


def dispatch(arguments: argparse.Namespace, context: Context) -> int:
    if arguments.command == "doctor":
        report = run_doctor(context)
        _print(report.render(as_json=arguments.json))
        return 1 if report.failed else 0
    if arguments.command == "status":
        return _status(context, arguments.json)
    if arguments.command == "runtime":
        if arguments.runtime_command == "configure":
            plan = configure_runtime(context, apply=arguments.apply)
            _apply_message(plan, arguments.apply, arguments.json)
            return 0
        report = collect_runtime_report(context)
        _print(report.render(as_json=arguments.json))
        return 0
    if arguments.command == "path":
        if arguments.path_command == "list":
            return _path_list(context, arguments.json)
        if arguments.path_command == "add":
            return _path_add(
                context,
                arguments.value,
                arguments.append,
                arguments.apply,
                arguments.json,
            )
        return _path_remove(context, arguments.value, arguments.apply, arguments.json)
    if arguments.command == "env":
        if arguments.env_command == "list":
            return _value_list(context.environment_dir, arguments.json)
        if arguments.env_command == "set":
            return _env_set(
                context, arguments.key, arguments.value, arguments.apply, arguments.json
            )
        return _env_unset(context, arguments.key, arguments.apply, arguments.json)
    if arguments.command == "secret":
        if arguments.secret_command == "list":
            return _value_list(context.secrets_dir, arguments.json)
        if arguments.secret_command == "set":
            return _secret_set(
                context, arguments.key, arguments.apply, arguments.stdin, arguments.json
            )
        return _secret_unset(context, arguments.key, arguments.apply, arguments.json)
    if arguments.command == "integration":
        if arguments.integration_command == "list":
            return _integration_list(context, arguments.json)
        if arguments.integration_command == "init":
            return _integration_init(
                context,
                arguments.name,
                arguments.shell or [],
                arguments.apply,
                arguments.json,
            )
        return _integration_remove(
            context, arguments.name, arguments.apply, arguments.json
        )
    if arguments.command == "stow":
        return _stow(context, arguments.apply, arguments.json)
    if arguments.command == "capture":
        return _capture(
            context, arguments.captured_command, arguments.apply, arguments.json
        )
    raise DotfilesError(f"unknown command: {arguments.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        context = Context.discover(arguments.repo)
        return dispatch(arguments, context)
    except DotfilesError as error:
        if arguments.json:
            print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        else:
            print(f"dotfiles: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
