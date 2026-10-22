from __future__ import annotations

import io
import json
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from dotfiles_cli.cli import main
from dotfiles_cli.core import Context, DotfilesError, shell_probe_command
from dotfiles_cli.shell_image import (
    activate_shell_image,
    apply_shell_image,
    check_shell_image,
    collect_shell_image_checks,
    compile_shell_image,
    load_private_secrets,
    rollback_shell_image,
    stage_shell_image,
    write_private_shell_config,
)

MANIFEST = """schema = 1
paths = ["${HOME}/managed", "${HOME}/.local/bin", "/usr/bin", "/bin"]
required_commands = ["sh"]

[environment]
EXAMPLE_HOME = "${HOME}/example"

[editor]
local = "nvim"
ssh = "vim"

[shortcuts]
gst = "git status"
ls = { expansion = "ls -l", shells = ["bash", "fish", "zsh"] }

[forwarders.l]
argv = ["eza", "--classify"]
description = "List files"

[integrations]
"""


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name).resolve()
        self.context = Context(self.repo, self.repo, self.repo)
        subprocess.run(
            ["git", "init", "-q", str(self.repo)], capture_output=True, check=True
        )
        shell_root = self.context.shell_root
        (shell_root / "native" / "nu").mkdir(parents=True)
        (shell_root / "native" / "fish").mkdir(parents=True)
        (shell_root / "native" / "sh").mkdir(parents=True)
        (self.repo / "managed").mkdir()
        (self.repo / ".local" / "bin").mkdir(parents=True)
        (shell_root / "shell.toml").write_text(MANIFEST)
        (shell_root / "native" / "sh" / "functions.sh").write_text("")
        (shell_root / "native" / "nu" / "commands.nu").write_text("")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str, stdin: str | None = None) -> tuple[int, str]:
        output = io.StringIO()
        command = ["--repo", str(self.repo), *arguments]
        stream = io.StringIO(stdin) if stdin is not None else None
        with (
            redirect_stdout(output),
            patch("dotfiles_cli.cli.Context.discover", return_value=self.context),
        ):
            if stream is None:
                status = main(command)
            else:
                with patch("sys.stdin", stream):
                    status = main(command)
        return status, output.getvalue()

    def active_release(self) -> str:
        activation = json.loads(
            (self.context.active_shell_dir / "manifest.json").read_text()
        )
        return activation["active_release"]

    def test_manifest_compiles_to_each_native_shortcut_mechanism(self) -> None:
        image = compile_shell_image(self.context)
        self.assertIn("alias gst='git status'", image.public_files["bash/init.bash"])
        self.assertIn("alias gst='git status'", image.public_files["zsh/init.zsh"])
        self.assertIn(
            "abbr --add -- gst 'git status'", image.public_files["fish/init.fish"]
        )
        self.assertNotIn("fish_complete_path", image.public_files["fish/init.fish"])
        self.assertIn("alias gst = git status", image.public_files["nu/config.nu"])
        self.assertNotIn("alias ls =", image.public_files["nu/config.nu"])

    def test_manifest_refuses_to_shadow_nushell_ls(self) -> None:
        manifest = self.context.shell_manifest
        manifest.write_text(
            MANIFEST.replace(
                'shells = ["bash", "fish", "zsh"]',
                'shells = ["bash", "fish", "zsh", "nu"]',
            )
        )
        with self.assertRaisesRegex(DotfilesError, "refusing to shadow Nushell ls"):
            compile_shell_image(self.context)

    def test_manifest_rejects_unknown_keys(self) -> None:
        self.context.shell_manifest.write_text(
            MANIFEST.replace("[environment]", "unexpected = true\n\n[environment]")
        )
        with self.assertRaisesRegex(DotfilesError, "unknown key: unexpected"):
            compile_shell_image(self.context)

    def test_manifest_rejects_malformed_forwarder_argv(self) -> None:
        self.context.shell_manifest.write_text(
            MANIFEST.replace('argv = ["eza", "--classify"]', 'argv = "eza"')
        )
        with self.assertRaisesRegex(DotfilesError, "expected a list of strings"):
            compile_shell_image(self.context)

    def test_manifest_rejects_unsupported_interpolation(self) -> None:
        self.context.shell_manifest.write_text(
            MANIFEST.replace("${HOME}/managed", "${USER}/managed")
        )
        with self.assertRaisesRegex(DotfilesError, "only.*HOME.*interpolation"):
            compile_shell_image(self.context)

    def test_manifest_rejects_shared_native_command_collisions(self) -> None:
        (self.context.native_dir / "sh" / "functions.sh").write_text("gst() { :; }\n")
        with self.assertRaisesRegex(
            DotfilesError, "shared command conflicts with native bash: gst"
        ):
            compile_shell_image(self.context)

    def test_shell_check_has_no_persistent_side_effect(self) -> None:
        plan = check_shell_image(self.context)
        self.assertIn("is valid", plan.summary)
        self.assertFalse(self.context.shell_v2_dir.exists())

    def test_shell_apply_activates_one_release_pair(self) -> None:
        status, output = self.run_cli("shell", "apply")
        self.assertEqual(status, 0)
        self.assertIn("Apply shell image", output)
        self.assertTrue(self.context.active_shell_dir.is_symlink())
        active = self.active_release()
        activation = self.context.active_shell_dir.resolve()
        release = self.context.shell_v2_dir / "releases" / active
        self.assertTrue((release / "public/bash/init.bash").is_file())
        self.assertTrue((release / "private/nu/secrets.nuon").is_file())
        self.assertTrue((activation / "public").is_dir())
        self.assertFalse((activation / "public").is_symlink())
        self.assertEqual(
            (activation / "private").resolve(), (release / "private").resolve()
        )
        for wrapper in (activation / "public").rglob("*"):
            if wrapper.is_file():
                self.assertIn(active, wrapper.read_text())
                self.assertNotIn("/current/", wrapper.read_text())
        self.assertEqual(
            stat.S_IMODE((release / "private/nu/secrets.nuon").stat().st_mode),
            0o600,
        )

    def test_activation_pins_one_public_private_pair_across_transitions(self) -> None:
        self.context.shell_manifest.write_text(
            MANIFEST.replace(
                'EXAMPLE_HOME = "${HOME}/example"',
                'EXAMPLE_HOME = "${HOME}/example"\nPAIR_PUBLIC = "public-a"',
            )
        )
        write_private_shell_config(self.context, {"PAIR_PRIVATE": "private-a"})
        apply_shell_image(self.context)
        release_a = self.active_release()
        activation_a = self.context.active_shell_dir.resolve()

        self.context.shell_manifest.write_text(
            self.context.shell_manifest.read_text().replace(
                'PAIR_PUBLIC = "public-a"', 'PAIR_PUBLIC = "public-b"'
            )
        )
        write_private_shell_config(self.context, {"PAIR_PRIVATE": "private-b"})
        apply_shell_image(self.context)

        self.assertTrue(activation_a.is_dir())
        self.assertTrue((self.context.shell_v2_dir / "releases" / release_a).is_dir())
        environment = {
            "HOME": str(self.repo),
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "TERM": "xterm-256color",
        }
        wrappers = activation_a / "public"
        commands = {
            "bash": [
                "/bin/bash",
                "--noprofile",
                "--norc",
                "-c",
                (
                    f'. "{wrappers / "bash/init.bash"}"; '
                    'printf "%s|%s\\n" "$PAIR_PUBLIC" "$PAIR_PRIVATE"'
                ),
            ],
            "fish": [
                "fish",
                "--no-config",
                "-c",
                (
                    f'source "{wrappers / "fish/init.fish"}"; '
                    "printf '%s|%s\\n' $PAIR_PUBLIC $PAIR_PRIVATE"
                ),
            ],
            "zsh": [
                "zsh",
                "-dfc",
                (
                    f'source "{wrappers / "zsh/init.zsh"}"; '
                    'printf "%s|%s\\n" "$PAIR_PUBLIC" "$PAIR_PRIVATE"'
                ),
            ],
            "nu": [
                "nu",
                "--no-config-file",
                "-c",
                (
                    f'source "{wrappers / "nu/env.nu"}"; '
                    'print $"($env.PAIR_PUBLIC)|($env.PAIR_PRIVATE)"'
                ),
            ],
        }
        for shell, command in commands.items():
            result = subprocess.run(
                command,
                cwd=self.repo,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            with self.subTest(shell=shell):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "public-a|private-a")

    def test_status_names_the_active_shell_release(self) -> None:
        apply_shell_image(self.context)
        status, output = self.run_cli("status")
        self.assertEqual(status, 0)
        self.assertIn(f"Shell image: {self.active_release()}", output)

    def test_stage_does_not_change_the_active_release(self) -> None:
        apply_shell_image(self.context)
        first = self.active_release()
        self.context.shell_manifest.write_text(MANIFEST + "\n# release B\n")
        image = stage_shell_image(self.context)
        self.assertEqual(self.active_release(), first)
        self.assertNotEqual(image.digest, first)
        activate_shell_image(self.context, image)
        self.assertEqual(self.active_release(), image.digest)

    def test_rollback_is_reversible_across_a_b_a_b(self) -> None:
        apply_shell_image(self.context)
        release_a = self.active_release()
        self.context.shell_manifest.write_text(MANIFEST + "\n# release B\n")
        apply_shell_image(self.context)
        release_b = self.active_release()
        self.assertNotEqual(release_a, release_b)

        rollback_shell_image(self.context)
        self.assertEqual(self.active_release(), release_a)
        rollback_shell_image(self.context)
        self.assertEqual(self.active_release(), release_b)

    def test_rollback_refuses_a_drifted_release_without_changing_current(self) -> None:
        apply_shell_image(self.context)
        release_a = self.active_release()
        self.context.shell_manifest.write_text(MANIFEST + "\n# release B\n")
        apply_shell_image(self.context)
        release_b = self.active_release()
        rollback_file = (
            self.context.shell_v2_dir / "releases" / release_a / "public/bash/init.bash"
        )
        rollback_file.write_text(rollback_file.read_text() + "# drift\n")

        with self.assertRaisesRegex(DotfilesError, "has drifted"):
            rollback_shell_image(self.context)

        self.assertEqual(self.active_release(), release_b)

    def test_rollback_refuses_an_unsafe_release_mode(self) -> None:
        apply_shell_image(self.context)
        release_a = self.active_release()
        self.context.shell_manifest.write_text(MANIFEST + "\n# release B\n")
        apply_shell_image(self.context)
        release_b = self.active_release()
        rollback_file = (
            self.context.shell_v2_dir
            / "releases"
            / release_a
            / "private/nu/secrets.nuon"
        )
        rollback_file.chmod(0o644)

        with self.assertRaisesRegex(DotfilesError, "unsafe mode"):
            rollback_shell_image(self.context)

        self.assertEqual(self.active_release(), release_b)

    def test_pruning_keeps_public_autoloads_and_two_private_releases(self) -> None:
        fish_functions = self.context.native_dir / "fish"
        (fish_functions / "retained_probe.fish").write_text(
            "function retained_probe\n    echo retained\nend\n"
        )
        apply_shell_image(self.context)
        release_a = self.active_release()

        self.context.shell_manifest.write_text(MANIFEST + "\n# release B\n")
        apply_shell_image(self.context)
        release_b = self.active_release()
        self.context.shell_manifest.write_text(MANIFEST + "\n# release C\n")
        plan = apply_shell_image(self.context)
        release_c = self.active_release()
        self.assertIn(
            "prune-private-history", {item.operation for item in plan.actions}
        )

        releases = self.context.shell_v2_dir / "releases"
        self.assertTrue((releases / release_a / "public").is_dir())
        self.assertFalse((releases / release_a / "private").exists())
        self.assertTrue((releases / release_b / "private").is_dir())
        self.assertTrue((releases / release_c / "private").is_dir())
        result = subprocess.run(
            [
                "fish",
                "--no-config",
                "-c",
                (
                    "set -p fish_function_path "
                    f"{releases / release_a / 'public/fish/functions'}; "
                    "retained_probe"
                ),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "retained")

        self.context.shell_manifest.write_text(MANIFEST)
        apply_shell_image(self.context)
        self.assertEqual(self.active_release(), release_a)
        self.assertTrue((releases / release_a / "private").is_dir())

    def test_existing_release_drift_blocks_reactivation(self) -> None:
        apply_shell_image(self.context)
        active = (
            self.context.shell_v2_dir
            / "releases"
            / self.active_release()
            / "public/bash/init.bash"
        )
        active.write_text(active.read_text() + "# drift\n")
        with self.assertRaisesRegex(DotfilesError, "has drifted"):
            apply_shell_image(self.context)

    def test_source_drift_is_reported_without_changing_current(self) -> None:
        apply_shell_image(self.context)
        active = self.active_release()
        self.context.shell_manifest.write_text(MANIFEST + "\n# changed\n")
        source_check = next(
            check
            for check in collect_shell_image_checks(self.context)
            if check[1] == "shell image sources"
        )
        self.assertEqual(source_check[0], "fail")
        self.assertEqual(self.active_release(), active)

    def test_secret_plan_never_prompts_or_writes(self) -> None:
        status, output = self.run_cli("secret", "set", "EXAMPLE_TOKEN")
        self.assertEqual(status, 0)
        self.assertIn("value will not be displayed", output)
        self.assertFalse(self.context.private_shell_manifest.exists())

    def test_secret_apply_uses_one_private_toml_with_safe_modes(self) -> None:
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
        self.assertEqual(
            load_private_secrets(self.context)["EXAMPLE_TOKEN"], "private-value"
        )
        self.assertEqual(
            stat.S_IMODE(self.context.private_shell_manifest.stat().st_mode), 0o600
        )
        self.assertEqual(
            stat.S_IMODE(self.context.private_shell_manifest.parent.stat().st_mode),
            0o700,
        )

    def test_unsafe_private_source_mode_is_rejected(self) -> None:
        write_private_shell_config(self.context, {"EXAMPLE_TOKEN": "private-value"})
        self.context.private_shell_manifest.chmod(0o644)
        with self.assertRaisesRegex(DotfilesError, "mode 0600"):
            load_private_secrets(self.context)

    def test_adding_secret_backs_up_the_complete_private_manifest(self) -> None:
        write_private_shell_config(
            self.context,
            {"EXAMPLE_TOKEN": "old-value", "SECOND_TOKEN": "keep-value"},
        )
        status, _ = self.run_cli(
            "secret",
            "set",
            "NEW_TOKEN",
            "--stdin",
            "--apply",
            stdin="new-value\n",
        )
        self.assertEqual(status, 0)
        backups = list((self.repo / ".Trash/dotfiles-secrets").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        self.assertIn('EXAMPLE_TOKEN = "old-value"', backups[0].read_text())
        self.assertIn('SECOND_TOKEN = "keep-value"', backups[0].read_text())

    def test_secret_update_refreshes_an_active_pair(self) -> None:
        write_private_shell_config(self.context, {"EXAMPLE_TOKEN": "old-value"})
        apply_shell_image(self.context)
        old_release = self.active_release()
        status, _ = self.run_cli(
            "secret",
            "set",
            "EXAMPLE_TOKEN",
            "--stdin",
            "--apply",
            stdin="new-value\n",
        )
        self.assertEqual(status, 0)
        self.assertNotEqual(self.active_release(), old_release)
        release = self.context.shell_v2_dir / "releases" / self.active_release()
        self.assertIn("new-value", (release / "private/nu/secrets.nuon").read_text())

    def test_private_value_never_lands_in_public_release(self) -> None:
        write_private_shell_config(self.context, {"EXAMPLE_TOKEN": "private-value"})
        apply_shell_image(self.context)
        release = self.context.shell_v2_dir / "releases" / self.active_release()
        public_text = "\n".join(
            path.read_text()
            for path in (release / "public").rglob("*")
            if path.is_file()
        )
        self.assertNotIn("private-value", public_text)
        self.assertIn(
            "private-value", (release / "private/nu/secrets.nuon").read_text()
        )

    def test_public_source_cannot_repeat_a_private_value(self) -> None:
        write_private_shell_config(
            self.context, {"EXAMPLE_TOKEN": "unique-private-value-987"}
        )
        self.context.shell_manifest.write_text(
            MANIFEST.replace("git status", "unique-private-value-987")
        )
        with self.assertRaisesRegex(DotfilesError, "contains secret EXAMPLE_TOKEN"):
            compile_shell_image(self.context)

    def test_generator_is_prebuilt_into_private_machine_state(self) -> None:
        executable = self.repo / ".local" / "bin" / "example"
        executable.write_text(
            "#!/bin/sh\n"
            "if [ \"${1-}\" = --version ]; then echo 'example 1.0'; "
            "else echo 'export EXAMPLE_GENERATED=1'; fi\n"
        )
        executable.chmod(0o755)
        self.context.shell_manifest.write_text(
            MANIFEST.replace(
                "[integrations]\n",
                '[integrations.example]\nbash = ["example", "hook", "bash"]\n',
            )
        )
        image = compile_shell_image(self.context)
        self.assertIn("# example (prebuilt)", image.private_files["bash/init.bash"])
        self.assertIn("EXAMPLE_GENERATED=1", image.private_files["bash/init.bash"])
        self.assertNotIn("EXAMPLE_GENERATED=1", image.public_files["bash/init.bash"])

    def test_generator_reads_checkout_config_before_stow(self) -> None:
        fresh_home = self.repo / "unlinked-home"
        fresh_home.mkdir()
        context = Context(self.repo, fresh_home, self.repo)
        config = self.repo / ".config/example/init.bash"
        config.parent.mkdir(parents=True)
        config.write_text("export EXAMPLE_GENERATED=from_checkout\n")
        executable = self.repo / ".local/bin/example"
        executable.write_text(
            "#!/bin/sh\n"
            "if [ \"${1-}\" = --version ]; then echo 'example 1.0'; "
            'else cat "$XDG_CONFIG_HOME/example/init.bash"; fi\n'
        )
        executable.chmod(0o755)
        self.context.shell_manifest.write_text(
            MANIFEST.replace(
                "[integrations]\n",
                f"[integrations.example]\nbash = [{json.dumps(str(executable))}]\n",
            )
        )
        image = compile_shell_image(context)
        self.assertFalse((fresh_home / ".config").exists())
        self.assertIn(
            "export EXAMPLE_GENERATED=from_checkout",
            image.private_files["bash/init.bash"],
        )

    def test_shell_check_rejects_invalid_private_generator_syntax(self) -> None:
        executable = self.repo / ".local" / "bin" / "example"
        executable.write_text(
            "#!/bin/sh\n"
            "if [ \"${1-}\" = --version ]; then echo 'example 1.0'; "
            "else printf 'if\\n'; fi\n"
        )
        executable.chmod(0o755)
        self.context.shell_manifest.write_text(
            MANIFEST.replace(
                "[integrations]\n",
                '[integrations.example]\nbash = ["example", "hook", "bash"]\n',
            )
        )

        with self.assertRaisesRegex(
            DotfilesError, "generated bash private syntax failed"
        ):
            check_shell_image(self.context)

    def test_failed_stow_does_not_activate_staged_image(self) -> None:
        apply_shell_image(self.context)
        original = self.active_release()
        self.context.shell_manifest.write_text(MANIFEST + "\n# release B\n")
        image = stage_shell_image(self.context)
        simulation = subprocess.CompletedProcess(
            ["stow"], returncode=0, stdout="simulation passed\n"
        )
        failure = subprocess.CompletedProcess(["stow"], returncode=9)
        with (
            patch("dotfiles_cli.cli.stage_shell_image", return_value=image),
            patch("dotfiles_cli.cli.subprocess.run", side_effect=[simulation, failure]),
        ):
            status, _ = self.run_cli("stow", "--apply")
        self.assertEqual(status, 9)
        self.assertEqual(self.active_release(), original)

    def test_json_secret_plan_is_machine_readable(self) -> None:
        status, output = self.run_cli("--json", "secret", "set", "EXAMPLE_TOKEN")
        self.assertEqual(status, 0)
        payload = json.loads(output)
        self.assertTrue(payload["changes"])
        self.assertEqual(payload["actions"][0]["operation"], "write-private")

    def test_capture_does_not_execute_without_apply(self) -> None:
        marker = self.repo / "capture-ran"
        status, _ = self.run_cli("capture", "--", "/usr/bin/touch", str(marker))
        self.assertEqual(status, 0)
        self.assertFalse(marker.exists())

    def test_bash_image_deduplicates_paths_in_managed_order(self) -> None:
        first = self.repo / "managed one"
        second = self.repo / "managed-two"
        inherited = self.repo / "inherited"
        for directory in (first, second, inherited):
            directory.mkdir()
        manifest = MANIFEST.replace(
            'paths = ["${HOME}/managed", "${HOME}/.local/bin", "/usr/bin", "/bin"]',
            'paths = ["${HOME}/managed one", "${HOME}/managed-two"]',
        )
        self.context.shell_manifest.write_text(manifest)
        apply_shell_image(self.context)
        environment = {
            "HOME": str(self.repo),
            "PATH": f"{second}:{inherited}:{inherited}",
        }
        result = subprocess.run(
            shell_probe_command(
                self.context,
                "bash",
                'IFS=: read -r -a values <<< "$PATH"; printf \'%s\\0\' "${values[@]}"',
            ),
            cwd=self.repo,
            env=environment,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(
            result.stdout.decode().split("\0")[:-1],
            [str(first), str(second), str(inherited)],
        )


if __name__ == "__main__":
    unittest.main()
