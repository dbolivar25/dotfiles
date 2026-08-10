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

from .core import Context, DotfilesError, Plan, validate_environment_key
from .doctor import run_doctor
from .shell_image import (
    activate_shell_image,
    apply_shell_image,
    check_shell_image,
    load_private_secrets,
    load_shell_config,
    rollback_shell_image,
    selected_shell_releases,
    stage_shell_image,
    write_private_shell_config,
)


def _print(value: str) -> None:
    if value:
        print(value)


def _apply_message(plan: Plan, applied: bool, as_json: bool) -> None:
    _print(plan.render(as_json=as_json, applied=applied))
    if plan.actions and not applied and not as_json:
        print("Dry run only. Re-run with --apply to make these changes.")


def _refresh_active_shell_image(context: Context, changed: bool) -> None:
    if changed and context.active_shell_dir.is_symlink():
        apply_shell_image(context)


def _secret_list(context: Context, as_json: bool) -> int:
    keys = sorted(load_private_secrets(context))
    _print(json.dumps(keys, indent=2) if as_json else "\n".join(keys))
    return 0


def _backup_private_source(context: Context) -> Path | None:
    source = context.private_shell_manifest
    if not source.is_file():
        return None
    backup_directory = context.home / ".Trash" / "dotfiles-secrets"
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_directory.chmod(0o700)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_directory / f"shell.local.toml.{timestamp}"
    shutil.copy2(source, backup)
    backup.chmod(0o600)
    return backup


def _secret_set(
    context: Context,
    key: str,
    apply: bool,
    from_stdin: bool,
    as_json: bool,
) -> int:
    validate_environment_key(key)
    secrets = load_private_secrets(context)
    source_exists = context.private_shell_manifest.is_file()
    plan = Plan(f"Set local secret {key}")
    if source_exists:
        plan.add(
            "backup-private",
            context.home / ".Trash" / "dotfiles-secrets",
            "preserve the complete current private manifest",
        )
    plan.add(
        "write-private",
        context.private_shell_manifest,
        "value will not be displayed",
    )
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
        if source_exists:
            _backup_private_source(context)
        secrets[key] = value
        write_private_shell_config(context, secrets)
        _refresh_active_shell_image(context, changed=True)
    _apply_message(plan, apply, as_json)
    return 0


def _secret_unset(context: Context, key: str, apply: bool, as_json: bool) -> int:
    validate_environment_key(key)
    secrets = load_private_secrets(context)
    plan = Plan(f"Unset local secret {key}")
    if key in secrets:
        plan.add(
            "backup-private",
            context.home / ".Trash" / "dotfiles-secrets",
            "preserve the complete current private manifest",
        )
        plan.add("write-private", context.private_shell_manifest, f"remove {key}")
        if apply:
            _backup_private_source(context)
            del secrets[key]
            write_private_shell_config(context, secrets)
            _refresh_active_shell_image(context, changed=True)
    _apply_message(plan, apply, as_json)
    return 0


def _stow(context: Context, apply: bool, as_json: bool) -> int:
    image = stage_shell_image(context) if apply else None
    if not apply:
        check_shell_image(context)
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
        result = subprocess.run(
            ["stow", "--restow", f"--target={context.home}", "."],
            cwd=context.repo,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode
        if image is None:  # pragma: no cover - narrows the apply branch for typing
            raise DotfilesError("shell image was not staged")
        removed_activations, removed_private_releases = activate_shell_image(
            context, image
        )
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
    integrations = sorted(
        {recipe.integration for recipe in load_shell_config(context).generators}
    )
    releases = selected_shell_releases(context)
    shell_image = {"active": releases[0], "rollback": releases[1]} if releases else None
    if as_json:
        print(
            json.dumps(
                {
                    "repo": str(context.repo),
                    "git": result.stdout.splitlines(),
                    "integrations": integrations,
                    "shell_image": shell_image,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"Repository: {context.repo}")
        print(result.stdout.rstrip())
        print(f"Integrations: {len(integrations)} ({', '.join(integrations)})")
        if releases:
            print(
                f"Shell image: {releases[0]}"
                + (f" (rollback {releases[1]})" if releases[1] else "")
            )
        else:
            print("Shell image: not applied")
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
    commands.add_parser("status", help="show repository and shell-image status")

    shell = commands.add_parser(
        "shell", help="validate or activate compiled shell startup files"
    ).add_subparsers(dest="shell_command", required=True)
    shell.add_parser("check", help="compile and validate without changing state")
    shell.add_parser("apply", help="compile and atomically activate source changes")
    shell.add_parser("rollback", help="atomically reactivate the previous release")

    secret = commands.add_parser(
        "secret", help="manage private machine-local shell values"
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
    if arguments.command == "secret":
        if arguments.secret_command == "list":
            return _secret_list(context, arguments.json)
        if arguments.secret_command == "set":
            return _secret_set(
                context, arguments.key, arguments.apply, arguments.stdin, arguments.json
            )
        return _secret_unset(context, arguments.key, arguments.apply, arguments.json)
    if arguments.command == "shell":
        if arguments.shell_command == "check":
            plan = check_shell_image(context)
            if arguments.json:
                print(json.dumps({"ok": True, "summary": plan.summary}, indent=2))
            else:
                print(plan.summary)
            return 0
        elif arguments.shell_command == "apply":
            plan = apply_shell_image(context)
        else:
            plan = rollback_shell_image(context)
        _apply_message(
            plan, applied=arguments.shell_command != "check", as_json=arguments.json
        )
        return 0
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
