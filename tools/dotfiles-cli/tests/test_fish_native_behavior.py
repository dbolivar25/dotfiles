from __future__ import annotations

import json
import os
import shlex
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).parents[3]
OLD_FISH_FUNCTIONS = REPO / ".config" / "fish" / "functions"
SHELL_STATE = Path.home() / ".local" / "state" / "dotfiles" / "shell" / "v2"

AUTOLOAD_DESCRIPTIONS = {
    ":q": "",
    ":wa": "",
    ":wq": "",
    ":xa": "",
    "clauded": "Run Claude with the --dangerously-skip-permissions flag",
    "l": "List directory contents with short format",
    "ll": "List directory contents with long format",
    "load_env": "",
    "ls": "List directory contents",
    "lt": "List directory contents as a tree",
    "mkcd": "",
    "up": "",
    "venv": "",
}

AUTOLOAD_WRAPS = {
    "clauded": "claude",
    "l": "eza",
    "ll": "eza",
    "ls": "eza",
    "lt": "eza",
}


def fish_function_file(name: str) -> Path:
    activation = json.loads((SHELL_STATE / "current/manifest.json").read_text())
    return (
        SHELL_STATE
        / "releases"
        / activation["active_release"]
        / "public/fish/functions"
        / f"{name}.fish"
    )


class FishNativeBehaviorTests(unittest.TestCase):
    def run_fish(self, body: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        return subprocess.run(
            ["fish", "--no-config", "--private", "-c", body],
            cwd=REPO,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_vim_fidgets_keep_exact_source_semantics(self) -> None:
        functions = REPO / ".config" / "shell" / "native" / "fish"
        expected = {
            ":q": "function :q\n    exit\nend\n",
            ":wa": "function :wa\n\nend\n",
            ":wq": "function :wq\n    exit\nend\n",
            ":xa": "function :xa\n    exit\nend\n",
        }
        self.assertEqual(
            {name: (functions / f"{name}.fish").read_text() for name in expected},
            expected,
        )

    def test_shared_functions_are_fish_autoloads_with_authored_metadata(self) -> None:
        names = " ".join(shlex.quote(name) for name in AUTOLOAD_DESCRIPTIONS)
        result = self.run_fish(
            "source .config/fish/conf.d/000-env.fish; "
            f"for name in {names}; "
            'functions --details --verbose $name | string join "|"; '
            "end"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        details = {}
        for line in result.stdout.splitlines():
            source, kind, line_number, shadowing, description = line.split("|", 4)
            name = Path(source).stem
            details[name] = (source, kind, line_number, shadowing, description)

        self.assertEqual(set(details), set(AUTOLOAD_DESCRIPTIONS))
        for name, description in AUTOLOAD_DESCRIPTIONS.items():
            with self.subTest(name=name):
                source, kind, line_number, shadowing, observed_description = details[
                    name
                ]
                self.assertEqual(
                    Path(source).resolve(), fish_function_file(name).resolve()
                )
                self.assertEqual(
                    (kind, line_number, shadowing, observed_description),
                    (
                        "autoloaded",
                        "1",
                        "scope-shadowing",
                        description,
                    ),
                )

        for name, wrapped in AUTOLOAD_WRAPS.items():
            with self.subTest(name=name, metadata="wraps"):
                declaration = fish_function_file(name).read_text().splitlines()[0]
                self.assertIn(f"--wraps={wrapped}", declaration)

    def test_fish_native_helpers_completions_and_hooks_remain_present(self) -> None:
        for hook in ("fish_prompt", "fish_greeting"):
            self.assertTrue(fish_function_file(hook).is_file())

        moved = set(AUTOLOAD_DESCRIPTIONS) | {"fish_prompt", "fish_greeting"}
        self.assertFalse(
            moved & {path.stem for path in OLD_FISH_FUNCTIONS.glob("*.fish")}
        )


if __name__ == "__main__":
    unittest.main()
