# SPDX-License-Identifier: AGPL-3.0-only
"""The workflows follow edbfi-ci's privileged-job rule (design/security.md).

A job that references a secret other than GITHUB_TOKEN runs only inline shell:
no actions, containers or services, and when it can be dispatched, only on
main. A workflow that runs only on pull_request can't be dispatched, so its
job instead admits only Dependabot's own same-repository PRs (edbfi-ci's
design/auto-merge.md rule 3). These line checks read each job's block, and
the workflow level above ``jobs:`` holds no secret; edbfi-ci's
privileged-jobs hook is the full check.
"""
from pathlib import Path
import re
import unittest

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
SECRET = re.compile(r"\bsecrets\s*(\.\s*(?!github_token\b)\w|\[)", re.IGNORECASE)
ACTION_KEYS = re.compile(r"^\s*(-\s+)?(uses|container|services)\s*:", re.MULTILINE)
MAIN_ONLY = "github.ref == 'refs/heads/main'"
DEPENDABOT_ONLY = ("github.event.pull_request.user.login == 'dependabot[bot]' && "
                   "github.event.pull_request.head.repo.full_name == github.repository")
EVENT = re.compile(r"  ([\w-]+):(?:\s|$)")


def workflow(name):
    return (WORKFLOWS / name).read_text()


JOB_ID = re.compile(r"^  ([\w-]+):\s*(#.*)?$")
ANCHOR_OR_ALIAS = re.compile(r"(?:^\s*-\s+|:\s+)[&*][\w-]+(?=\s|$)", re.MULTILINE)


def split_jobs(text, name):
    """The workflow-level lines and each job's lines by job id.

    Only the block style these workflows use is accepted: ``jobs:`` alone at
    column 0, each job id indented two spaces, everything inside a job
    indented further, and no YAML anchors or aliases (an aliased step list
    would hide its ``uses:`` from the job's text). A top-level key after
    ``jobs:`` is workflow level again. Any other shape fails here instead of
    being checked as if it had been split correctly.
    """
    if ANCHOR_OR_ALIAS.search(text):
        raise AssertionError(f"{name}: YAML anchors and aliases are not supported")
    head, by_id, current, in_jobs = [], {}, None, False
    for line in text.splitlines(keepends=True):
        bare = line.strip()
        if not line[:1].isspace() and bare and not bare.startswith("#"):
            in_jobs, current = bare == "jobs:", None
            if line.startswith("jobs:") and not in_jobs:
                raise AssertionError(f"{name}: write jobs: in block style")
            if not in_jobs:
                head.append(line)
            continue
        if not in_jobs:
            head.append(line)
        elif not bare or bare.startswith("#"):
            if current is not None:
                by_id[current] += line
        elif match := JOB_ID.match(line):
            current = match.group(1)
            by_id[current] = line
        elif line.startswith("   ") and current is not None:
            by_id[current] += line
        else:
            raise AssertionError(f"{name}: job ids must be indented two spaces: {bare}")
    return "".join(head), by_id


def jobs(path):
    return split_jobs(path.read_text(), path.name)


def triggers(head):
    """The events of a block-style ``on:``; any other shape gives none, so
    the job falls back to the main-only check. The block runs to the next
    top-level key: blank, indented and comment lines (column 0 included)
    stay in it, and every other line at indent 2 must be a plain event key."""
    blocks = re.findall(r"^on:[ \t]*\n((?:(?:[ \t].*|#.*)?\n)*)", head, re.MULTILINE)
    if len(blocks) != 1 or len(re.findall(r"^on\s*:", head, re.MULTILINE)) != 1:
        return set()
    keys = [line for line in blocks[0].splitlines()
            if re.match(r"  [^\s#]", line)]
    events = [EVENT.match(line) for line in keys]
    if not all(events):
        return set()
    return {event.group(1) for event in events}


class PrivilegedJobTests(unittest.TestCase):
    def test_secrets_are_only_used_inside_jobs(self):
        for path in WORKFLOWS.glob("*.yml"):
            head, by_id = jobs(path)
            self.assertTrue(by_id, path.name)
            self.assertIsNone(SECRET.search(head), path.name)

    def test_jobs_with_secrets_run_only_shell_on_main(self):
        privileged = [
            (path.name, triggers(head), job_id, block)
            for path in WORKFLOWS.glob("*.yml")
            for head, by_id in [jobs(path)]
            for job_id, block in by_id.items()
            if SECRET.search(block)
        ]
        self.assertIn("sync-hotio.yml", [name for name, _, _, _ in privileged])
        for name, events, job_id, block in privileged:
            self.assertEqual(ACTION_KEYS.findall(block), [], f"{name}: {job_id}")
            guard = DEPENDABOT_ONLY if events == {"pull_request"} else MAIN_ONLY
            # The job's own if:, not a step's or a comment.
            self.assertRegex(block, rf"(?m)^    if: {re.escape(guard)}", f"{name}: {job_id}")

    def test_only_a_pull_request_only_workflow_skips_the_main_guard(self):
        self.assertEqual(triggers("on:\n  pull_request:\n    types: [opened]\njobs:\n"),
                         {"pull_request"})
        self.assertEqual(triggers("on:\n  pull_request:\n  workflow_dispatch:\n"),
                         {"pull_request", "workflow_dispatch"})
        self.assertEqual(triggers("on:\n  pull_request:\n# note\n  # note\n  workflow_dispatch:\njobs:\n"),
                         {"pull_request", "workflow_dispatch"})
        twice = "on:\n  pull_request:\njobs:\non:\n  workflow_dispatch:\n"
        unread = ["on:\n  pull_request:\n" + key + "\n"
                  for key in ("  workflow_dispatch :", '  "workflow_dispatch":', "  ? workflow_dispatch")]
        for text in ("on: pull_request\n", "on: [pull_request]\n", "true:\n  pull_request:\n", twice, *unread):
            with self.subTest(text=text):
                self.assertEqual(triggers(text), set())

    def test_job_blocks_split_at_job_ids_only(self):
        _, by_id = jobs(WORKFLOWS / "ci.yml")
        self.assertEqual(list(by_id), ["checks", "ci-ok"])

    def test_the_split_rejects_shapes_it_cannot_check(self):
        four_spaces = "on: push\njobs:\n    a:\n      runs-on: x\n    b:\n      runs-on: x\n"
        aliased = (
            "on: push\njobs:\n  a:\n    steps: &shared\n      - uses: x/y@z\n"
            "  b:\n    steps: *shared\n"
        )
        flow = "on: push\njobs: {a: {runs-on: x}}\n"
        for text in (four_spaces, aliased, flow):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                _ = split_jobs(text, "fixture.yml")

    def test_workflow_level_keys_after_jobs_stay_workflow_level(self):
        head, by_id = split_jobs(
            "on: push\njobs:\n  a:\n    runs-on: x\n"
            "env:\n  TOKEN: ${{ secrets.PERSONAL_TOKEN }}\n",
            "fixture.yml",
        )
        self.assertEqual(list(by_id), ["a"])
        self.assertIsNotNone(SECRET.search(head))
        self.assertIsNone(SECRET.search(by_id["a"]))

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
