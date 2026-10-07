# SPDX-License-Identifier: AGPL-3.0-only
"""The workflows follow edbfi-ci's privileged-job rule (design/security.md).

A job that references a secret other than GITHUB_TOKEN runs only inline shell:
no actions, containers or services, and when it can be dispatched, only on
main (named, or as the default branch, which is main here). Every workflow here
has one job, so these line checks read whole files; edbfi-ci's privileged-jobs
hook is the full check.
"""
from pathlib import Path
import re
import unittest

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
SECRET = re.compile(r"\bsecrets\s*(\.\s*(?!github_token\b)\w|\[)", re.IGNORECASE)
ACTION_KEYS = re.compile(r"^\s*(-\s+)?(uses|container|services)\s*:", re.MULTILINE)
MAIN_ONLY = "github.ref == 'refs/heads/main'"
# immortality.yml's bytes are shared with edbfi/base-image (default branch
# `workflows`), so it names the default branch instead of main.
DEFAULT_BRANCH_ONLY = "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"


def workflow(name):
    return (WORKFLOWS / name).read_text()


class PrivilegedJobTests(unittest.TestCase):
    def test_each_workflow_has_one_job(self):
        for path in WORKFLOWS.glob("*.yml"):
            jobs = path.read_text().split("\njobs:\n", 1)[1]
            self.assertEqual(len(re.findall(r"^  [\w-]+:", jobs, re.MULTILINE)), 1, path.name)

    def test_jobs_with_secrets_run_only_shell_on_main(self):
        privileged = [path for path in WORKFLOWS.glob("*.yml") if SECRET.search(path.read_text())]
        self.assertIn(WORKFLOWS / "sync-hotio.yml", privileged)
        for path in privileged:
            text = path.read_text()
            self.assertEqual(ACTION_KEYS.findall(text), [], path.name)
            self.assertTrue(f"if: {MAIN_ONLY}" in text or f"if: {DEFAULT_BRANCH_ONLY}" in text, path.name)

    def test_immortality_keeps_the_schedules_alive_from_the_default_branch(self):
        text = workflow("immortality.yml")
        self.assertIn(f"if: {DEFAULT_BRANCH_ONLY}", text)
        self.assertIn("GITHUB_TOKEN: ${{ secrets.IMMORTALITY_TOKEN }}", text)
        self.assertIn("REPOS: ${{ github.repository }}", text)
        self.assertIn('sha256sum -c -', text)

    def test_watcher_holds_no_secret_and_runs_only_on_main(self):
        text = workflow("watch-hotio.yml")
        self.assertIsNone(SECRET.search(text))
        self.assertIn(f"if: {MAIN_ONLY}", text)
        self.assertIn('gh workflow run sync-hotio.yml --repo "$GITHUB_REPOSITORY" --ref main', text)

    def test_sync_runs_this_repository_at_the_triggering_commit(self):
        text = workflow("sync-hotio.yml")
        self.assertIn('"$GITHUB_SHA"', text)
        self.assertNotIn("persist-credentials", text)
        self.assertNotIn("extraheader", text)


if __name__ == "__main__":
    unittest.main()
