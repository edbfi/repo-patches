#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Keep edbfi/base-image and edbfi/website as Hotio's latest commit plus one edbfi commit.

`watch` lists the branches that need a sync; `sync` rebuilds each selected
branch from Hotio's head, commits edbfi's adaptations once as
github-actions[bot] and force-pushes it with a lease on the destination head
it was built from. A destination whose tree already equals the candidate's
is left alone.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / "hweb-content"
MIRROR_FILES = ROOT / "mirrors"
PULLFROG = ROOT / ".github/workflows/pullfrog.yml"

BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
BOT_ENV = {"GIT_AUTHOR_NAME": BOT_NAME, "GIT_AUTHOR_EMAIL": BOT_EMAIL,
           "GIT_COMMITTER_NAME": BOT_NAME, "GIT_COMMITTER_EMAIL": BOT_EMAIL}

# Destination repository -> (Hotio repository, branches in sync order).
# `workflows` goes first: the image branches call its reusable workflows.
TARGETS = {"base-image": ("hotio/base", ("workflows", "alpinevpn", "noblevpn")),
           "website": ("hotio/website", ("master",))}
ALL = tuple(f"{target}:{branch}" for target, (_, branches) in TARGETS.items() for branch in branches)

INIT_SETUP = "root/etc/s6-overlay/s6-rc.d/init-setup/run"
# (path, Hotio's text, edbfi's text). Every occurrence is replaced and at least
# one must exist, so a changed Hotio layout stops the sync instead of
# publishing a half-adapted branch.
CALLER_EDITS = (
    (".github/workflows/call-build.yml",
     b"uses: hotio/base/.github/workflows/build-on-call.yml@workflows",
     b"uses: edbfi/base-image/.github/workflows/build-on-call.yml@workflows"),
    (".github/workflows/call-update.yml",
     b"uses: hotio/base/.github/workflows/update-on-call.yml@workflows",
     b"uses: edbfi/base-image/.github/workflows/update-on-call.yml@workflows"),
)
WORKFLOWS_EDITS = (
    (".github/workflows/build-on-call.yml",
     b"https://hotio.dev/containers/", b"https://web.edb.fi/containers/"),
    (".github/workflows/maintenance.yml",
     b"https://raw.githubusercontent.com/hotio/base/",
     b"https://raw.githubusercontent.com/edbfi/base-image/"),
)
IMAGE_EDITS = (
    (INIT_SETUP, b'$(figlet "hotio")', b'$(figlet "edbfi")'),
    (INIT_SETUP, b"Donate:        https://hotio.dev/donate",
     b"Upstream:      https://hotio.dev/donate"),
    (INIT_SETUP, b"Documentation: https://hotio.dev${app_uri}",
     b"Documentation: https://web.edb.fi${app_uri}"),
    (INIT_SETUP, b"Support:       https://hotio.dev/discord",
     b"Support:       https://github.com/edbfi/$(jq -r '.app' <<< \"${IMAGE_STATS}\")/issues"),
)
# Nothing in a generated base-image branch may still point builds, images,
# documentation or support at Hotio. The runtime user `hotio` stays.
BASE_IMAGE_FORBIDDEN = (b"hotio/base/.github/workflows/", b"raw.githubusercontent.com/hotio/",
                        b"ghcr.io/hotio/", b"hotio.dev/containers", b"hotio.dev/discord",
                        b'figlet "hotio"')


class SyncError(RuntimeError):
    pass


def log(message):
    print(message, file=sys.stderr, flush=True)


def git(cwd, *args, env=None, data=None, check=True):
    result = subprocess.run(["git", "-C", str(cwd), *args], input=data, env=env,
                            capture_output=True)
    if check and result.returncode:
        raise SyncError(f"git {args[0]} failed: " + result.stderr.decode(errors="replace").strip())
    return result


def out(cwd, *args, **kwargs):
    return git(cwd, *args, **kwargs).stdout.decode().strip()


def git_env(token=None):
    """Environment for network git calls; the token never appears in argv or URLs."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::add-mask::{basic}", flush=True)
        env.update(GIT_CONFIG_COUNT="1",
                   GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                   GIT_CONFIG_VALUE_0=f"AUTHORIZATION: basic {basic}")
    return env


def open_repo(path, target, github="https://github.com"):
    """A local repository with remotes `hotio` and `dest` for one destination."""
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        out(path, "init", "--quiet")
        out(path, "config", "core.autocrlf", "false")
        out(path, "config", "gc.auto", "0")
        out(path, "remote", "add", "hotio", f"{github}/{TARGETS[target][0]}.git")
        out(path, "remote", "add", "dest", f"{github}/edbfi/{target}.git")
    return path


def fetch(repo, remote, branch, env):
    """Fetch one branch; return its commit, or None when the branch does not exist."""
    probe = git(repo, "ls-remote", "--exit-code", remote, f"refs/heads/{branch}", env=env, check=False)
    if probe.returncode == 2:
        return None
    if probe.returncode:
        raise SyncError(f"cannot read {remote} {branch}: " + probe.stderr.decode(errors="replace").strip())
    out(repo, "fetch", "--quiet", "--no-tags", "--force", remote,
        f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}", env=env)
    return out(repo, "rev-parse", f"refs/remotes/{remote}/{branch}^{{commit}}")


def remote_head(repo, branch, env):
    result = git(repo, "ls-remote", "--exit-code", "dest", f"refs/heads/{branch}", env=env, check=False)
    if result.returncode == 2:
        return None
    if result.returncode:
        raise SyncError("cannot read the destination: " + result.stderr.decode(errors="replace").strip())
    return result.stdout.decode().split()[0]


def blob(repo, commit, path):
    """A file's bytes at `commit`, or None when it does not exist there."""
    if commit is None:
        return None
    result = git(repo, "cat-file", "blob", f"{commit}:{path}", check=False)
    return result.stdout if result.returncode == 0 else None


def edit(work, path, old, new):
    file = work / path
    if not file.is_file():
        raise SyncError(f"Hotio layout changed: {path} is missing")
    data = file.read_bytes()
    if old not in data:
        raise SyncError(f"Hotio layout changed: {path} no longer contains {old.decode()!r}")
    file.write_bytes(data.replace(old, new))


def adapt_base_image(work, branch):
    edits = CALLER_EDITS + (WORKFLOWS_EDITS if branch == "workflows" else IMAGE_EDITS)
    for path, old, new in edits:
        edit(work, path, old, new)
    (work / "renovate.json").unlink(missing_ok=True)
    (work / "README.md").write_bytes((MIRROR_FILES / "base-image/README.md").read_bytes())
    if branch == "workflows":
        (work / ".github/workflows/pullfrog.yml").write_bytes(PULLFROG.read_bytes())


def adapt_website(work, published):
    from site_overlay import apply_overlay
    (work / "renovate.json").unlink(missing_ok=True)
    apply_overlay(work, OVERLAY, published)
    (work / "README.md").write_bytes((MIRROR_FILES / "website/README.md").read_bytes())
    (work / ".github/workflows").mkdir(parents=True, exist_ok=True)
    (work / ".github/workflows/pullfrog.yml").write_bytes(PULLFROG.read_bytes())


def message(target, branch, hotio_sha):
    upstream = TARGETS[target][0]
    text = (f"chore(mirror): sync {branch} with {upstream}@{hotio_sha[:7]}\n\n"
            f"Hotio's {branch} at {hotio_sha} plus edbfi's adaptations in this one\n"
            f"commit, generated by edbfi/repo-patches (tools/mirror.py). The branch is\n"
            f"regenerated and force-pushed on every sync: change the adaptations in\n"
            f"edbfi/repo-patches, never here.\n\n"
            f"Upstream: {upstream}@{hotio_sha}\n")
    if os.environ.get("GITHUB_SHA"):
        text += f"Generator: edbfi/repo-patches@{os.environ['GITHUB_SHA']}\n"
    return text


def build_candidate(repo, target, branch, hotio_sha, dest_sha):
    """Hotio's commit plus one bot commit with edbfi's adaptations; returns its SHA.

    Website tag data and rendered tags tables are read from `dest_sha`.
    """
    with tempfile.TemporaryDirectory(prefix="mirror-") as temp:
        work = Path(temp) / "tree"
        out(repo, "worktree", "add", "--quiet", "--detach", "--force", str(work), hotio_sha)
        try:
            if target == "base-image":
                adapt_base_image(work, branch)
            else:
                adapt_website(work, lambda path: blob(repo, dest_sha, path))
            out(work, "add", "--all")
            tree = out(work, "write-tree")
        finally:
            git(repo, "worktree", "remove", "--force", str(work), check=False)
            git(repo, "worktree", "prune", check=False)
    env = dict(os.environ, **BOT_ENV)
    commit = out(repo, "commit-tree", tree, "-p", hotio_sha, env=env,
                 data=message(target, branch, hotio_sha).encode())
    verify_candidate(repo, target, hotio_sha, dest_sha, commit)
    return commit


def verify_candidate(repo, target, hotio_sha, dest_sha, commit):
    """Refuse a candidate that is not Hotio's head plus one adapted bot commit."""
    parents = out(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]
    if parents != [hotio_sha]:
        raise SyncError("candidate is not a single commit on Hotio's head")
    identity = out(repo, "show", "-s", "--format=%an <%ae>|%cn <%ce>", commit)
    if identity != f"{BOT_NAME} <{BOT_EMAIL}>|{BOT_NAME} <{BOT_EMAIL}>":
        raise SyncError("candidate is not authored and committed by " + BOT_NAME)
    if target == "base-image":
        args = ["grep", "-I", "-l", "-F"]
        for needle in BASE_IMAGE_FORBIDDEN:
            args += ["-e", needle.decode()]
        found = git(repo, *args, commit, check=False)
        if found.returncode > 1:
            raise SyncError("cannot scan the candidate: " + found.stderr.decode(errors="replace").strip())
        if found.returncode == 0:
            raise SyncError("candidate still points at Hotio: " + found.stdout.decode().strip())
    else:
        from site_overlay import container_names
        for name in container_names(OVERLAY):
            path = f"docs/containers/{name}-tags.json"
            expected = blob(repo, dest_sha, path) or b"{}\n"
            if blob(repo, commit, path) != expected:
                raise SyncError(f"candidate {path} differs from the destination")


def tree_of(repo, commit):
    return out(repo, "rev-parse", f"{commit}^{{tree}}")


def push(repo, branch, candidate, dest_sha, env):
    """Force-push with a lease on `dest_sha`; True on success."""
    lease = f"--force-with-lease=refs/heads/{branch}:{dest_sha or ''}"
    result = git(repo, "push", "--quiet", lease, "dest", f"{candidate}:refs/heads/{branch}",
                 env=env, check=False)
    if result.returncode:
        log(result.stderr.decode(errors="replace").strip())
    return result.returncode == 0


def sync_branch(repo, target, branch, *, push_changes, env, evidence=None, attempts=5):
    for attempt in range(1, attempts + 1):
        hotio_sha = fetch(repo, "hotio", branch, env)
        if hotio_sha is None:
            raise SyncError(f"{TARGETS[target][0]} has no branch {branch}")
        dest_sha = fetch(repo, "dest", branch, env)
        candidate = build_candidate(repo, target, branch, hotio_sha, dest_sha)
        result = {"target": f"edbfi/{target}", "branch": branch, "hotio": hotio_sha,
                  "destination": dest_sha, "candidate": candidate}
        if evidence is not None:
            write_evidence(repo, evidence, target, branch, hotio_sha, candidate)
        if dest_sha and tree_of(repo, candidate) == tree_of(repo, dest_sha):
            return dict(result, status="unchanged")
        if not push_changes:
            return dict(result, status="would push")
        if push(repo, branch, candidate, dest_sha, env):
            # A successful leased push set the branch to the candidate; a bot
            # may already have added a commit on top, so don't re-read it.
            return dict(result, status="pushed")
        if remote_head(repo, branch, env) == dest_sha:
            raise SyncError(f"push to edbfi/{target} {branch} was rejected")
        log(f"edbfi/{target} {branch} moved during the sync (attempt {attempt}); rebuilding")
    raise SyncError(f"edbfi/{target} {branch} kept moving; gave up after {attempts} attempts")


def write_evidence(repo, folder, target, branch, hotio_sha, candidate):
    folder.mkdir(parents=True, exist_ok=True)
    stem = folder / f"{target}-{branch}"
    stem.with_suffix(".diff").write_bytes(git(repo, "diff", hotio_sha, candidate).stdout)
    stem.with_suffix(".log").write_bytes(git(
        repo, "log", "--format=%H %P%n  %an <%ae> | %cn <%ce>%n  %s", "-n", "3", candidate).stdout)


def needs_sync(repo, target, branch, env):
    """Why the branch needs a sync, or None when it is a current mirror."""
    upstream = TARGETS[target][0]
    hotio_sha = fetch(repo, "hotio", branch, env)
    dest_sha = fetch(repo, "dest", branch, env)
    if hotio_sha is None:
        raise SyncError(f"{upstream} has no branch {branch}")
    if dest_sha is None:
        return "the destination branch does not exist"
    reason = stale_reason(repo, target, branch, hotio_sha, dest_sha)
    if reason is None:
        return None
    try:
        candidate = build_candidate(repo, target, branch, hotio_sha, dest_sha)
    except (SyncError, ValueError) as error:
        return f"{reason}; the adaptations no longer apply: {error}"
    if tree_of(repo, candidate) == tree_of(repo, dest_sha):
        # A sync would skip the push; dispatching it would repeat on every watch.
        log(f"edbfi/{target} {branch}: {reason}, but the destination tree is already current")
        return None
    return reason


def stale_reason(repo, target, branch, hotio_sha, dest_sha):
    upstream = TARGETS[target][0]
    base = git(repo, "merge-base", dest_sha, hotio_sha, check=False).stdout.decode().strip()
    if not base:
        return "the destination shares no history with Hotio"
    authors = out(repo, "log", "--format=%ae", f"{base}..{hotio_sha}").split()
    human = [email for email in authors if email != BOT_EMAIL]
    if human:
        return f"{len(human)} new non-bot commit(s) on {upstream} {branch}"
    # A generated branch is Hotio's commit `base`, then our sync commit, then
    # only bot commits (packages.txt, meta.json, tags) on a straight line.
    lines = out(repo, "log", "--reverse", "--format=%H %P|%ae", f"{base}..{dest_sha}").splitlines()
    if not lines:
        return f"the destination has no sync commit on {upstream}@{base[:7]}"
    first, sync_author = lines[0].split("|")
    sync_sha, *sync_parents = first.split()
    if sync_parents != [base] or sync_author != BOT_EMAIL or \
            f"Upstream: {upstream}@{base}" not in out(repo, "show", "-s", "--format=%B", sync_sha):
        return f"the destination has no sync commit on {upstream}@{base[:7]}"
    for line in lines[1:]:
        commit, author = line.split("|")
        if len(commit.split()) != 2 or author != BOT_EMAIL:
            return f"the destination has a commit not made by the bot ({commit.split()[0][:7]})"
    try:
        rebuilt = build_candidate(repo, target, branch, base, sync_sha)
    except (SyncError, ValueError) as error:
        return f"the adaptations no longer apply: {error}"
    if tree_of(repo, rebuilt) != tree_of(repo, sync_sha):
        return "the adaptations in edbfi/repo-patches changed since the last sync"
    return None


def parse_selection(text):
    selected = text.split() if text and text.strip() else list(ALL)
    unknown = [item for item in selected if item not in ALL]
    if unknown:
        raise SyncError("unknown branch selection " + " ".join(unknown) + "; choose from " + " ".join(ALL))
    return [item for item in ALL if item in selected]


def run_sync(selection, workdir, *, push_changes, token=None, github="https://github.com", evidence=None):
    env = git_env(token)
    results, failed = [], False
    for target in TARGETS:
        repo = None
        for item in selection:
            name, branch = item.split(":")
            if name != target:
                continue
            repo = repo or open_repo(workdir / target, target, github)
            try:
                result = sync_branch(repo, target, branch, push_changes=push_changes, env=env,
                                     evidence=evidence)
            except (SyncError, ValueError) as error:
                log(f"::error::edbfi/{target} {branch}: {error}")
                results.append({"target": f"edbfi/{target}", "branch": branch, "status": "failed",
                                "error": str(error)})
                failed = True
                break  # later branches of this destination depend on the earlier ones
            log(f"edbfi/{target} {branch}: {result['status']} ({result['candidate'][:7]} on "
                f"{TARGETS[target][0]}@{result['hotio'][:7]})")
            results.append(result)
    return results, failed


def run_watch(workdir, github="https://github.com"):
    env = git_env()
    due = []
    for item in ALL:
        target, branch = item.split(":")
        repo = open_repo(workdir / target, target, github)
        reason = needs_sync(repo, target, branch, env)
        log(f"edbfi/{target} {branch}: {reason or 'current'}")
        if reason:
            due.append(item)
    return due


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    watch = sub.add_parser("watch", help="list the branches that need a sync")
    watch.add_argument("--github-output", type=Path, help="append branches=<list> to this file")
    sync = sub.add_parser("sync", help="rebuild and push the selected branches")
    sync.add_argument("--branches", default="", help="space-separated; empty means all: " + " ".join(ALL))
    sync.add_argument("--dry-run", action="store_true", help="build and compare, never push")
    sync.add_argument("--evidence", type=Path, help="write each candidate's diff and log here")
    for command in (watch, sync):
        command.add_argument("--workdir", type=Path, help="reuse this folder for the local clones")
        command.add_argument("--github", default="https://github.com", help=argparse.SUPPRESS)
    opts = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="hotio-mirror-") as temp:
        workdir = opts.workdir or Path(temp)
        try:
            if opts.command == "watch":
                due = run_watch(workdir, opts.github)
                print(" ".join(due))
                if opts.github_output:
                    with opts.github_output.open("a") as handle:
                        handle.write(f"branches={' '.join(due)}\n")
                return 0
            selection = parse_selection(opts.branches)
            token = os.environ.get("PERSONAL_TOKEN", "")
            if not opts.dry_run and not token:
                raise SyncError("PERSONAL_TOKEN is not set. Add a personal access token with Contents and "
                                "Workflows read/write on edbfi/base-image and edbfi/website as the "
                                "Actions secret PERSONAL_TOKEN of edbfi/repo-patches.")
            results, failed = run_sync(selection, workdir, push_changes=not opts.dry_run, token=token,
                                       github=opts.github, evidence=opts.evidence)
        except SyncError as error:
            log(f"::error::{error}")
            return 1
    print(json.dumps(results, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
