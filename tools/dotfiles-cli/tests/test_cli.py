from __future__ import annotations

import io
import json
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from dotfiles_cli.cli import main
from dotfiles_cli.core import Context
from dotfiles_cli.doctor import run_doctor
from dotfiles_cli.runtime import collect_runtime_report, load_runtime_ownership


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        (self.repo / ".git").mkdir()
        shell_root = self.repo / ".config" / "shell"
        (shell_root / "adapters").mkdir(parents=True)
        (shell_root / "environment.d").mkdir()
        (shell_root / "integrations").mkdir()
        (shell_root / "behavior" / "editor").mkdir(parents=True)
        (shell_root / "adapters" / "fish.fish").write_text("# Fish adapter\n")
        (shell_root / "adapters" / "zsh.zsh").write_text("# Zsh adapter\n")
        (shell_root / "adapters" / "nu.nu").write_text("# Nushell adapter\n")
        (shell_root / "behavior" / "editor" / "local").write_text("nvim\n")
        (shell_root / "behavior" / "editor" / "ssh").write_text("vim\n")
        (shell_root / "paths").write_text("# Managed paths\n${HOME}/.local/bin\n")
        (shell_root / "required-commands").write_text("")
        source = (
            Path(__file__).parents[3] / ".config" / "shell" / "runtime-ownership.toml"
        )
        (shell_root / "runtime-ownership.toml").write_text(source.read_text())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str, stdin: str | None = None) -> tuple[int, str]:
        output = io.StringIO()
        command = ["--repo", str(self.repo), *arguments]
        stream = io.StringIO(stdin) if stdin is not None else None
        with redirect_stdout(output):
            if stream is None:
                status = main(command)
            else:
                with patch("sys.stdin", stream):
                    status = main(command)
        return status, output.getvalue()

    def test_path_add_is_dry_by_default(self) -> None:
        before = (self.repo / ".config" / "shell" / "paths").read_text()
        status, output = self.run_cli("path", "add", "/opt/example/bin")
        self.assertEqual(status, 0)
        self.assertIn("Dry run only", output)
        self.assertEqual(
            (self.repo / ".config" / "shell" / "paths").read_text(), before
        )

    def test_path_add_requires_apply_to_write(self) -> None:
        status, _ = self.run_cli("path", "add", "/opt/example/bin", "--apply")
        self.assertEqual(status, 0)
        entries = (self.repo / ".config" / "shell" / "paths").read_text().splitlines()
        self.assertEqual(entries[1], "/opt/example/bin")

    def test_environment_set_normalizes_home(self) -> None:
        value = str(Path.home() / "Library" / "example")
        status, _ = self.run_cli("env", "set", "EXAMPLE_HOME", value, "--apply")
        self.assertEqual(status, 0)
        target = self.repo / ".config" / "shell" / "environment.d" / "EXAMPLE_HOME"
        self.assertEqual(target.read_text(), "${HOME}/Library/example\n")

    def test_secret_plan_never_prompts_or_writes(self) -> None:
        status, output = self.run_cli("secret", "set", "EXAMPLE_TOKEN")
        self.assertEqual(status, 0)
        self.assertIn("value will not be displayed", output)
        self.assertFalse((self.repo / ".config" / "shell" / "secrets.d").exists())

    def test_secret_apply_uses_private_mode(self) -> None:
        status, output = self.run_cli(
            "secret",
            "set",
            "EXAMPLE_TOKEN",
            "--stdin",
            "--apply",
            stdin="private-value\n",
        )
        self.assertEqual(status, 0)
        self.assertNotIn("private-value", output)
        target = self.repo / ".config" / "shell" / "secrets.d" / "EXAMPLE_TOKEN"
        self.assertEqual(target.read_text(), "private-value\n")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_integration_init_registers_nushell(self) -> None:
        status, _ = self.run_cli("integration", "init", "example", "--apply")
        self.assertEqual(status, 0)
        integration = self.repo / ".config" / "shell" / "integrations" / "example"
        self.assertTrue((integration / "fish.fish").is_file())
        self.assertTrue((integration / "zsh.zsh").is_file())
        self.assertTrue((integration / "nu.nu").is_file())
        nu_adapter = (
            self.repo / ".config" / "shell" / "adapters" / "nu.nu"
        ).read_text()
        self.assertIn("source ~/.config/shell/integrations/example/nu.nu", nu_adapter)

    def test_integration_remove_unregisters_nushell(self) -> None:
        self.run_cli("integration", "init", "example", "--apply")
        status, _ = self.run_cli("integration", "remove", "example", "--apply")
        self.assertEqual(status, 0)
        self.assertFalse(
            (self.repo / ".config" / "shell" / "integrations" / "example").exists()
        )
        nu_adapter = (
            self.repo / ".config" / "shell" / "adapters" / "nu.nu"
        ).read_text()
        self.assertNotIn("integrations/example", nu_adapter)

    def test_json_plan_is_machine_readable(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(
                ["--repo", str(self.repo), "--json", "env", "set", "EXAMPLE", "value"]
            )
        self.assertEqual(status, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["changes"])
        self.assertEqual(payload["actions"][0]["operation"], "write")

    def test_capture_does_not_execute_without_apply(self) -> None:
        marker = self.repo / "capture-ran"
        status, _ = self.run_cli("capture", "--", "/usr/bin/touch", str(marker))
        self.assertEqual(status, 0)
        self.assertFalse(marker.exists())

    def test_runtime_ownership_parses_required_boundaries(self) -> None:
        ownership = load_runtime_ownership(
            self.repo / ".config" / "shell" / "runtime-ownership.toml"
        )
        declarations = {runtime.name: runtime for runtime in ownership.runtimes}
        self.assertEqual(
            set(declarations),
            {
                "node",
                "ruby",
                "go",
                "java",
                "elixir",
                "erlang",
                "python",
                "rust",
                "ocaml",
                "haskell",
                "bun",
                "dotnet",
            },
        )
        self.assertEqual(declarations["node"].owner, "mise")
        self.assertEqual(declarations["elixir"].phase, "shadow")
        self.assertEqual(declarations["python"].owner, "uv")
        self.assertEqual(declarations["rust"].phase, "retained")

    def test_runtime_status_json_reports_shadow_not_consolidation(self) -> None:
        home = str(Path.home())

        def observed(
            _context: Context, _shell: str, commands: tuple[str, ...]
        ) -> dict[str, str]:
            paths = {}
            for command in commands:
                if command == "node":
                    paths[command] = (
                        f"{home}/.local/share/mise/installs/node/24/bin/node"
                    )
                else:
                    paths[command] = f"/opt/homebrew/bin/{command}"
            return paths

        with patch("dotfiles_cli.runtime._probe_shell", side_effect=observed):
            status, output = self.run_cli("--json", "runtime", "status")
        self.assertEqual(status, 0)
        payload = json.loads(output)
        self.assertEqual(payload["mode"], "shadow-validation")
        self.assertFalse(payload["consolidated"])
        node = next(item for item in payload["runtimes"] if item["name"] == "node")
        self.assertEqual(node["status"], "provisional")
        self.assertFalse(node["legacy_shadowing"])

    def test_runtime_conflicts_are_data_not_command_failures(self) -> None:
        home = str(Path.home())
        observations = {
            "fish": f"{home}/.nvm/versions/node/v24/bin/node",
            "zsh": "/opt/homebrew/bin/node",
            "nu": f"{home}/.local/share/mise/installs/node/24/bin/node",
        }

        def observed(
            _context: Context, shell: str, commands: tuple[str, ...]
        ) -> dict[str, str | None]:
            return {
                command: observations[shell] if command == "node" else None
                for command in commands
            }

        with patch("dotfiles_cli.runtime._probe_shell", side_effect=observed):
            report = collect_runtime_report(Context.discover(str(self.repo)))
        node = next(item for item in report.runtimes if item.name == "node")
        self.assertTrue(report.ok)
        self.assertEqual(node.status, "shadow")
        self.assertTrue(node.cross_shell_disagreement)
        self.assertTrue(node.legacy_shadowing)

    def test_runtime_warns_for_consistent_unknown_and_unexpected_owners(self) -> None:
        context = Context.discover(str(self.repo))
        cases = {
            "unknown": ("/opt/custom/bin/node", "resolved path ownership is unknown"),
            "unexpected": (
                str(Path.home() / ".cargo" / "bin" / "node"),
                "observed owner differs from target: rustup",
            ),
        }
        for label, (node_path, warning) in cases.items():
            with self.subTest(label=label):

                def observed(
                    _context: Context,
                    _shell: str,
                    commands: tuple[str, ...],
                    path: str = node_path,
                ) -> dict[str, str]:
                    return {
                        command: path
                        if command == "node"
                        else f"/opt/custom/bin/{command}"
                        for command in commands
                    }

                with patch("dotfiles_cli.runtime._probe_shell", side_effect=observed):
                    report = collect_runtime_report(context)
                    completed = __import__("subprocess").CompletedProcess(
                        ["check"], returncode=0, stdout=b"", stderr=b""
                    )
                    with patch(
                        "dotfiles_cli.doctor.subprocess.run", return_value=completed
                    ):
                        doctor = run_doctor(context)

                node = next(item for item in report.runtimes if item.name == "node")
                self.assertTrue(report.ok)
                self.assertFalse(node.cross_shell_disagreement)
                self.assertFalse(node.legacy_shadowing)
                self.assertTrue(any(warning in item for item in report.warnings))
                visibility = next(
                    check
                    for check in doctor.checks
                    if check.name == "runtime shadow visibility"
                )
                self.assertEqual(visibility.status, "warn")

    def test_runtime_probe_never_executes_inspected_commands(self) -> None:
        completed = __import__("subprocess").CompletedProcess(
            ["shell"], returncode=1, stdout=b"", stderr=b""
        )
        with patch(
            "dotfiles_cli.runtime.subprocess.run", return_value=completed
        ) as run:
            collect_runtime_report(Context.discover(str(self.repo)))
        executables = [invocation.args[0][0] for invocation in run.call_args_list]
        self.assertEqual(executables, ["fish", "zsh", "nu"])
        inspected = {
            "node",
            "ruby",
            "go",
            "java",
            "elixir",
            "erl",
            "python",
            "rustc",
        }
        self.assertFalse(inspected.intersection(executables))

    def test_runtime_status_is_read_only(self) -> None:
        target = self.repo / ".config" / "shell" / "runtime-ownership.toml"
        before = target.read_bytes()
        with patch(
            "dotfiles_cli.runtime._probe_shell",
            return_value={
                command: None
                for runtime in load_runtime_ownership(target).runtimes
                for command in runtime.commands
            },
        ):
            status, _ = self.run_cli("runtime", "status")
        self.assertEqual(status, 0)
        self.assertEqual(target.read_bytes(), before)

    def test_malformed_runtime_ownership_is_rejected(self) -> None:
        target = self.repo / ".config" / "shell" / "runtime-ownership.toml"
        target.write_text('version = 1\nmode = "shadow-validation"\nshells = [')
        status, output = self.run_cli("--json", "runtime", "status")
        self.assertEqual(status, 2)
        self.assertIn("invalid runtime ownership file", json.loads(output)["error"])

    def test_doctor_fails_when_runtime_ownership_is_missing(self) -> None:
        target = self.repo / ".config" / "shell" / "runtime-ownership.toml"
        target.unlink()
        report = run_doctor(Context.discover(str(self.repo)))
        shell_module = next(
            check for check in report.checks if check.name == "shell module"
        )
        self.assertEqual(shell_module.status, "fail")
        self.assertIn("runtime-ownership.toml", shell_module.detail)


if __name__ == "__main__":
    unittest.main()
