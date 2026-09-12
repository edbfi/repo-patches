#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare upstream updates in a disposable clone; never push or replace history."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

TARGETS = {"base-image": ("hotio/base", {"workflows", "alpinevpn", "noblevpn"}),
           "website": ("hotio/website", {"master"})}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def filtered_site_commit(root, revision, names, owned):
    """Filter an immutable tree using a separate index, without touching checkout."""
    from site_overlay import excluded_path
    paths = subprocess.check_output(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "-z", revision]
    ).split(b"\0")
    removed = [path for path in paths if path and excluded_path(path.decode(), names)]
    with tempfile.TemporaryDirectory(prefix="site-index-") as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"))
        def indexed(*args, data=None):
            return subprocess.check_output(["git", "-C", str(root), *args], input=data, env=env)
        indexed("read-tree", revision)
        if removed:
            indexed("update-index", "--force-remove", "-z", "--stdin", data=b"\0".join(removed) + b"\0")
        for path, blob in owned.items():
            indexed("update-index", "--add", "--cacheinfo", "100644," + blob + "," + path)
        tree = indexed("write-tree").decode().strip()
    return git(root, "-c", "user.name=github-actions[bot]",
               "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
               "commit-tree", tree, "-m", "Temporary inventory-filtered merge input")


def prepare(root, upstream_sha, target, branch, output, overlay=None):
    upstream_repo, branches = TARGETS[target]
    if branch not in branches or not re.fullmatch(r"[0-9a-f]{40}", upstream_sha):
        raise ValueError("Unexpected branch or revision")
    if git(root, "status", "--porcelain"):
        raise ValueError("Candidate clone must be clean")
    provenance_file = root / ".upstream.json"
    if provenance_file.is_symlink():
        raise ValueError("Upstream provenance cannot be a symlink")
    provenance = json.loads(provenance_file.read_text())
    if provenance.get("repository") != upstream_repo or provenance.get("branch") != branch:
        raise ValueError("Upstream provenance does not match target")
    previous = provenance.get("revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", previous):
        raise ValueError("Invalid recorded upstream revision")
    git(root, "cat-file", "-e", previous + "^{commit}")
    base = git(root, "rev-parse", "HEAD")
    merge_previous, merge_base, merge_upstream = previous, base, upstream_sha
    if target == "website":
        if overlay is None:
            raise ValueError("Website overlay is required")
        from site_overlay import container_names, OVERLAY_MAPPING
        names = container_names(overlay)
        owned_files = {new: (overlay / old).read_bytes() for old, new in OVERLAY_MAPPING.items()}
        for name in names:
            owned_files["docs/containers/" + name + ".md"] = (overlay / "docs/containers" / (name + ".md")).read_bytes()
            tag_path = "docs/containers/" + name + "-tags.json"
            tags = root / tag_path
            if tags.is_symlink():
                raise ValueError("Container tags cannot be a symlink")
            content = tags.read_bytes() if tags.exists() else b"{}\n"
            json.loads(content)
            owned_files[tag_path] = content
        for logo in (overlay / "assets/img/image-logos").iterdir():
            if logo.is_file() and logo.stem in names | {"flood"}:
                owned_files["docs/img/image-logos/" + logo.name] = logo.read_bytes()
        owned = {path: subprocess.check_output(
            ["git", "-C", str(root), "hash-object", "-w", "--stdin"], input=content
        ).decode().strip() for path, content in owned_files.items()}
        merge_previous, merge_base, merge_upstream = (
            filtered_site_commit(root, revision, names, owned) for revision in (previous, base, upstream_sha)
        )
    result = subprocess.run(["git", "-C", str(root), "merge-tree", "--write-tree",
                             "--merge-base", merge_previous, merge_base, merge_upstream],
                            text=True, capture_output=True)
    if result.returncode:
        raise ValueError("Upstream merge conflicts; resolve a reviewed candidate manually. " + result.stdout)
    tree = result.stdout.splitlines()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise ValueError("Unexpected merge result")
    git(root, "read-tree", "--reset", "-u", tree)
    if target == "website":
        if overlay is None:
            raise ValueError("Website overlay is required")
        from site_overlay import apply_overlay
        apply_overlay(root, overlay)
    provenance["revision"] = upstream_sha
    provenance_file.write_text(json.dumps(provenance, indent=2) + "\n")
    git(root, "add", "--all")
    output.mkdir(parents=True, exist_ok=True)
    report = {"target": "edbfi/" + target, "branch": branch, "base": base,
              "previousUpstream": previous, "upstream": upstream_sha}
    if git(root, "diff", "--cached", "--name-only"):
        patch = subprocess.check_output(["git", "-C", str(root), "diff", "--cached", "--binary"])
        (output / "candidate.patch").write_bytes(patch)
        git(root, "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit", "-s", "-m", "chore(sync): refresh " + branch + " from upstream")
        report.update(status="prepared", candidate=git(root, "rev-parse", "HEAD"))
        git(root, "bundle", "create", str((output / "candidate.bundle").resolve()), "HEAD")
    else:
        report["status"] = "unchanged"
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--output", type=Path, required=True)
    opts = parser.parse_args()
    upstream_repo, branches = TARGETS[opts.target]
    if opts.branch not in branches:
        parser.error("Branch is not configured for this target")
    if opts.output.exists() and any(opts.output.iterdir()):
        parser.error("Output directory must be empty")
    with tempfile.TemporaryDirectory(prefix="repo-patches-") as temp:
        root = Path(temp) / "candidate"
        subprocess.run(["git", "clone", "--branch", opts.branch,
                        "https://github.com/edbfi/" + opts.target + ".git", str(root)], check=True)
        git(root, "remote", "add", "upstream", "https://github.com/" + upstream_repo + ".git")
        git(root, "fetch", "upstream", opts.branch)
        upstream_sha = git(root, "rev-parse", "FETCH_HEAD")
        report = prepare(root, upstream_sha, opts.target, opts.branch, opts.output,
                         Path(__file__).resolve().parent.parent / "hweb-content")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
