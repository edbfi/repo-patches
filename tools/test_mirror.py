import base64
import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import mirror
from mirror import BOT_EMAIL, BOT_NAME

HUMAN = ("Hotio", "hotio@example.com")
BOT = (BOT_NAME, BOT_EMAIL)

CALL_BUILD = b"""name: call-build
on:
  push:
jobs:
  call:
    uses: hotio/base/.github/workflows/build-on-call.yml@workflows
    secrets: inherit
"""
CALL_UPDATE = b"""name: call-update
on:
  schedule:
    - cron:  '0 * * * *'
jobs:
  call:
    uses: hotio/base/.github/workflows/update-on-call.yml@workflows
    secrets: inherit
"""
BUILD_ON_CALL = b"""name: build-on-call
on:
  workflow_call:
jobs:
  build:
    steps:
      - run: echo "meta-docs-url=https://hotio.dev/containers/${NAME}" >> $GITHUB_OUTPUT
  notify:
    steps:
      - run: curl "${DISCORD_WEBHOOK}"
"""
MAINTENANCE = b"""name: maintenance
jobs:
  do-work:
    steps:
      - run: |
          curl -fsSL https://raw.githubusercontent.com/hotio/base/refs/heads/alpinevpn/build.sh > build.sh
          #curl -fsSL https://raw.githubusercontent.com/hotio/base/refs/heads/workflows/x.yml > x.yml
"""
INIT = b"""#!/command/with-contenv bash
echo -ne "
$(figlet "hotio")
Donate:        https://hotio.dev/donate
Documentation: https://hotio.dev${app_uri}
Support:       https://hotio.dev/discord
Image:         ${image}
"
usermod -o -u "${PUID}" hotio > /dev/null
"""
TBODY = b'<tbody id="tags-table-body">\n<tr><td>%s</td></tr>\n</tbody>'


def git(cwd, *args, env=None, data=None):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          env=env, input=data).stdout.decode().strip()


def commit(bare, branch, files, message="change", who=HUMAN, parent="branch"):
    """Commit `files` (path -> bytes, None deletes) on `branch` of a bare repository."""
    with tempfile.TemporaryDirectory() as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"),
                   GIT_AUTHOR_NAME=who[0], GIT_AUTHOR_EMAIL=who[1],
                   GIT_COMMITTER_NAME=who[0], GIT_COMMITTER_EMAIL=who[1])
        if parent == "branch":
            probe = subprocess.run(["git", "-C", str(bare), "rev-parse", "-q", "--verify",
                                    f"refs/heads/{branch}"], capture_output=True)
            parent = probe.stdout.decode().strip() or None
        if parent:
            git(bare, "read-tree", parent, env=env)
        else:
            git(bare, "read-tree", "--empty", env=env)
        for path, content in files.items():
            if content is None:
                git(bare, "update-index", "--force-remove", path, env=env)
                continue
            sha = git(bare, "hash-object", "-w", "--stdin", data=content)
            mode = "100755" if path.endswith("/run") else "100644"
            git(bare, "update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}", env=env)
        tree = git(bare, "write-tree", env=env)
        args = ["commit-tree", tree, "-m", message] + (["-p", parent] if parent else [])
        sha = git(bare, *args, env=env)
        git(bare, "update-ref", f"refs/heads/{branch}", sha)
        return sha


def head(bare, branch):
    return git(bare, "rev-parse", f"refs/heads/{branch}")


def show(bare, rev, path):
    return subprocess.run(["git", "-C", str(bare), "show", f"{rev}:{path}"],
                          capture_output=True, check=True).stdout


def exists(bare, rev, path):
    return subprocess.run(["git", "-C", str(bare), "cat-file", "-e", f"{rev}:{path}"],
                          capture_output=True).returncode == 0


class MirrorFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.github = Path(self.temp.name) / "github"
        self.work = Path(self.temp.name) / "work"
        self.bare = {}
        for name in ("hotio/base", "edbfi/base-image", "hotio/website", "edbfi/website"):
            path = self.github / f"{name}.git"
            path.mkdir(parents=True)
            git(path, "init", "--bare", "--quiet")
            self.bare[name] = path
        self.hotio, self.dest = self.bare["hotio/base"], self.bare["edbfi/base-image"]
        self.hweb, self.dweb = self.bare["hotio/website"], self.bare["edbfi/website"]
        commit(self.hotio, "workflows", {
            ".github/workflows/call-build.yml": CALL_BUILD,
            ".github/workflows/call-update.yml": CALL_UPDATE,
            ".github/workflows/build-on-call.yml": BUILD_ON_CALL,
            ".github/workflows/maintenance.yml": MAINTENANCE,
            "renovate.json": b"{}\n", "LICENSE": b"GPL\n"}, "workflows")
        for branch in ("alpinevpn", "noblevpn"):
            commit(self.hotio, branch, {
                ".github/workflows/call-build.yml": CALL_BUILD,
                ".github/workflows/call-update.yml": CALL_UPDATE,
                "root/etc/s6-overlay/s6-rc.d/init-setup/run": INIT,
                "meta.json": b'{"version": "1"}\n', "packages.txt": b"a=1\n"}, branch)
            commit(self.hotio, branch, {"packages.txt": b"a=2\n"}, "Modified: packages.txt", BOT)
        commit(self.hweb, "master", {
            ".github/workflows/deploy-pages.yml": b"name: Deploy Website\r\non:\r\n  push:\r\n",
            "renovate.json": b"{}\n", "mkdocs.yml": b"site_name: hotio.dev\n",
            "docs/CNAME": b"hotio.dev\n", "docs/index.md": b"hotio\n",
            "includes/wireguard.md": b"wg\n", "includes/annotations.md": b"notes\n",
            "docs/javascripts/tablesort.js": b"sort\n", "docs/javascripts/tagcopy.js": b"copy\n",
            "docs/stylesheets/extra-13.css": b"css\n", "docs/scripts/pullio.md": b"pullio\n",
            "docs/containers/caddy.md": b"hotio caddy\n" + TBODY % b"hotio" + b"\n",
            "docs/containers/caddy-tags.json": b'{"hotio": {}}\n',
            "docs/containers/radarr.md": b"radarr\n", "docs/containers/radarr-tags.json": b"{}\n"},
            "site")
        # Today's edbfi branches: diverged hand-made history.
        for branch in ("workflows", "alpinevpn", "noblevpn"):
            commit(self.dest, branch, {"README.md": b"old\n"}, "hand-made", ("edbfi", "e@example.com"))
        commit(self.dweb, "master", {
            "README.md": b"old\n",
            "docs/containers/caddy.md": b"old caddy page\n" + TBODY % b"edbfi release" + b"\n",
            "docs/containers/caddy-tags.json": b'{"release": {"commit_sha": "abc"}}\n',
            "docs/containers/qflood-tags.json": b'{"release": {"commit_sha": "def"}}\n'},
            "hand-made", ("edbfi", "e@example.com"))

    def sync(self, selection="", push=True, evidence=None):
        with contextlib.redirect_stderr(io.StringIO()):
            return mirror.run_sync(mirror.parse_selection(selection), self.work, push_changes=push,
                                   github=str(self.github), evidence=evidence)

    def watch(self):
        with contextlib.redirect_stderr(io.StringIO()):
            return mirror.run_watch(self.work, str(self.github))


class BaseImageTests(MirrorFixture):
    def test_each_branch_is_hotio_head_plus_one_bot_commit(self):
        results, failed = self.sync("base-image:workflows base-image:alpinevpn base-image:noblevpn")
        self.assertFalse(failed)
        self.assertEqual([r["status"] for r in results], ["pushed"] * 3)
        for branch in ("workflows", "alpinevpn", "noblevpn"):
            top = head(self.dest, branch)
            self.assertEqual(git(self.dest, "rev-parse", f"{top}^"), head(self.hotio, branch))
            self.assertEqual(git(self.dest, "rev-list", "--count", f"{head(self.hotio, branch)}..{top}"), "1")
            self.assertEqual(git(self.dest, "show", "-s", "--format=%an <%ae>|%cn <%ce>", top),
                             f"{BOT_NAME} <{BOT_EMAIL}>|{BOT_NAME} <{BOT_EMAIL}>")
            self.assertIn(f"Upstream: hotio/base@{head(self.hotio, branch)}",
                          git(self.dest, "show", "-s", "--format=%B", top))
            self.assertIn(b"uses: edbfi/base-image/.github/workflows/build-on-call.yml@workflows",
                          show(self.dest, top, ".github/workflows/call-build.yml"))
            self.assertIn(b"uses: edbfi/base-image/.github/workflows/update-on-call.yml@workflows",
                          show(self.dest, top, ".github/workflows/call-update.yml"))
            self.assertEqual(show(self.dest, top, "README.md"),
                             (mirror.MIRROR_FILES / "base-image/README.md").read_bytes())

    def test_workflows_adaptations_keep_notify_and_maintenance(self):
        self.sync("base-image:workflows")
        top = head(self.dest, "workflows")
        build = show(self.dest, top, ".github/workflows/build-on-call.yml")
        self.assertIn(b"https://web.edb.fi/containers/${NAME}", build)
        self.assertIn(b"  notify:", build)
        self.assertNotIn(b"permissions", build)
        maintenance = show(self.dest, top, ".github/workflows/maintenance.yml")
        self.assertEqual(maintenance.count(b"raw.githubusercontent.com/edbfi/base-image/refs/heads/"), 2)
        self.assertNotIn(b"edbfi/base/", maintenance)
        self.assertFalse(exists(self.dest, top, "renovate.json"))
        self.assertEqual(show(self.dest, top, ".github/workflows/pullfrog.yml"), mirror.PULLFROG.read_bytes())
        # The default branch carries the base-image immortality job, byte for byte,
        # guarded by the default branch (`workflows`), never by main.
        immortality = show(self.dest, top, ".github/workflows/immortality.yml")
        self.assertEqual(immortality, (mirror.MIRROR_FILES / "base-image/immortality.yml").read_bytes())
        self.assertIn(b"if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)\n",
                      immortality)
        self.assertNotIn(b"refs/heads/main", immortality)
        changed = git(self.dest, "diff", "--name-status", head(self.hotio, "workflows"), top).splitlines()
        self.assertEqual(sorted(changed), sorted([
            "M\t.github/workflows/build-on-call.yml", "M\t.github/workflows/call-build.yml",
            "M\t.github/workflows/call-update.yml", "M\t.github/workflows/maintenance.yml",
            "A\t.github/workflows/immortality.yml", "A\t.github/workflows/pullfrog.yml",
            "A\tREADME.md", "D\trenovate.json"]))

    def test_image_banner_matches_edbfi(self):
        self.sync("base-image:alpinevpn")
        top = head(self.dest, "alpinevpn")
        init = show(self.dest, top, "root/etc/s6-overlay/s6-rc.d/init-setup/run")
        self.assertIn(b'$(figlet "edbfi")\n'
                      b"Upstream:      https://hotio.dev/donate\n"
                      b"Documentation: https://web.edb.fi${app_uri}\n"
                      b"Support:       https://github.com/edbfi/$(jq -r '.app' <<< \"${IMAGE_STATS}\")/issues\n"
                      b"Image:         ${image}\n", init)
        self.assertIn(b'usermod -o -u "${PUID}" hotio', init)
        self.assertEqual(git(self.dest, "ls-tree", top, "root/etc/s6-overlay/s6-rc.d/init-setup/run").split()[0],
                         "100755")
        self.assertFalse(exists(self.dest, top, ".github/workflows/pullfrog.yml"))
        self.assertFalse(exists(self.dest, top, ".github/workflows/immortality.yml"))
        changed = git(self.dest, "diff", "--name-only", head(self.hotio, "alpinevpn"), top).splitlines()
        self.assertEqual(sorted(changed), [".github/workflows/call-build.yml", ".github/workflows/call-update.yml",
                                           "README.md", "root/etc/s6-overlay/s6-rc.d/init-setup/run"])

    def test_second_run_is_a_no_op(self):
        self.sync()
        before = {branch: head(self.dest, branch) for branch in ("workflows", "alpinevpn", "noblevpn")}
        results, failed = self.sync()
        self.assertFalse(failed)
        self.assertEqual({r["status"] for r in results}, {"unchanged"})
        self.assertEqual(before, {branch: head(self.dest, branch) for branch in before})

    def test_dry_run_never_pushes_and_writes_evidence(self):
        before = head(self.dest, "alpinevpn")
        evidence = Path(self.temp.name) / "evidence"
        results, failed = self.sync("base-image:alpinevpn", push=False, evidence=evidence)
        self.assertFalse(failed)
        self.assertEqual(results[0]["status"], "would push")
        self.assertEqual(head(self.dest, "alpinevpn"), before)
        self.assertIn(b'+$(figlet "edbfi")', (evidence / "base-image-alpinevpn.diff").read_bytes())
        self.assertTrue((evidence / "base-image-alpinevpn.log").is_file())

    def test_changed_hotio_layout_stops_without_pushing(self):
        commit(self.hotio, "alpinevpn", {"root/etc/s6-overlay/s6-rc.d/init-setup/run":
                                         INIT.replace(b"Support:       https://hotio.dev/discord\n", b"")})
        before = head(self.dest, "alpinevpn")
        results, failed = self.sync("base-image:alpinevpn")
        self.assertTrue(failed)
        self.assertIn("Hotio layout changed", results[0]["error"])
        self.assertEqual(head(self.dest, "alpinevpn"), before)

    def test_new_hotio_reference_is_refused(self):
        commit(self.hotio, "noblevpn", {"build.sh": b"docker pull ghcr.io/hotio/base:noblevpn\n"})
        results, failed = self.sync("base-image:noblevpn")
        self.assertTrue(failed)
        self.assertIn("still points at Hotio", results[0]["error"])

    def test_failed_workflows_branch_stops_image_branches_not_website(self):
        commit(self.hotio, "workflows", {".github/workflows/call-build.yml": b"jobs: {}\n"})
        results, failed = self.sync()
        self.assertTrue(failed)
        self.assertEqual([(r["branch"], r["status"]) for r in results],
                         [("workflows", "failed"), ("master", "pushed")])

    def test_bot_commit_landing_mid_sync_is_refetched(self):
        original = mirror.push
        calls = []

        def racing_push(repo, branch, candidate, dest_sha, env):
            calls.append(dest_sha)
            if len(calls) == 1:
                commit(self.dest, branch, {"packages.txt": b"a=3\n"}, "Modified: packages.txt", BOT)
            return original(repo, branch, candidate, dest_sha, env)

        with mock.patch.object(mirror, "push", racing_push):
            results, failed = self.sync("base-image:alpinevpn")
        self.assertFalse(failed)
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0], calls[1])
        self.assertEqual(results[0]["status"], "pushed")
        self.assertEqual(git(self.dest, "rev-parse", "alpinevpn^"), head(self.hotio, "alpinevpn"))

    def test_bot_commit_right_after_the_push_is_not_a_failure(self):
        original = mirror.push

        def push_then_bot(repo, branch, candidate, dest_sha, env):
            pushed = original(repo, branch, candidate, dest_sha, env)
            commit(self.dest, branch, {"packages.txt": b"a=4\n"}, "Modified: packages.txt [skip ci]", BOT)
            return pushed

        with mock.patch.object(mirror, "push", push_then_bot):
            results, failed = self.sync("base-image:alpinevpn base-image:noblevpn")
        self.assertFalse(failed)
        self.assertEqual([r["status"] for r in results], ["pushed", "pushed"])
        for branch in ("alpinevpn", "noblevpn"):
            self.assertEqual(git(self.dest, "rev-parse", f"{branch}^^"), head(self.hotio, branch))

    def test_destination_that_keeps_moving_gives_up(self):
        def always_racing(repo, branch, candidate, dest_sha, env):
            commit(self.dest, branch, {"packages.txt": os.urandom(8).hex().encode()}, "Modified", BOT)
            return mirror.git(repo, "push", f"--force-with-lease=refs/heads/{branch}:{dest_sha}", "dest",
                              f"{candidate}:refs/heads/{branch}", env=env, check=False).returncode == 0

        with mock.patch.object(mirror, "push", always_racing):
            results, failed = self.sync("base-image:alpinevpn")
        self.assertTrue(failed)
        self.assertIn("kept moving", results[0]["error"])

    def test_rejected_push_is_not_retried(self):
        hook = self.dest / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\necho rejected by test >&2\nexit 1\n")
        hook.chmod(0o755)
        before = head(self.dest, "alpinevpn")
        results, failed = self.sync("base-image:alpinevpn")
        self.assertTrue(failed)
        self.assertIn("was rejected", results[0]["error"])
        self.assertEqual(head(self.dest, "alpinevpn"), before)


class WebsiteTests(MirrorFixture):
    def test_site_is_hotio_plus_overlay_with_destination_tag_data(self):
        results, failed = self.sync("website:master")
        self.assertFalse(failed)
        top = head(self.dweb, "master")
        self.assertEqual(git(self.dweb, "rev-parse", f"{top}^"), head(self.hweb, "master"))
        self.assertEqual(show(self.dweb, top, "docs/containers/caddy-tags.json"),
                         b'{"release": {"commit_sha": "abc"}}\n')
        self.assertEqual(show(self.dweb, top, "docs/containers/qflood-tags.json"),
                         b'{"release": {"commit_sha": "def"}}\n')
        self.assertEqual(show(self.dweb, top, "docs/containers/zondarr-tags.json"), b"{}\n")
        caddy = show(self.dweb, top, "docs/containers/caddy.md")
        self.assertIn(TBODY % b"edbfi release", caddy)
        overlay = (mirror.OVERLAY / "docs/containers/caddy.md").read_bytes()
        self.assertEqual(caddy[:overlay.index(b'<tbody id="tags-table-body">')],
                         overlay[:overlay.index(b'<tbody id="tags-table-body">')])
        self.assertEqual(show(self.dweb, top, "docs/containers/zondarr.md"),
                         (mirror.OVERLAY / "docs/containers/zondarr.md").read_bytes())
        for gone in ("docs/containers/radarr.md", "docs/containers/radarr-tags.json",
                     "docs/scripts/pullio.md", "renovate.json"):
            self.assertFalse(exists(self.dweb, top, gone), gone)
        self.assertEqual(show(self.dweb, top, ".github/workflows/deploy-pages.yml"),
                         b"name: Deploy Website\r\non:\r\n  push:\r\n")
        self.assertEqual(show(self.dweb, top, "docs/CNAME").strip(), b"web.edb.fi")
        self.assertEqual(show(self.dweb, top, "README.md"), (mirror.MIRROR_FILES / "website/README.md").read_bytes())
        self.assertEqual(show(self.dweb, top, ".github/workflows/pullfrog.yml"), mirror.PULLFROG.read_bytes())
        self.assertFalse(exists(self.dweb, top, ".github/workflows/immortality.yml"))  # no schedule there

    def test_tag_update_during_sync_is_kept(self):
        original = mirror.push
        newer = b'{"release": {"commit_sha": "newer"}}\n'

        def racing_push(repo, branch, candidate, dest_sha, env):
            if racing_push.first:
                racing_push.first = False
                commit(self.dweb, "master", {"docs/containers/caddy-tags.json": newer,
                                             "docs/containers/caddy.md": b"x\n" + TBODY % b"newer"},
                       "Update Tags for [edbfi/caddy]", BOT)
            return original(repo, branch, candidate, dest_sha, env)

        racing_push.first = True
        with mock.patch.object(mirror, "push", racing_push):
            results, failed = self.sync("website:master")
        self.assertFalse(failed)
        top = head(self.dweb, "master")
        self.assertEqual(show(self.dweb, top, "docs/containers/caddy-tags.json"), newer)
        self.assertIn(TBODY % b"newer", show(self.dweb, top, "docs/containers/caddy.md"))
        self.assertEqual(git(self.dweb, "rev-parse", f"{top}^"), head(self.hweb, "master"))

    def test_second_run_after_tag_commits_keeps_them(self):
        self.sync("website:master")
        commit(self.dweb, "master", {"docs/containers/caddy-tags.json": b'{"x": 1}\n'}, "Update Tags", BOT)
        before = head(self.dweb, "master")
        results, _ = self.sync("website:master")
        self.assertEqual(results[0]["status"], "unchanged")
        self.assertEqual(head(self.dweb, "master"), before)


class WatchTests(MirrorFixture):
    def test_watch_lifecycle(self):
        self.assertEqual(self.watch(), list(mirror.ALL))  # today's hand-made branches
        self.sync()
        self.assertEqual(self.watch(), [])
        # Bot commits on either side need no sync.
        commit(self.hotio, "alpinevpn", {"packages.txt": b"a=9\n"}, "Modified: packages.txt", BOT)
        commit(self.dest, "alpinevpn", {"packages.txt": b"a=8\n"}, "Modified: packages.txt", BOT)
        commit(self.dweb, "master", {"docs/containers/caddy-tags.json": b'{"y": 1}\n'}, "Update Tags", BOT)
        commit(self.hweb, "master", {"docs/containers/radarr-tags.json": b'{"z": 1}\n'}, "Update Tags", BOT)
        self.assertEqual(self.watch(), [])
        # A human Hotio commit does.
        commit(self.hotio, "noblevpn", {"meta.json": b'{"version": "2"}\n'}, "use MTU from wg conf file")
        self.assertEqual(self.watch(), ["base-image:noblevpn"])
        self.sync("base-image:noblevpn")
        self.assertEqual(self.watch(), [])
        # So does a hand edit of the mirror.
        commit(self.dest, "workflows", {"README.md": b"edited\n"}, "docs: edit", ("edbfi", "e@example.com"))
        self.assertEqual(self.watch(), ["base-image:workflows"])

    def test_changed_adaptations_trigger_a_sync(self):
        self.sync()
        files = Path(self.temp.name) / "mirrors"
        (files / "base-image").mkdir(parents=True)
        (files / "website").mkdir()
        (files / "base-image/README.md").write_text("new readme\n")
        (files / "website/README.md").write_bytes((mirror.MIRROR_FILES / "website/README.md").read_bytes())
        with mock.patch.object(mirror, "MIRROR_FILES", files):
            self.assertEqual(self.watch(), ["base-image:workflows", "base-image:alpinevpn", "base-image:noblevpn"])

    def test_changed_immortality_job_triggers_the_workflows_branch(self):
        self.sync()
        changed = Path(self.temp.name) / "immortality.yml"
        changed.write_bytes(mirror.IMMORTALITY.read_bytes() + b"# changed\n")
        with mock.patch.object(mirror, "IMMORTALITY", changed):
            self.assertEqual(self.watch(), ["base-image:workflows"])

    def test_hotio_rewind_triggers_a_sync(self):
        self.sync()
        older = git(self.hotio, "rev-parse", "alpinevpn^")
        git(self.hotio, "update-ref", "refs/heads/alpinevpn", older)
        self.assertEqual(self.watch(), ["base-image:alpinevpn"])

    def test_human_commit_with_current_tree_is_not_dispatched(self):
        self.sync("base-image:alpinevpn")
        commit(self.hotio, "alpinevpn", {"meta.json": b'{"version": "1"}\n'}, "touch")
        self.assertEqual(self.watch().count("base-image:alpinevpn"), 0)


class SummaryTests(MirrorFixture):
    def summary(self, results, evidence, budget=mirror.SUMMARY_BUDGET):
        path = Path(self.temp.name) / "summary.md"
        mirror.write_summary(path, results, evidence, dry_run=True, budget=budget)
        return path.read_text()

    def test_summary_shows_every_branch_within_the_budget(self):
        evidence = Path(self.temp.name) / "evidence"
        results, failed = self.sync(push=False, evidence=evidence)
        self.assertFalse(failed)
        sizes = {f"{r['target'].split('/')[1]}-{r['branch']}": sum(
            len((evidence / f"{r['target'].split('/')[1]}-{r['branch']}{suffix}").read_bytes())
            for suffix in (".log", ".stat", ".diff")) for r in results}
        largest = max(sizes, key=sizes.get)
        budget = sum(sizes.values()) - sizes[largest] + sizes[largest] // 2
        text = self.summary(results, evidence, budget)
        self.assertTrue(text.startswith("## Hotio mirror sync (dry run)\n"))
        for item in mirror.ALL:
            self.assertIn(f"### edbfi/{item.replace(':', ' ')}: would push\n", text)
        self.assertIn('+$(figlet "edbfi")', text)  # small reports are shown whole
        self.assertEqual(text.count("Cut to "), 1)
        self.assertIn(f"of {sizes[largest]} bytes. For the whole diff, run", text)
        self.assertLessEqual(len(text.encode()), budget + 4096)

    def test_summary_shows_the_error_of_a_failed_branch(self):
        commit(self.hotio, "alpinevpn", {"root/etc/s6-overlay/s6-rc.d/init-setup/run": b"#!/bin/sh\n"})
        evidence = Path(self.temp.name) / "evidence"
        results, failed = self.sync("base-image:alpinevpn", push=False, evidence=evidence)
        self.assertTrue(failed)
        text = self.summary(results, evidence)
        self.assertIn("### edbfi/base-image alpinevpn: failed\n", text)
        self.assertIn("Hotio layout changed", text)

    def test_code_block_fence_outlasts_backticks_in_the_text(self):
        self.assertEqual(mirror.code_block("+```yaml\n+````\n", "diff"), "`````diff\n+```yaml\n+````\n`````\n")
        self.assertEqual(mirror.code_block("plain"), "```\nplain\n```\n")


class CommandTests(MirrorFixture):
    def run_main(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.run_main_keep_stdout(*args)

    def run_main_keep_stdout(self, *args):
        stderr = io.StringIO()
        with mock.patch.dict(os.environ), contextlib.redirect_stderr(stderr):
            os.environ.pop("PERSONAL_TOKEN", None)
            code = mirror.main([*args, "--workdir", str(self.work), "--github", str(self.github)])
        return code, stderr.getvalue()

    def test_sync_without_token_fails_clearly(self):
        before = head(self.dest, "workflows")
        code, err = self.run_main("sync")
        self.assertEqual(code, 1)
        self.assertIn("::error::PERSONAL_TOKEN is not set", err)
        self.assertEqual(head(self.dest, "workflows"), before)

    def test_dry_run_needs_no_token(self):
        code, _ = self.run_main("sync", "--dry-run")
        self.assertEqual(code, 0)

    def test_summary_needs_no_evidence_folder(self):
        summary = Path(self.temp.name) / "summary.md"
        summary.write_text("earlier step\n")
        code, _ = self.run_main("sync", "--dry-run", "--branches", "base-image:noblevpn", "--summary", str(summary))
        self.assertEqual(code, 0)
        text = summary.read_text()
        self.assertTrue(text.startswith("earlier step\n## Hotio mirror sync (dry run)\n"))
        self.assertIn("### edbfi/base-image noblevpn: would push\n", text)

    def test_unwritable_summary_does_not_fail_the_sync(self):
        summary = Path(self.temp.name) / "summary-is-a-folder"
        summary.mkdir()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code, err = self.run_main_keep_stdout("sync", "--dry-run", "--branches", "base-image:noblevpn",
                                                  "--summary", str(summary))
        self.assertEqual(code, 0)
        self.assertIn("::warning::cannot write the run summary", err)
        self.assertIn('"status": "would push"', stdout.getvalue())

    def test_unknown_selection_rejected(self):
        code, err = self.run_main("sync", "--dry-run", "--branches", "base-image:workflows; rm -rf /")
        self.assertEqual(code, 1)
        self.assertIn("unknown branch selection", err)

    def test_selection_runs_in_canonical_order(self):
        self.assertEqual(mirror.parse_selection("website:master base-image:noblevpn base-image:workflows"),
                         ["base-image:workflows", "base-image:noblevpn", "website:master"])

    def test_watch_writes_github_output(self):
        output = Path(self.temp.name) / "output"
        code, _ = self.run_main("watch", "--github-output", str(output))
        self.assertEqual(code, 0)
        self.assertEqual(output.read_text(), "branches=" + " ".join(mirror.ALL) + "\n")

    def test_token_only_reaches_git_through_the_environment(self):
        token = "secret-value"
        basic = base64.b64encode(b"x-access-token:" + token.encode()).decode()
        env = mirror.git_env(token)
        self.assertEqual(env["GIT_CONFIG_KEY_0"], "http.https://github.com/.extraheader")
        self.assertEqual(env["GIT_CONFIG_VALUE_0"], "AUTHORIZATION: basic " + basic)
        argvs = []
        real_run = subprocess.run

        def recording_run(args, *rest, **kwargs):
            argvs.append(list(args))
            return real_run(args, *rest, **kwargs)

        with mock.patch.object(mirror.subprocess, "run", recording_run), \
                contextlib.redirect_stderr(io.StringIO()):
            results, failed = mirror.run_sync(list(mirror.ALL), self.work, push_changes=True, token=token,
                                              github=str(self.github))
        self.assertFalse(failed)
        self.assertIn("push", {arg for argv in argvs for arg in argv})
        for argv in argvs:
            self.assertFalse(any(token in arg or basic in arg for arg in argv), argv)

    def test_failed_scan_stops_the_sync(self):
        real_git = mirror.git

        def failing_grep(cwd, *args, **kwargs):
            if args[0] == "grep":
                return subprocess.CompletedProcess(args, 128, b"", b"fatal: bad object")
            return real_git(cwd, *args, **kwargs)

        before = head(self.dest, "alpinevpn")
        with mock.patch.object(mirror, "git", failing_grep):
            results, failed = self.sync("base-image:alpinevpn")
        self.assertTrue(failed)
        self.assertIn("cannot scan the candidate", results[0]["error"])
        self.assertEqual(head(self.dest, "alpinevpn"), before)


if __name__ == "__main__":
    unittest.main()
