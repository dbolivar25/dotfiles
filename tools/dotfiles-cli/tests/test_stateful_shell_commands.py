from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[3]
NATIVE = REPO / ".config" / "shell" / "native"
POSIX_SHELLS = ("bash", "zsh")


class StatefulShellCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def executable(self, name: str, body: str) -> Path:
        target = self.bin / name
        target.write_text(f"#!/bin/sh\n{body}\n")
        target.chmod(0o755)
        return target

    def environment(self, **values: str) -> dict[str, str]:
        environment = os.environ.copy()
        environment.pop("VIRTUAL_ENV", None)
        environment.update(values)
        environment["HOME"] = str(self.root)
        environment["PATH"] = f"{self.bin}:{environment['PATH']}"
        return environment

    def run_shell(
        self,
        shell: str,
        body: str,
        **environment: str,
    ) -> subprocess.CompletedProcess[str]:
        commands = {
            "bash": ["/bin/bash", "--noprofile", "--norc", "-c", body],
            "zsh": ["zsh", "-dfc", body],
            "nu": ["nu", "--no-config-file", "-c", body],
        }
        return subprocess.run(
            commands[shell],
            cwd=self.root,
            env=self.environment(**environment),
            text=True,
            capture_output=True,
            check=False,
        )

    def source(self, shell: str) -> str:
        if shell == "nu":
            adapter = NATIVE / "nu" / "commands.nu"
        else:
            adapter = NATIVE / "sh" / "functions.sh"
        command = "source"
        if shell == "bash":
            command = "."
        return f"{command} {shlex.quote(str(adapter))}"

    def test_venv_lifecycle_keeps_activation_in_the_calling_shell(self) -> None:
        self.executable(
            "python3",
            'test "$1 $2" = "-m venv" || exit 2\nmkdir -p "$3/bin"',
        )
        for shell in POSIX_SHELLS:
            source = self.source(shell)
            created = self.run_shell(
                shell,
                f"{source}; venv new; test -d .venv; venv remove; test ! -e .venv",
            )
            with self.subTest(shell=shell, case="new and remove"):
                self.assertEqual(created.returncode, 0, created.stderr)

            activate = self.root / ".venv" / "bin" / "activate"
            activate.parent.mkdir(parents=True)
            activate.write_text(
                f"export VIRTUAL_ENV={shlex.quote(str(self.root / '.venv'))}\n"
                "deactivate() { unset VIRTUAL_ENV; }\n"
            )
            active = self.run_shell(
                shell,
                f'{source}; venv activate; printf "%s\\n" "$VIRTUAL_ENV"; venv deactivate; printf "%s\\n" "${{VIRTUAL_ENV-unset}}"',
            )
            with self.subTest(shell=shell, case="activate and deactivate"):
                self.assertEqual(active.returncode, 0, active.stderr)
                self.assertEqual(
                    active.stdout.splitlines(),
                    [str(self.root / ".venv"), "unset"],
                )
            activate.unlink()
            activate.parent.rmdir()
            activate.parent.parent.rmdir()

    def test_nushell_venv_preserves_native_overlay_exports(self) -> None:
        source = self.source("nu")
        bin_dir = self.root / ".venv" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "activate.nu").write_text(
            "export-env {\n"
            f"    $env.VIRTUAL_ENV = '{self.root / '.venv'}'\n"
            "    $env.VIRTUAL_ENV_PROMPT = '(native) '\n"
            "}\n"
            "export alias pydoc = python -m pydoc\n"
        )

        active = self.run_shell(
            "nu",
            f'{source}; venv; print $"($env.VIRTUAL_ENV)|($env.VIRTUAL_ENV_PROMPT)"; scope aliases | where name == pydoc | get name.0',
        )
        self.assertEqual(active.returncode, 0, active.stderr)
        self.assertEqual(
            active.stdout.splitlines(), [f"{self.root / '.venv'}|(native) ", "pydoc"]
        )

    def test_load_env_preserves_literal_values_in_the_calling_shell(self) -> None:
        dotenv = self.root / ".env"
        dotenv.write_text(
            "# comment\n   # indented comment\n\nFIRST=one=two\nSPACED=two words  \n"
        )
        for shell in (*POSIX_SHELLS, "nu"):
            source = self.source(shell)
            probe = 'printf "%s|%s>\\n" "$FIRST" "$SPACED"'
            if shell == "nu":
                probe = 'print $"($env.FIRST)|($env.SPACED)>"'
            result = self.run_shell(shell, f"{source}; load_env; {probe}")
            with self.subTest(shell=shell):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "one=two|two words  >\n")

            missing = self.run_shell(shell, f"{source}; load_env absent.env")
            with self.subTest(shell=shell, case="missing"):
                self.assertNotEqual(missing.returncode, 0)

    def test_fish_commands_remain_individual_shared_autoloads(self) -> None:
        for name in ("venv", "load_env"):
            self.assertTrue((NATIVE / "fish" / f"{name}.fish").is_file())
        self.assertTrue((NATIVE / "nu" / "commands.nu").is_file())


if __name__ == "__main__":
    unittest.main()
