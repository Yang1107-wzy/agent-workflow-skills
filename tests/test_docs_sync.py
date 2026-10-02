import base64
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/workflow-docs-sync/scripts/change_manifest.py"


class DocsSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write("tool.py", "print('before')\n")
        self.write("README.md", "Synthetic tool instructions.\n")
        self.write("docs/usage.md", "Synthetic usage.\n")
        self.write("CONTRIBUTING.rst", "Synthetic contributors.\n")
        self.write("CHANGELOG.md", "Synthetic history.\n")
        self.write("notes.md", "Not a convention candidate.\n")
        self.base = self.commit("base")

    def git(self, *args):
        result = subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, check=True
        )
        return result.stdout.decode("utf-8").strip()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, message):
        self.git("add", "--all")
        self.git("-c", "commit.gpgSign=false", "commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def cli(self, base=None, head=None, repository=None, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(repository or self.root),
             "--base=" + (base or self.base), "--head=" + (head or self.base)],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )

    def report(self, **kwargs):
        result = self.cli(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_explicit_commits_and_real_change(self):
        self.write("tool.py", "print('after')\n")
        head = self.commit("behavior change")
        data = self.report(base="main~1", head="main")
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual((data["base_commit"], data["head_commit"]), (self.base, head))
        self.assertEqual(data["commit_changes"], [{"status": "M", "path": "tool.py"}])

    def test_empty_diff_is_valid(self):
        data = self.report()
        self.assertEqual(data["commit_changes"], [])
        self.assertEqual(data["working_tree"], {"tracked": [], "untracked": []})

    def test_rename_delete_and_unusual_delimiters(self):
        old_name = "docs/old\tname\n.md"
        new_name = "docs/new\tname\n.md"
        self.write(old_name, "A stable paragraph for rename detection.\n" * 10)
        base = self.commit("add unusual filename")
        self.git("mv", "--", old_name, new_name)
        self.git("rm", "--", "tool.py")
        data = self.report(base=base, head=self.commit("rename and delete"))
        renamed = next(row for row in data["commit_changes"] if row["status"].startswith("R"))
        self.assertEqual((renamed["old_path"], renamed["path"]), (old_name, new_name))
        self.assertIn({"status": "D", "path": "tool.py"}, data["commit_changes"])

    def test_dirty_and_untracked_are_separate_from_commit_diff(self):
        self.write("tool.py", "print('committed')\n")
        head = self.commit("change")
        self.write("tool.py", "print('dirty')\n")
        self.write("scratch/new.md", "untracked\n")
        data = self.report(head=head)
        self.assertEqual(data["commit_changes"], [{"status": "M", "path": "tool.py"}])
        self.assertEqual(data["working_tree"]["tracked"], [{"status": " M", "path": "tool.py"}])
        self.assertEqual(data["working_tree"]["untracked"], [{"status": "??", "path": "scratch/new.md"}])

    def test_dirty_staged_rename_uses_old_and_new_paths(self):
        self.git("mv", "README.md", "Read Me.md")
        tracked = self.report()["working_tree"]["tracked"]
        self.assertEqual(tracked, [{"status": "R ", "path": "Read Me.md", "old_path": "README.md"}])

    def test_candidates_are_head_tree_suggestions(self):
        self.git("mv", "docs/usage.md", "docs/cli.md")
        self.write("docs/dirty.md", "untracked, not part of head\n")
        # Commit only the rename, leaving the new guide untracked.
        self.git("-c", "commit.gpgSign=false", "commit", "-m", "rename guide")
        data = self.report(head="HEAD")
        suggestions = data["candidate_documentation_paths"]
        self.assertEqual(data["candidate_documentation_basis"], "head_tree_conventions_only")
        self.assertEqual({row["path"] for row in suggestions}, {
            "README.md", "docs/cli.md", "CONTRIBUTING.rst", "CHANGELOG.md",
        })
        self.assertTrue(all(row["reason"] for row in suggestions))

    def test_unicode_survives_ascii_process_locale(self):
        self.write("docs/使用方法.md", "文本\n")
        head = self.commit("unicode")
        self.write("资料.txt", "untracked\n")
        env = {**os.environ, "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
        data = self.report(head=head, env=env)
        self.assertEqual(data["commit_changes"], [{"status": "A", "path": "docs/使用方法.md"}])
        self.assertIn({"status": "??", "path": "资料.txt"}, data["working_tree"]["untracked"])

    def test_non_utf8_names_have_lossless_base64_instead_of_replacement(self):
        raw_path = b"docs/raw-\xff.md"

        def git_input(args, raw):
            return subprocess.run(["git", *args], cwd=self.root, input=raw,
                                  capture_output=True, check=True).stdout.strip()

        # Store raw bytes directly in Git objects; some filesystems reject them.
        blob = git_input(["hash-object", "-w", "--stdin"], b"raw-name fixture\n")
        docs_tree = git_input(["mktree", "-z"], b"100644 blob " + blob + b"\traw-\xff.md\0")
        tree = git_input(["mktree", "-z"], b"040000 tree " + docs_tree + b"\tdocs\0")
        head = git_input(["commit-tree", tree.decode("ascii"), "-p", self.base, "-m", "raw path"], b"")
        data = self.report(head=head.decode("ascii"))
        expected = base64.b64encode(raw_path).decode("ascii")
        self.assertIn({"status": "A", "path": None, "path_bytes_base64": expected}, data["commit_changes"])
        suggestion = next(row for row in data["candidate_documentation_paths"] if row["path"] is None)
        self.assertEqual(suggestion["path_bytes_base64"], expected)

    def test_closed_stdout_pipe_returns_io_error_without_shutdown_traceback(self):
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), str(self.root), "--base", self.base,
             "--head", self.base],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        process.stdout.close()
        stderr = process.communicate()[1].decode("utf-8", errors="replace")
        self.assertEqual(process.returncode, 2, stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("Exception ignored", stderr)
        self.assertNotIn("BrokenPipeError", stderr)

    def test_closed_stdout_descriptor_returns_io_error_without_shutdown_traceback(self):
        wrapper = (
            "import os, runpy, sys; script, repo, base = sys.argv[1:4]; os.close(1); "
            "sys.argv = [script, repo, '--base', base, '--head', base]; "
            "runpy.run_path(script, run_name='__main__')"
        )
        process = subprocess.run(
            [sys.executable, "-c", wrapper, str(SCRIPT), str(self.root), self.base],
            capture_output=True,
        )
        stderr = process.stderr.decode("utf-8", errors="replace")
        self.assertEqual(process.returncode, 2, stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("Exception ignored", stderr)
        self.assertNotIn("OSError", stderr)

    def test_invalid_revisions_fail_without_json_or_traceback(self):
        for revision in ("missing-commit", "--help", "--output=intrusion", "HEAD:tool.py", "HEAD..HEAD"):
            with self.subTest(revision=revision):
                result = self.cli(base=revision)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "intrusion").exists())

    def test_invalid_head_also_fails(self):
        result = self.cli(head="--all")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_unborn_missing_and_non_repository_fail(self):
        empty = Path(self.tmp.name) / "unborn"
        empty.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(empty)], check=True, capture_output=True)
        ordinary = Path(self.tmp.name) / "ordinary"
        ordinary.mkdir()
        for directory in (empty, ordinary, Path(self.tmp.name) / "missing"):
            with self.subTest(directory=directory.name):
                result = self.cli(repository=directory, base="HEAD", head="HEAD")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)

    def test_rejects_nested_folder_to_keep_paths_repository_relative(self):
        result = self.cli(repository=self.root / "docs")
        self.assertEqual(result.returncode, 2)

    def test_source_and_git_state_unchanged_even_with_external_diff_config(self):
        self.write("tool.py", "print('committed')\n")
        head = self.commit("committed")
        self.write("tool.py", "print('dirty')\n")
        self.write("untracked.txt", "private scratch\n")
        self.git("config", "diff.external", "definitely-not-a-command")
        before = {str(path.relative_to(self.root)): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        self.report(head=head)
        after = {str(path.relative_to(self.root)): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(after, before)

    def test_helper_works_when_skill_is_copied_without_siblings(self):
        import shutil

        target = Path(self.tmp.name) / "installed" / "workflow-docs-sync"
        shutil.copytree(SCRIPT.parents[1], target)
        result = subprocess.run(
            [sys.executable, str(target / "scripts/change_manifest.py"), str(self.root),
             "--base", self.base, "--head", self.base],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["commit_changes"], [])

    def test_every_git_call_forbids_lazy_fetch_and_optional_index_updates(self):
        from unittest import mock

        spec = importlib.util.spec_from_file_location("change_manifest", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = subprocess.run
        with mock.patch.object(module.subprocess, "run", wraps=original) as run:
            module.change_manifest(self.root, self.base, self.base)
        for call in run.call_args_list:
            self.assertIn("--no-lazy-fetch", call.args[0])
            self.assertEqual(call.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")

    def test_inherited_git_directory_cannot_redirect_repository(self):
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(other)], check=True, capture_output=True)
        env = {**os.environ, "GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other)}
        data = self.report(env=env)
        self.assertEqual(data["head_commit"], self.base)


class GitParsingTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location("change_manifest", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_rejects_truncated_nul_records(self):
        module = self.module()
        for raw in (b"R100\0old\0", b"D\0missing-terminator", b"M\0"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                module.parse_commit_changes(raw)
        with self.assertRaises(ValueError):
            module.parse_working_tree(b"R  new\0")

    def test_copy_and_raw_old_name_round_trip(self):
        module = self.module()
        data = module.parse_commit_changes(b"C100\0old-\xff\0new.md\0")
        self.assertEqual(data, [{"status": "C100", "path": "new.md", "old_path": None,
                                 "old_path_bytes_base64": "b2xkLf8="}])
        tracked = module.parse_working_tree(b"R  new.md\0old-\xff\0")["tracked"]
        self.assertEqual(tracked[0]["old_path_bytes_base64"], "b2xkLf8=")


if __name__ == "__main__":
    unittest.main()
