#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Recreate an upstream-derived tree with edbfi customizations; never push."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from prepare_sync import TARGETS, git
from site_overlay import apply_overlay, container_names


def replace_required(path, old, new):
    text = path.read_text()
    if old not in text:
        raise ValueError(f"Upstream layout changed: {path}: missing {old!r}")
    path.write_text(text.replace(old, new))


def refresh(root, target, branch, upstream, overlay):
    repository, branches = TARGETS[target]
    if branch not in branches:
        raise ValueError("Unexpected target branch")
    if git(root, "status", "--porcelain"):
        raise ValueError("Refresh requires a clean disposable clone")
    provenance = json.loads((root / ".upstream.json").read_text())
    if provenance["repository"] != repository or provenance["branch"] != branch:
        raise ValueError("Upstream provenance does not match target")
    revision = git(root, "rev-parse", "--verify", upstream + "^{commit}")
    base = git(root, "rev-parse", "HEAD")
    # These destination-owned files survive recreation. All other files come
    # from upstream or the canonical overlay; old replacement CI is removed.
    retained = ["README.md"]
    if target == "website":
        retained += ["LICENSE-overlay", "requirements.txt", "tools/check_site.py"]
        retained += [f"docs/containers/{name}-tags.json" for name in container_names(overlay)]
    saved = {name: (root / name).read_bytes() for name in retained if (root / name).is_file()}
    if target == "website":
        for name in container_names(overlay):
            saved.setdefault(f"docs/containers/{name}-tags.json", b"{}\n")
    git(root, "read-tree", "--reset", "-u", revision)
    for name, content in saved.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    # Renovate has been retired. Account-wide maintenance and notifications
    # are not part of the edbfi container refresh.
    (root / "renovate.json").unlink(missing_ok=True)
    (root / ".github/workflows/maintenance.yml").unlink(missing_ok=True)
    if target == "base-image":
        for name, called in (("call-build.yml", "build-on-call.yml"),
                             ("call-update.yml", "update-on-call.yml")):
            replace_required(root / ".github/workflows" / name,
                             f"hotio/base/.github/workflows/{called}@workflows",
                             f"edbfi/base-image/.github/workflows/{called}@workflows")
        if branch == "workflows":
            build = root / ".github/workflows/build-on-call.yml"
            replace_required(build, "https://hotio.dev/containers/", "https://web.edb.fi/containers/")
            text = build.read_text()
            if "\n  notify:\n" not in text:
                raise ValueError("Upstream notification job changed")
            build.write_text(text.split("\n  notify:\n", 1)[0] + "\n")
            # Explicit permissions are needed with edbfi's read-only default.
            for name in ("call-build.yml", "call-update.yml", "build-on-call.yml", "update-on-call.yml"):
                path = root / ".github/workflows" / name
                replace_required(path, "\njobs:\n", "\npermissions:\n  contents: write\n  packages: write\n\njobs:\n")
        else:
            init = root / "root/etc/s6-overlay/s6-rc.d/init-setup/run"
            replace_required(init, '$(figlet "hotio")', '$(figlet "edbfi")')
            replace_required(init, "Donate:        https://hotio.dev/donate", "Upstream:      https://hotio.dev/donate")
            replace_required(init, "Documentation: https://hotio.dev", "Documentation: https://web.edb.fi")
            replace_required(init, "Support:       https://hotio.dev/discord",
                             "Support:       https://github.com/edbfi/$(jq -r '.app' <<< \"${IMAGE_STATS}\")/issues")
            for name in ("call-build.yml", "call-update.yml"):
                replace_required(root / ".github/workflows" / name, "\njobs:\n",
                                 "\npermissions:\n  contents: write\n  packages: write\n\njobs:\n")
    else:
        apply_overlay(root, overlay)
        # Keep the existing pinned site builder while using upstream's Pages flow.
        replace_required(root / ".github/workflows/deploy-pages.yml",
                         "pip install zensical", "pip install -r requirements.txt")
    provenance["revision"] = revision
    (root / ".upstream.json").write_text(json.dumps(provenance, indent=2) + "\n")
    git(root, "add", "--all")
    return {"target": f"edbfi/{target}", "branch": branch, "base": base, "upstream": revision}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--output", type=Path, required=True)
    opts = parser.parse_args()
    repository, branches = TARGETS[opts.target]
    if opts.branch not in branches:
        parser.error("Branch is not configured for this target")
    if opts.output.exists() and any(opts.output.iterdir()):
        parser.error("Output directory must be empty")
    with tempfile.TemporaryDirectory(prefix="hotio-refresh-") as temp:
        root = Path(temp) / "candidate"
        subprocess.run(["git", "clone", "--branch", opts.branch,
                        f"https://github.com/edbfi/{opts.target}.git", str(root)], check=True)
        git(root, "fetch", f"https://github.com/{repository}.git", opts.branch)
        report = refresh(root, opts.target, opts.branch, "FETCH_HEAD",
                         Path(__file__).resolve().parent.parent / "hweb-content")
        opts.output.mkdir(parents=True, exist_ok=True)
        patch = subprocess.check_output(["git", "-C", str(root), "diff", "--cached", "--binary"])
        if patch:
            (opts.output / "candidate.patch").write_bytes(patch)
            git(root, "-c", "user.name=github-actions[bot]", "-c",
                "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                "commit", "-s", "-m", "ci: refresh upstream hotio files and edbfi customizations")
            git(root, "bundle", "create", str((opts.output / "candidate.bundle").resolve()), "HEAD")
            report.update(status="prepared", candidate=git(root, "rev-parse", "HEAD"))
        else:
            report["status"] = "unchanged"
        (opts.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
