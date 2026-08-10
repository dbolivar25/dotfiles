from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[3]
GENERATED = (
    Path.home()
    / ".local"
    / "state"
    / "dotfiles"
    / "shell"
    / "v2"
    / "current"
    / "public"
)


class CommandBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def executable(self, name: str, body: str) -> Path:
        target = self.bin / name
        target.write_text(f"#!/bin/sh\nset -eu\n{body}\n")
        target.chmod(0o755)
        return target

    def environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment["PATH"] = f"{self.bin}:{environment['PATH']}"
        return environment

    def source(self, shell: str) -> str:
        path = GENERATED / shell / f"init.{shell}"
        if shell == "bash":
            return f'. "{path}"'
        return f'source "{path}"'

    def select_test_path(self, shell: str) -> str:
        if shell == "fish":
            return f"set -gx PATH {self.bin} /usr/bin /bin"
        if shell == "nu":
            return f'$env.PATH = ["{self.bin}" "/usr/bin" "/bin"]'
        return f"export PATH={self.bin}:/usr/bin:/bin"

    def run_shell(self, shell: str, body: str) -> subprocess.CompletedProcess[str]:
        commands = {
            "bash": ["/bin/bash", "--noprofile", "--norc", "-c", body],
            "fish": ["fish", "--no-config", "-c", body],
            "zsh": ["zsh", "-dfc", body],
            "nu": ["nu", "--no-config-file", "-c", body],
        }
        return subprocess.run(
            commands[shell],
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_listing_forwarders_preserve_arguments_in_every_shell(self) -> None:
        self.executable(
            "eza", 'for argument in "$@"; do printf \'<%s>\\n\' "$argument"; done'
        )
        expected = [
            "<--color=always>",
            "<--group-directories-first>",
            "<--classify>",
            "<alpha>",
            "<two words>",
        ]
        for shell in ("bash", "fish", "zsh", "nu"):
            source = self.source(shell)
            if shell == "nu":
                source = f'source "{GENERATED / "nu" / "env.nu"}"'
            result = self.run_shell(
                shell,
                f"{source}; {self.select_test_path(shell)}; l alpha 'two words'",
            )
            with self.subTest(shell=shell):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), expected)

    def test_navigation_commands_mutate_the_calling_shell(self) -> None:
        for shell in ("bash", "fish", "zsh", "nu"):
            source = self.source(shell)
            if shell == "nu":
                source = f'source "{GENERATED / "nu" / "env.nu"}"'
            probe = "mkcd child/grandchild; pwd; up 2; pwd"
            if shell == "nu":
                probe = "mkcd child/grandchild; print $env.PWD; up 2; print $env.PWD"
            result = self.run_shell(shell, f"{source}; {probe}")
            with self.subTest(shell=shell):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    result.stdout.splitlines(),
                    [str(self.root / "child" / "grandchild"), str(self.root)],
                )
            child = self.root / "child"
            if child.exists():
                for path in sorted(child.rglob("*"), reverse=True):
                    if path.is_dir():
                        path.rmdir()
                child.rmdir()

    def test_clauded_forwarder_prepends_flag_and_preserves_arguments(self) -> None:
        self.executable("claude", "printf '<%s>\\n' \"$@\"")
        for shell in ("bash", "fish", "zsh", "nu"):
            source = self.source(shell)
            if shell == "nu":
                source = f'source "{GENERATED / "nu" / "env.nu"}"'
            result = self.run_shell(
                shell,
                f"{source}; {self.select_test_path(shell)}; clauded 'hello world'",
            )
            with self.subTest(shell=shell):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    result.stdout.splitlines(),
                    ["<--dangerously-skip-permissions>", "<hello world>"],
                )

    def test_fenv_pipeline_executes_in_every_shell(self) -> None:
        for shell in ("bash", "fish", "zsh", "nu"):
            source = self.source(shell)
            if shell == "nu":
                source = f'source "{GENERATED / "nu" / "env.nu"}"'
            if shell == "bash":
                probe = (
                    "shopt -s expand_aliases; "
                    "FENV_PARITY=visible eval \"fenv '^FENV_PARITY=visible$'\""
                )
            elif shell == "zsh":
                probe = (
                    "export FENV_PARITY=visible; eval \"fenv '^FENV_PARITY=visible$'\""
                )
            elif shell == "fish":
                probe = (
                    "abbr --show fenv | string match -q \"*'env | rg'*\"; and "
                    "set -lx FENV_PARITY visible; and env | rg '^FENV_PARITY=visible$'"
                )
            else:
                probe = (
                    "with-env {FENV_PARITY: visible} { fenv '^FENV_PARITY=visible$' }"
                )
            result = self.run_shell(shell, f"{source}; {probe}")
            with self.subTest(shell=shell):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "FENV_PARITY=visible")

    def test_nushell_keeps_structured_ls(self) -> None:
        result = self.run_shell(
            "nu",
            f'source "{GENERATED / "nu" / "env.nu"}"; '
            "print (scope aliases | where name == ls | length)",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "0")


if __name__ == "__main__":
    unittest.main()
