#!/usr/bin/env python3
"""Exercise the workflow's embedded Git synchronization logic locally."""

import os
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

REPOSITORY_WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "mirror-gitlab-main.yml"
ARTIFACT_WORKFLOW = Path(__file__).with_name("mirror-gitlab-main.yml")
WORKFLOW = REPOSITORY_WORKFLOW if REPOSITORY_WORKFLOW.exists() else ARTIFACT_WORKFLOW
TEXT = WORKFLOW.read_text(encoding="utf-8")
MATCH = re.search(r"(?m)^        run: \|\n((?:          .*\n|\n)+)", TEXT)
if not MATCH:
    raise RuntimeError("Could not locate embedded workflow shell")
SCRIPT = "\n".join(line[10:] if line.startswith("          ") else "" for line in MATCH.group(1).splitlines()) + "\n"


def git(*args, cwd=None, check=True):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


class MirrorWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.git"
        self.target = self.root / "target.git"
        git("init", "--bare", "--initial-branch=main", str(self.source))
        git("init", "--bare", "--initial-branch=main", str(self.target))
        self.work = self.root / "work"
        git("init", str(self.work))
        git("-C", str(self.work), "config", "user.name", "Fixture")
        git("-C", str(self.work), "config", "user.email", "fixture@example.invalid")
        (self.work / "tracked.txt").write_text("base\n")
        git("-C", str(self.work), "add", "tracked.txt")
        git("-C", str(self.work), "commit", "-m", "base")
        git("-C", str(self.work), "branch", "-M", "main")
        git("-C", str(self.work), "remote", "add", "source", str(self.source))
        git("-C", str(self.work), "remote", "add", "target", str(self.target))
        git("-C", str(self.work), "push", "source", "main:refs/heads/main")
        git("-C", str(self.work), "push", "target", "main:refs/heads/main")
        self.base = self.head("source")

    def tearDown(self):
        self.tmp.cleanup()

    def head(self, remote):
        return git("--git-dir", str(getattr(self, remote)), "rev-parse", "refs/heads/main").stdout.strip()

    def commit(self, message, content):
        (self.work / "tracked.txt").write_text(content)
        git("-C", str(self.work), "commit", "-am", message)
        return git("-C", str(self.work), "rev-parse", "HEAD").stdout.strip()

    def refs(self, namespace):
        return git(
            "--git-dir",
            str(self.target),
            "for-each-ref",
            namespace,
            "--format=%(refname) %(objectname)",
        ).stdout

    def run_workflow(self, *, source_exists=True, target_exists=True, repository="tbnhan/codex-lb", branch="main"):
        env = os.environ.copy()
        env.update(
            {
                "GITLAB_SYNC_SSH_KEY": "fixture-key-not-used",
                "SOURCE_URL": str(self.source),
                "TARGET_URL": str(self.target),
                "SOURCE_REF": "refs/heads/main",
                "TARGET_REF": "refs/heads/main",
                "GITLAB_HOST_KEY": "fixture",
                "GITHUB_REPOSITORY": repository,
                "GITHUB_REF": f"refs/heads/{branch}",
                "GITHUB_STEP_SUMMARY": str(self.root / "summary.md"),
                "HOME": str(self.root / "home"),
                "SSH_AUTH_SOCK": str(self.root / "agent.sock"),
            }
        )
        script = SCRIPT
        # Test-only substitutions skip SSH setup and cleanup; the Git logic is unchanged.
        start = script.index('eval "$(ssh-agent -s)"')
        end = script.index('git init --quiet "$temp_dir/repo"')
        script = script[:start] + script[end:]
        cleanup = """            if [[ "$agent_started" == 1 ]]; then
              ssh-agent -k >/dev/null 2>&1 || true
            fi
"""
        script = script.replace(cleanup, "")
        if not source_exists:
            git("--git-dir", str(self.source), "update-ref", "-d", "refs/heads/main")
        if not target_exists:
            git("--git-dir", str(self.target), "update-ref", "-d", "refs/heads/main")
        return subprocess.run(
            ["bash", "-euo", "pipefail", "-c", script],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_ssh_configuration_uses_agent_identity_and_pinned_host(self):
        command_match = re.search(r'^          export GIT_SSH_COMMAND="([^"]+)"$', TEXT, re.MULTILINE)
        host_key_match = re.search(r"^          GITLAB_HOST_KEY: (.+)$", TEXT, re.MULTILINE)
        self.assertIsNotNone(command_match)
        self.assertIsNotNone(host_key_match)

        ssh_dir = self.root / "ssh"
        ssh_dir.mkdir()
        known_hosts = ssh_dir / "known_hosts"
        pinned_host_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAfuCHKVTjquxvt6CM6tdG4SLp1Btn/nOeHHE5UOzRdf"
        self.assertEqual(host_key_match.group(1), pinned_host_key)
        known_hosts.write_text(f"gitlab.com {pinned_host_key}\n", encoding="utf-8")
        agent_socket = str(ssh_dir / "agent.sock")
        ssh_command = (
            command_match.group(1).replace("$temp_dir", str(self.root)).replace("$SSH_AUTH_SOCK", agent_socket)
        )
        effective = subprocess.run(
            [*shlex.split(ssh_command), "-G", "git@gitlab.com"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        options = dict(line.split(None, 1) for line in effective.splitlines() if " " in line)
        self.assertEqual(options["identityagent"], agent_socket)
        self.assertEqual(options["identitiesonly"], "no")
        self.assertEqual(options["identityfile"], "none")
        self.assertEqual(options["stricthostkeychecking"], "true")
        self.assertEqual(options["userknownhostsfile"], str(known_hosts))
        self.assertEqual(known_hosts.read_text(encoding="utf-8"), f"gitlab.com {pinned_host_key}\n")
        self.assertFalse(Path(agent_socket).exists())

    def test_behind_target_is_fast_forwarded(self):
        expected = self.commit("advance source", "advanced\n")
        git("-C", str(self.work), "push", "source", "main:refs/heads/main")
        proc = self.run_workflow()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.head("target"), expected)
        self.assertIn(expected, (self.root / "summary.md").read_text())

    def test_equal_sha_is_noop(self):
        proc = self.run_workflow()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.head("target"), self.base)
        self.assertIn("already up to date", (self.root / "summary.md").read_text())

    def test_target_ahead_is_rejected_without_modification(self):
        self.commit("target-only", "target\n")
        git("-C", str(self.work), "push", "target", "main:refs/heads/main")
        before = self.head("target")
        proc = self.run_workflow()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("target main is ahead or diverged", proc.stderr)
        self.assertEqual(self.head("target"), before)

    def test_diverged_sibling_history_is_rejected_without_modification(self):
        source_work = self.root / "source-work"
        git("clone", str(self.source), str(source_work))
        self.configure(source_work)
        (source_work / "tracked.txt").write_text("source sibling\n")
        git("-C", str(source_work), "commit", "-am", "source sibling")
        source_sha = git("-C", str(source_work), "rev-parse", "HEAD").stdout.strip()
        git("-C", str(source_work), "push", "origin", "HEAD:refs/heads/main")

        target_work = self.root / "target-work"
        git("clone", str(self.target), str(target_work))
        self.configure(target_work)
        (target_work / "tracked.txt").write_text("target sibling\n")
        git("-C", str(target_work), "commit", "-am", "target sibling")
        target_sha = git("-C", str(target_work), "rev-parse", "HEAD").stdout.strip()
        git("-C", str(target_work), "push", "origin", "HEAD:refs/heads/main")

        proc = self.run_workflow()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("target main is ahead or diverged", proc.stderr)
        self.assertEqual(self.head("source"), source_sha)
        self.assertEqual(self.head("target"), target_sha)

    def configure(self, path):
        git("-C", str(path), "config", "user.name", "Fixture")
        git("-C", str(path), "config", "user.email", "fixture@example.invalid")

    def test_missing_source_fails(self):
        proc = self.run_workflow(source_exists=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("couldn't find remote ref", proc.stderr)

    def test_missing_target_fails_while_source_exists(self):
        proc = self.run_workflow(target_exists=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Target main is missing", proc.stderr)
        self.assertEqual(self.head("source"), self.base)

    def test_non_main_branch_and_wrong_repository_are_rejected(self):
        for repository, branch in (("tbnhan/codex-lb", "dev"), ("someone-else/codex-lb", "main")):
            with self.subTest(repository=repository, branch=branch):
                before = self.head("target")
                proc = self.run_workflow(repository=repository, branch=branch)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("Workflow is restricted", proc.stderr)
                self.assertEqual(self.head("target"), before)

    def test_dev_and_tags_remain_unchanged(self):
        target_work = self.root / "target-refs"
        git("clone", str(self.target), str(target_work))
        self.configure(target_work)
        (target_work / "tracked.txt").write_text("destination dev\n")
        git("-C", str(target_work), "commit", "-am", "destination dev")
        git("-C", str(target_work), "push", "origin", "HEAD:refs/heads/dev")
        git("-C", str(target_work), "tag", "destination-tag")
        git("-C", str(target_work), "push", "origin", "refs/tags/destination-tag")

        git("-C", str(self.work), "branch", "dev")
        git("-C", str(self.work), "tag", "source-tag")
        git("-C", str(self.work), "push", "source", "refs/heads/dev")
        git("-C", str(self.work), "push", "source", "refs/tags/source-tag")
        before_heads = self.refs("refs/heads")
        before_tags = self.refs("refs/tags")

        expected = self.commit("main-only", "main changed\n")
        git("-C", str(self.work), "push", "source", "main:refs/heads/main")
        proc = self.run_workflow()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        after_heads = self.refs("refs/heads")
        after_tags = self.refs("refs/tags")
        self.assertEqual(self.head("target"), expected)
        expected_heads = before_heads.replace(f"refs/heads/main {self.base}", f"refs/heads/main {expected}")
        self.assertEqual(after_heads, expected_heads)
        self.assertEqual(after_tags, before_tags)


if __name__ == "__main__":
    unittest.main()
