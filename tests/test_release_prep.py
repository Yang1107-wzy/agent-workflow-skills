import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = (
    Path(__file__).resolve().parents[1] / "skills/workflow-release-prep/scripts/prepare_release.py"
)


class ReleasePrepTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "package"
        self.root.mkdir()
        self.write("pyproject.toml", '[project]\nname = "synthetic"\nversion = "1.2.3"\n')
        self.write("CHANGELOG.md", "# Changelog\n\n## [1.2.3] - 2026-01-01\n\nSynthetic change.\n")
        self.write("dist/synthetic.txt", "Synthetic release fixture; not a built distribution.\n")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def cli(self, *extra, root=None, script=SCRIPT, env=None):
        return subprocess.run(
            [
                sys.executable,
                str(script),
                str(root or self.root),
                "--version",
                "1.2.3",
                "--artifact",
                "dist/synthetic.txt",
                *extra,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    def data(self, result, code=0):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return json.loads(result.stdout)

    def test_matching_metadata_changelog_and_hash_with_explicit_limits(self):
        data = self.data(self.cli())
        self.assertTrue(data["local_ready"])
        self.assertEqual(
            data["manifests"],
            [{"path": "pyproject.toml", "kind": "python", "version": "1.2.3", "status": "matched"}],
        )
        artifact = data["artifacts"][0]
        self.assertEqual(
            artifact["sha256"],
            hashlib.sha256((self.root / "dist/synthetic.txt").read_bytes()).hexdigest(),
        )
        self.assertGreater(artifact["bytes"], 0)
        self.assertEqual(data["git"]["status"], "not_repository")
        self.assertEqual(
            data["checks_not_run"],
            ["tests", "build", "artifact_source_provenance", "remote_ci", "publication"],
        )

    def test_mismatch_is_readiness_issue(self):
        self.write("pyproject.toml", '[project]\nversion = "1.2.4"\n')
        data = self.data(self.cli(), 1)
        self.assertFalse(data["local_ready"])
        self.assertEqual(data["manifests"][0]["status"], "mismatch")

    def test_generic_no_manifest_and_tool_only_pyproject(self):
        (self.root / "pyproject.toml").unlink()
        self.assertEqual(self.data(self.cli())["manifests"], [])
        self.write("pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        self.assertEqual(self.data(self.cli())["manifests"][0]["status"], "generic")

    def test_missing_and_dynamic_package_versions_remain_unresolved(self):
        for content in (
            '[project]\nname = "synthetic"\n',
            '[project]\ndynamic = ["version"]\n',
            '[project]\nversion = "1.2.3"\ndynamic = ["version"]\n',
        ):
            with self.subTest(content=content):
                self.write("pyproject.toml", content)
                self.assertEqual(self.data(self.cli(), 1)["manifests"][0]["status"], "unresolved")
        (self.root / "pyproject.toml").unlink()
        self.write("package.json", '{"name":"synthetic"}')
        self.assertEqual(self.data(self.cli(), 1)["manifests"][0]["status"], "unresolved")

    def test_both_manifests_checked_even_when_one_disagrees(self):
        self.write("package.json", '{"version":"1.2.3"}')
        self.assertEqual(len(self.data(self.cli())["manifests"]), 2)
        self.write("package.json", '{"version":"2.0.0"}')
        rows = self.data(self.cli(), 1)["manifests"]
        self.assertEqual([row["status"] for row in rows], ["matched", "mismatch"])

    def test_missing_empty_directory_and_escape_artifacts(self):
        (self.root / "empty").write_bytes(b"")
        for artifact in ("missing", "empty", "dist", "../outside", str(self.root / "empty")):
            with self.subTest(artifact=artifact):
                self.assertTrue(self.data(self.cli("--artifact", artifact), 1)["issues"])

    def test_symlink_artifact_and_symlink_directory_rejected(self):
        (self.root / "linked").symlink_to(self.root / "dist/synthetic.txt")
        (self.root / "linked-dir").symlink_to(self.root / "dist", target_is_directory=True)
        for artifact in ("linked", "linked-dir/synthetic.txt"):
            with self.subTest(artifact=artifact):
                self.assertTrue(self.data(self.cli("--artifact", artifact), 1)["issues"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "named pipes are unavailable on this platform")
    def test_fifo_is_rejected_without_blocking(self):
        os.mkfifo(self.root / "fifo")
        self.assertTrue(self.data(self.cli("--artifact", "fifo"), 1)["issues"])

    def test_changelog_heading_requires_exact_version_not_body_or_substring(self):
        for content in (
            "## 11.2.3\nMentions 1.2.3 in body.\n",
            "## Unreleased\n1.2.3\n",
            "## 1.2.30\nSynthetic\n",
            "## 1.2.3-rc.1\nSynthetic\n",
        ):
            with self.subTest(content=content):
                self.write("CHANGELOG.md", content)
                self.assertTrue(self.data(self.cli(), 1)["issues"])
        (self.root / "CHANGELOG.md").unlink()
        self.assertTrue(self.data(self.cli(), 1)["issues"])

    def test_fenced_example_headings_are_not_release_sections(self):
        for fence in ("```", "~~~"):
            with self.subTest(fence=fence):
                content = f"# Changelog\n{fence}markdown\n## 1.2.3\n{fence}\n"
                self.write("CHANGELOG.md", content)
                self.assertTrue(self.data(self.cli(), 1)["issues"])
                self.write("CHANGELOG.md", content + "\n## [1.2.3]\nActual section.\n")
                self.assertTrue(self.data(self.cli())["changelog"]["matched"])

    def test_atx_changelog_headings_accept_zero_to_three_leading_spaces(self):
        for spaces in range(4):
            with self.subTest(spaces=spaces):
                self.write("CHANGELOG.md", " " * spaces + "## [1.2.3]\nSynthetic section.\n")
                changelog = self.data(self.cli())["changelog"]
                self.assertTrue(changelog["matched"])
                self.assertEqual(changelog["heading"], "## [1.2.3]")

    def test_four_space_indented_code_heading_is_not_a_release_section(self):
        self.write("CHANGELOG.md", "    ## [1.2.3]\n    Synthetic code example.\n")
        self.assertFalse(self.data(self.cli(), 1)["changelog"]["matched"])

    def test_strict_semver_requested_and_manifest(self):
        for version in ("01.2.3", "1.2", "v1.2.3", "1.2.3-rc.1", "1.2.3+build", "1.2.3\n"):
            with self.subTest(version=version):
                result = self.cli("--version", version)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
        self.write("package.json", '{"version":123}')
        self.assertEqual(self.cli().returncode, 2)

    def test_literal_toml_single_quotes_comments_and_unrelated_fields(self):
        self.write(
            "pyproject.toml",
            "[project]\nversion = '1.2.3' # local version\n"
            'dependencies = [\n  "demo>=1",\n]\n[project.urls]\nHomepage = "invalid"\n',
        )
        self.assertTrue(self.data(self.cli())["local_ready"])

    def test_ambiguous_or_unsupported_project_metadata_is_input_error(self):
        for content in (
            '[project]\nversion="1.2.3"\nversion="1.2.3"\n',
            "[project]\nversion=42\n",
            '[project]\nversion="1.2.3\n',
            '[project]\nversion="""1.2.3"""\n',
            '[project]\n"version"="1.2.3"\n',
            'project.version="1.2.3"\n',
            'project={version="1.2.3"}\n',
            '["project"]\nversion="1.2.3"\n',
            '[project]\nversion="1.2.3"\n[project]\n',
            '[project]\ndynamic=[\n"version"\n]\n',
        ):
            with self.subTest(content=content):
                self.write("pyproject.toml", content)
                result = self.cli()
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)

    def test_multiline_project_strings_cannot_supply_spurious_literal_version(self):
        self.write("pyproject.toml", '[project]\ndescription = """\nversion="1.2.3"\n"""\n')
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(result.stdout, "")

    def test_nested_project_metadata_without_version_is_unresolved(self):
        self.write("pyproject.toml", '[project.urls]\nHomepage = "synthetic.invalid"\n')
        self.assertEqual(self.data(self.cli(), 1)["manifests"][0]["status"], "unresolved")

    def test_unsupported_version_table_and_quoted_key_forms_are_input_errors(self):
        for content in (
            '[project]\n"version".extra="1.2.3"\n',
            '[project.version]\nvalue="1.2.3"\n',
        ):
            with self.subTest(content=content):
                self.write("pyproject.toml", content)
                self.assertEqual(self.cli().returncode, 2)

    def assert_unsupported_toml_in_cli_and_memory(self, content):
        self.write("pyproject.toml", content)
        with self.subTest(interface="cli", content=content):
            result = self.cli()
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("Traceback", result.stderr)
        with self.subTest(interface="memory", content=content):
            spec = importlib.util.spec_from_file_location("release_prep", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with self.assertRaises(ValueError):
                module.python_version(content)

    def test_escaped_quoted_project_tables_cannot_be_classified_generic(self):
        self.assert_unsupported_toml_in_cli_and_memory('["pro\\u006aect"]\nversion = "9.9.9"\n')

    def test_escaped_quoted_metadata_keys_cannot_bypass_version_checks(self):
        for content in (
            '[project]\n"ver\\u0073ion" = "9.9.9"\n',
            '[project]\nversion = "1.2.3"\n"ver\\u0073ion" = "9.9.9"\n',
            '"pro\\u006aect" = {version = "9.9.9"}\n',
        ):
            self.assert_unsupported_toml_in_cli_and_memory(content)

    def test_malformed_duplicate_deep_or_nonobject_json_is_input_error(self):
        for content in (
            "{",
            '{"version":"1.2.3","version":"1.2.3"}',
            "[]",
            '{"version":"1.2.3","x":' + "[" * 2000 + "0" + "]" * 2000 + "}",
            '{"version":"1.2.3","x":NaN}',
        ):
            with self.subTest(content=content[:60]):
                self.write("package.json", content)
                result = self.cli()
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)

    def test_bounded_metadata_and_invalid_utf8(self):
        for content in (b"x" * (1024 * 1024 + 1), b"\xff"):
            (self.root / "package.json").write_bytes(content)
            result = self.cli()
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)

    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout.strip()

    def repository(self):
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", ".")
        self.git("-c", "commit.gpgSign=false", "commit", "-m", "synthetic fixture")
        return self.git("rev-parse", "HEAD")

    def test_git_commit_and_dirty_state_without_mutation(self):
        commit = self.repository()
        data = self.data(self.cli())
        self.assertEqual(data["git"]["commit"], commit)
        self.assertFalse(data["git"]["dirty"])
        self.write("untracked.txt", "synthetic pending work\n")
        before = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        data = self.data(self.cli(), 1)
        self.assertTrue(data["git"]["dirty"])
        after = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        self.assertEqual(after, before)

    def test_inherited_git_directory_cannot_redirect_selected_source(self):
        commit = self.repository()
        env = {**os.environ, "GIT_DIR": "/missing-git-dir", "GIT_WORK_TREE": "/missing"}
        self.assertEqual(self.data(self.cli(env=env))["git"]["commit"], commit)

    def test_ancestor_repository_is_outside_selected_source_scope(self):
        self.repository()
        self.write("unrelated-dirty.txt", "Synthetic unrelated ancestor changes.\n")
        nested = self.root / "nested-package"
        nested.mkdir()
        self.write("nested-package/CHANGELOG.md", "## 1.2.3\nSynthetic generic package.\n")
        self.write("nested-package/dist/synthetic.txt", "Synthetic artifact.\n")
        data = self.data(self.cli(root=nested))
        self.assertEqual(
            data["git"],
            {
                "status": "outside_selected_scope",
                "commit": None,
                "dirty": None,
                "provenance": "not_checked",
            },
        )

    def test_worktree_git_file_recognizes_exact_selected_root(self):
        self.repository()
        worktree = Path(self.temp.name) / "worktree"
        self.git("worktree", "add", "--detach", str(worktree), "HEAD")
        self.assertTrue((worktree / ".git").is_file())
        data = self.data(self.cli(root=worktree))
        self.assertEqual(data["git"]["status"], "checked")
        self.assertEqual(data["git"]["commit"], self.git("rev-parse", "HEAD"))

    def test_markdown_output_and_unicode_under_ascii_locale(self):
        self.write("dist/资料.txt", "Synthetic UTF-8 artifact\n")
        env = {**os.environ, "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
        data = self.data(self.cli("--artifact", "dist/资料.txt", env=env))
        self.assertEqual(data["artifacts"][1]["path"], "dist/资料.txt")
        result = self.cli("--artifact", "dist/资料.txt", "--format", "markdown", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dist/资料.txt", result.stdout)
        self.assertIn("not run", result.stdout)
        self.assertIn(data["artifacts"][0]["sha256"], result.stdout)

    def surrogate_argv_cli(self, relative_bytes, output_format):
        # Reproduce Linux ASCII-locale argv even on POSIX systems with UTF-8 filesystems.
        wrapper = (
            "import runpy,sys; script,root,relative,output_format=sys.argv[1:]; "
            "relative=bytes.fromhex(relative).decode('ascii','surrogateescape'); "
            "sys.argv=[script,root,'--version','1.2.3','--artifact',relative,"
            "'--format',output_format]; runpy.run_path(script,run_name='__main__')"
        )
        return subprocess.run(
            [
                sys.executable,
                "-c",
                wrapper,
                str(SCRIPT),
                str(self.root),
                relative_bytes.hex(),
                output_format,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    @unittest.skipUnless(os.name == "posix", "surrogateescape paths require POSIX")
    def test_surrogateescaped_utf8_argv_reports_real_path_and_hash_without_mutation(self):
        relative = "dist/资料.txt"
        self.write(relative, "Synthetic UTF-8 artifact\n")
        before = {
            p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()
        }
        digest = hashlib.sha256(before[Path(relative)]).hexdigest()
        for output_format in ("json", "markdown"):
            with self.subTest(output_format=output_format):
                result = self.surrogate_argv_cli(relative.encode("utf-8"), output_format)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(relative, result.stdout)
                self.assertIn(digest, result.stdout)
                if output_format == "json":
                    row = self.data(result)["artifacts"][0]
                    self.assertEqual(row["path"], relative)
                    self.assertEqual(row["bytes"], len(before[Path(relative)]))
                    self.assertEqual(row["sha256"], digest)
        after = {
            p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()
        }
        self.assertEqual(after, before)

    @unittest.skipUnless(os.name == "posix", "surrogateescape paths require POSIX")
    def test_surrogateescaped_missing_path_issues_recover_unicode_and_escape_invalid_bytes(self):
        for relative_bytes, displayed in (
            ("dist/不存在.txt".encode("utf-8"), "dist/不存在.txt"),
            (b"dist/invalid-\xff.txt", r"dist/invalid-\xff.txt"),
        ):
            for output_format in ("json", "markdown"):
                with self.subTest(relative_bytes=relative_bytes, output_format=output_format):
                    result = self.surrogate_argv_cli(relative_bytes, output_format)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    if output_format == "json":
                        self.assertEqual(
                            self.data(result, 1)["issues"], [f"missing artifact: {displayed}"]
                        )
                    else:
                        self.assertIn(f"missing artifact: {displayed}", result.stdout)
                    self.assertNotIn("\ufffd", result.stdout)

    @unittest.skipUnless(sys.platform.startswith("linux"), "macOS rejects invalid UTF-8 filenames")
    def test_invalid_byte_artifact_reports_visible_escape_and_exact_hash(self):
        relative_bytes = b"dist/invalid-\xff.txt"
        content = b"Synthetic raw-byte filename artifact\n"
        with open(os.fsencode(self.root) + b"/" + relative_bytes, "wb") as stream:
            stream.write(content)
        for output_format in ("json", "markdown"):
            with self.subTest(output_format=output_format):
                result = self.surrogate_argv_cli(relative_bytes, output_format)
                self.assertEqual(result.returncode, 0, result.stderr)
                digest = hashlib.sha256(content).hexdigest()
                if output_format == "json":
                    self.assertEqual(
                        self.data(result)["artifacts"],
                        [
                            {
                                "path": r"dist/invalid-\xff.txt",
                                "bytes": len(content),
                                "sha256": digest,
                            }
                        ],
                    )
                else:
                    self.assertIn(r"dist/invalid-\xff.txt", result.stdout)
                    self.assertIn(digest, result.stdout)
                self.assertNotIn("\ufffd", result.stdout)
        with open(os.fsencode(self.root) + b"/" + relative_bytes, "rb") as stream:
            self.assertEqual(stream.read(), content)

    def test_missing_root_and_invalid_usage(self):
        self.assertEqual(self.cli(root=self.root / "absent").returncode, 2)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), "--version", "1.2.3"], capture_output=True
        )
        self.assertEqual(result.returncode, 2)

    def test_closed_stdout_consumer_has_no_shutdown_traceback(self):
        process = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                str(self.root),
                "--version",
                "1.2.3",
                "--artifact",
                "dist/synthetic.txt",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        process.stdout.close()
        stderr = process.communicate()[1].decode("utf-8", errors="replace")
        self.assertEqual(process.returncode, 2, stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("Exception ignored", stderr)
        self.assertNotIn("BrokenPipeError", stderr)

    def test_closed_stdout_descriptor_is_input_io_error(self):
        wrapper = (
            "import os,runpy,sys; script,root=sys.argv[1:3]; os.close(1); "
            "sys.argv=[script,root,'--version','1.2.3','--artifact','dist/synthetic.txt']; "
            "runpy.run_path(script,run_name='__main__')"
        )
        result = subprocess.run(
            [sys.executable, "-c", wrapper, str(SCRIPT), str(self.root)], capture_output=True
        )
        stderr = result.stderr.decode("utf-8", errors="replace")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("Exception ignored", stderr)

    def test_generic_stdout_io_failure_is_normalized(self):
        spec = importlib.util.spec_from_file_location("release_prep", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with (
            mock.patch.object(module.sys, "stdout") as stdout,
            mock.patch.object(module.sys, "stderr", io.StringIO()) as stderr,
        ):
            stdout.write.side_effect = OSError("synthetic output failure")
            self.assertEqual(
                module.main(
                    [str(self.root), "--version", "1.2.3", "--artifact", "dist/synthetic.txt"]
                ),
                2,
            )
            stdout.flush.assert_not_called()
            self.assertIn("synthetic output failure", stderr.getvalue())

    def test_generic_stdout_flush_failure_is_normalized(self):
        spec = importlib.util.spec_from_file_location("release_prep", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with (
            mock.patch.object(module.sys, "stdout") as stdout,
            mock.patch.object(module.sys, "stderr", io.StringIO()) as stderr,
        ):
            stdout.flush.side_effect = OSError("synthetic flush failure")
            self.assertEqual(
                module.main(
                    [str(self.root), "--version", "1.2.3", "--artifact", "dist/synthetic.txt"]
                ),
                2,
            )
            self.assertIn("synthetic flush failure", stderr.getvalue())

    def test_json_quoted_braces_do_not_count_as_nesting(self):
        self.write("package.json", json.dumps({"version": "1.2.3", "description": "[" * 100}))
        self.assertTrue(self.data(self.cli())["local_ready"])

    def test_standalone_installed_skill(self):
        target = Path(self.temp.name) / "installed/workflow-release-prep"
        shutil.copytree(SCRIPT.parents[1], target)
        self.assertTrue(
            self.data(self.cli(script=target / "scripts/prepare_release.py"))["local_ready"]
        )


if __name__ == "__main__":
    unittest.main()
