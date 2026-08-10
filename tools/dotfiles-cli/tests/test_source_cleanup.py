from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from dotfiles_cli.core import Context
from dotfiles_cli.shell_image import load_shell_config

REPO = Path(__file__).parents[3]
SHELL = REPO / ".config" / "shell"
CONTEXT = Context(REPO, Path.home(), REPO)


class SourceCleanupTests(unittest.TestCase):
    def test_authored_shell_tree_has_one_manifest_and_native_source(self) -> None:
        self.assertEqual(
            {path.name for path in SHELL.iterdir()},
            {"shell.toml", "native"},
        )

    def test_manifest_preserves_bun_and_mise_without_activation_hooks(self) -> None:
        config = load_shell_config(CONTEXT)
        self.assertEqual(config.environment["BUN_INSTALL"], "${HOME}/.bun")
        self.assertIn("${HOME}/.bun/bin", config.paths)
        self.assertIn("${HOME}/.local/share/mise/shims", config.paths)
        source = (SHELL / "shell.toml").read_text()
        self.assertNotIn("bun completions", source)
        self.assertNotIn("mise activate", source)

    def test_only_real_build_time_integrations_are_declared(self) -> None:
        config = load_shell_config(CONTEXT)
        coverage: dict[str, set[str]] = {}
        for recipe in config.generators:
            coverage.setdefault(recipe.integration, set()).add(recipe.shell)
        self.assertEqual(
            coverage,
            {
                "starship": {"bash", "zsh"},
                "zoxide": {"bash", "fish", "zsh", "nu"},
            },
        )

    def test_live_shell_loaders_point_directly_at_the_state_image(self) -> None:
        state = ".local/state/dotfiles/shell/v2/current/public"
        self.assertIn(state, (REPO / ".bashrc").read_text())
        self.assertIn(state, (REPO / ".zshrc").read_text())
        self.assertIn(state, (REPO / ".config/fish/conf.d/000-env.fish").read_text())
        self.assertIn(state, (REPO / ".config/nushell/env.nu").read_text())
        self.assertEqual(
            (REPO / ".config/nushell/config.nu").read_text(),
            "$env.config.show_banner = false\n",
        )

    def test_missing_image_keeps_guardable_shells_usable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dotfiles-missing-image-") as root:
            environment = {
                "HOME": root,
                "PATH": os.environ["PATH"],
                "TERM": "xterm-256color",
                "XDG_CONFIG_HOME": str(Path(root) / ".config"),
            }
            commands = {
                "bash": [
                    "/bin/bash",
                    "--noprofile",
                    "--rcfile",
                    str(REPO / ".bashrc"),
                    "-ic",
                    "exit 0",
                ],
                "fish": [
                    "fish",
                    "--no-config",
                    "-c",
                    f"source {REPO / '.config/fish/conf.d/000-env.fish'}",
                ],
                "zsh": [
                    "zsh",
                    "-dfc",
                    f"source {REPO / '.zshrc'}",
                ],
            }
            for shell, command in commands.items():
                result = subprocess.run(
                    command,
                    cwd=REPO,
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                with self.subTest(shell=shell):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("run `dotfiles shell apply`", result.stderr)

    def test_nushell_keeps_structured_ls_and_external_jj(self) -> None:
        env_config = (REPO / ".config/nushell/env.nu").read_text()
        self.assertLess(
            env_config.index("$env.ENV_CONVERSIONS"),
            env_config.index("source ~/.local/state/dotfiles/shell/v2/current"),
        )
        native = (SHELL / "native/nu/config.nu").read_text()
        self.assertNotIn("alias ls =", native)
        self.assertNotIn("alias jj =", native)
        self.assertEqual(shutil.which("jj"), "/opt/homebrew/bin/jj")
        self.assertFalse((REPO / ".config/nushell/zoxide.nu").exists())

    def test_fish_fidgets_and_autoload_sources_are_native(self) -> None:
        functions = SHELL / "native/fish/functions"
        for name in (":q", ":wa", ":wq", ":xa", "load_env", "venv"):
            with self.subTest(name=name):
                self.assertTrue((functions / f"{name}.fish").is_file())
        for path in (
            REPO / ".config/fish/conf.d/002-abbreviations.fish",
            REPO / ".config/fish/functions/bass.fish",
            REPO / ".config/fish/functions/__bass.py",
        ):
            self.assertFalse(path.exists())
        self.assertNotIn("edc/bass", (REPO / ".config/fish/fish_plugins").read_text())


if __name__ == "__main__":
    unittest.main()
