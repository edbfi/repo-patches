# SPDX-License-Identifier: AGPL-3.0-only
"""The workflows follow edbfi-ci's privileged-job rule (design/security.md).

A job that references a secret other than GITHUB_TOKEN runs only inline shell:
no actions, containers or services, and when it can be dispatched, only on
main. These line checks read each job's block, and the workflow level above
``jobs:`` holds no secret; edbfi-ci's privileged-jobs hook is the full check.
"""
from pathlib import Path
import re
import unittest

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
SECRET = re.compile(r"\bsecrets\s*(\.\s*(?!github_token\b)\w|\[)", re.IGNORECASE)
ACTION_KEYS = re.compile(r"^\s*(-\s+)?(uses|container|services)\s*:", re.MULTILINE)
MAIN_ONLY = "github.ref == 'refs/heads/main'"


def workflow(name):
    return (WORKFLOWS / name).read_text()


def jobs(path):
    """The workflow level above ``jobs:``, and each job's lines by job id.

    A job starts at a two-space ``id:`` line under ``jobs:``; deeper keys are
    indented further, so they stay inside their job.
    """
    head, _, body = path.read_text().partition("\njobs:\n")
    blocks = re.split(r"^(?=  [\w-]+:)", body, flags=re.MULTILINE)
    return head, {b.split(":", 1)[0].strip(): b for b in blocks if b.strip()}


class PrivilegedJobTests(unittest.TestCase):
    def test_secrets_are_only_used_inside_jobs(self):
        for path in WORKFLOWS.glob("*.yml"):
            head, by_id = jobs(path)
            self.assertTrue(by_id, path.name)
            self.assertIsNone(SECRET.search(head), path.name)

    def test_jobs_with_secrets_run_only_shell_on_main(self):
        privileged = [
            (path.name, job_id, block)
            for path in WORKFLOWS.glob("*.yml")
            for job_id, block in jobs(path)[1].items()
            if SECRET.search(block)
        ]
        self.assertIn("sync-hotio.yml", [name for name, _, _ in privileged])
        for name, job_id, block in privileged:
            self.assertEqual(ACTION_KEYS.findall(block), [], f"{name}: {job_id}")
            self.assertIn(f"if: {MAIN_ONLY}", block, f"{name}: {job_id}")

    def test_job_blocks_split_at_job_ids_only(self):
        _, by_id = jobs(WORKFLOWS / "ci.yml")
        self.assertEqual(list(by_id), ["checks", "ci-ok"])

    def test_immortality_keeps_the_schedules_alive(self):
        text = workflow("immortality.yml")
        self.assertIn("# Copy as .github/workflows/immortality.yml (design/watchdog.md).", text)
        self.assertIn(f"if: {MAIN_ONLY}", text)
        self.assertIn("GITHUB_TOKEN: ${{ secrets.IMMORTALITY_TOKEN }}", text)
        self.assertIn("REPOS: ${{ github.repository }}", text)
        # The script is pinned to a commit and checked against a pinned SHA-256.
        self.assertRegex(text, r"\n +SCRIPT_URL: https://raw\.githubusercontent\.com/[\w-]+/[\w-]+/[0-9a-f]{40}/")
        self.assertRegex(text, r"\n +SCRIPT_SHA256: [0-9a-f]{64}\n")
        self.assertIn('echo "${SCRIPT_SHA256}  ${script}" | sha256sum -c -', text)

    def test_base_image_immortality_differs_only_in_header_and_branch_guard(self):
        # base-image's default branch is `workflows`, so its copy names the
        # default branch instead of main; everything else stays in step.
        ours = workflow("immortality.yml")
        theirs = (WORKFLOWS.parent.parent / "mirrors/base-image/immortality.yml").read_text()
        header = ("# SPDX-License-Identifier: AGPL-3.0-only\n"
                  "# Copy as .github/workflows/immortality.yml (design/watchdog.md).\n")
        self.assertTrue(ours.startswith(header))
        default_branch = "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"
        self.assertEqual(ours[len(header):].replace(f"if: {MAIN_ONLY}", f"if: {default_branch}"), theirs)

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
