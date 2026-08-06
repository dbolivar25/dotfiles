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


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        (self.repo / ".git").mkdir()
        shell_root = self.repo / ".config" / "shell"
        (shell_root / "adapters").mkdir(parents=True)
        (shell_root / "environment.d").mkdir()
        (shell_root / "integrations").mkdir()
        (shell_root / "adapters" / "nu.nu").write_text("# Nushell adapter\n")
        (shell_root / "paths").write_text("# Managed paths\n${HOME}/.local/bin\n")

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


if __name__ == "__main__":
    unittest.main()
