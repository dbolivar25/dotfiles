from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".local/bin/ghostty-theme"


class GhosttyThemeTests(unittest.TestCase):
    def test_preserves_config_symlinks_when_herdr_reload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            home = root / "home"
            repo = root / "repo"
            bin_directory = root / "bin"
            tmp_directory = root / "tmp"
            for directory in (home, repo, bin_directory, tmp_directory):
                directory.mkdir(parents=True)

            herdr_source = repo / "herdr.toml"
            herdr_source.write_text(
                textwrap.dedent(
                    """\
                    [theme]
                    name = "rose-pine"
                    auto_switch = false

                    [keys]
                    prefix = "cmd+;"
                    """
                )
            )
            hunk_source = repo / "hunk.toml"
            hunk_source.write_text(
                'theme = "rose-pine"\nmode = "auto"\nline_numbers = true\n'
            )

            herdr_config = home / ".config/herdr/config.toml"
            hunk_config = home / ".config/hunk/config.toml"
            herdr_config.parent.mkdir(parents=True)
            hunk_config.parent.mkdir(parents=True)
            herdr_config.symlink_to(os.path.relpath(herdr_source, herdr_config.parent))
            hunk_config.symlink_to(os.path.relpath(hunk_source, hunk_config.parent))

            fake_uname = bin_directory / "uname"
            fake_uname.write_text("#!/bin/sh\nprintf 'Linux\\n'\n")
            fake_uname.chmod(0o755)

            fake_herdr = bin_directory / "herdr"
            fake_herdr.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    if [ "$1 $2" = "config check" ]; then
                      exit 0
                    fi
                    if [ "$1 $2" = "status server" ]; then
                      exit 0
                    fi
                    if [ "$1 $2" = "server reload-config" ]; then
                      exit 1
                    fi
                    exit 2
                    """
                )
            )
            fake_herdr.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "GHOSTTY_CONFIG_DIR": str(home / ".config/ghostty"),
                    "HERDR_BIN": str(fake_herdr),
                    "HERDR_CONFIG_PATH": str(herdr_config),
                    "HOME": str(home),
                    "HUNK_CONFIG_PATH": str(hunk_config),
                    "PATH": f"{bin_directory}:{environment['PATH']}",
                    "TMPDIR": str(tmp_directory),
                }
            )

            result = subprocess.run(
                [str(SCRIPT), "light"],
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(herdr_config.is_symlink())
            self.assertTrue(hunk_config.is_symlink())
            self.assertIn('name = "rose-pine-dawn"', herdr_source.read_text())
            self.assertIn('prefix = "cmd+;"', herdr_source.read_text())
            self.assertIn('theme = "rose-pine-dawn"', hunk_source.read_text())
            self.assertIn("line_numbers = true", hunk_source.read_text())
            self.assertEqual(herdr_source.stat().st_mode & 0o777, 0o644)
            self.assertEqual(hunk_source.stat().st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
