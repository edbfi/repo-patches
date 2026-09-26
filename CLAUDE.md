# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Stdlib-only Python tools (`tools/`) that prepare upstream-merge candidates for `edbfi/base-image` and `edbfi/website`, plus the canonical website overlay (`hweb-content/`). No dependencies to install.

## Commands

- All tests: `python3 -m unittest discover -s tools -p 'test_*.py'`
- One file: `python3 -m unittest discover -s tools -p 'test_site_overlay.py'`
- One case: `cd tools && python3 -m unittest test_site_overlay.OverlayTests.test_corrupt_tags_rejected`
- Tests import modules by bare name (`from site_overlay import ...`), so `python3 -m unittest tools.test_site_overlay` from the root fails with an import error; use `discover -s tools` or run from `tools/`.
- `python3 tools/prepare_sync.py ...` clones the real destination over the network. To test preparation logic, call `prepare()` against a local fixture repo the way `SyncFixture` in `tools/test_prepare_sync.py` does.

## Invariants

- Preparation stays read-only: it must not push, dispatch, publish or need a PAT. Its output is `result.json`, `candidate.patch` and `candidate.bundle` in the output directory.
- `.upstream.json` in the destination is the only merge-base source. Don't infer the upstream revision from commit history.
- The container inventory is the set of `hweb-content/docs/containers/*.md` files (`container_names()` in `tools/site_overlay.py`). Anything upstream that isn't in it, plus `docs/guides/` and `docs/scripts/`, is pruned before merging and again during overlay.
- `hweb-content/docs/containers/*-tags.json` are never copied into candidates. Tag JSON always comes from the destination repo, and a missing file is created as `{}`. To change published tags, change the destination, not these files.
- Only the paths in `OVERLAY_MAPPING` (`tools/site_overlay.py`), the container pages and matching logos get overlaid. A new file under `hweb-content/` has no effect until you add it to `OVERLAY_MAPPING`, which `prepare_sync.py` also reads.
- Logos are kept only when the file stem equals a container name, or is `flood`. Any other logo is deleted from the candidate.
- `includes/*.md`, `docs/javascripts/*.js` and `extra-13.css` come from upstream and are checked, never vendored. Don't add copies to `hweb-content/`. If you change the required list in `apply_overlay()`, update the fixture file lists in both `tools/test_site_overlay.py` and `tools/test_prepare_sync.py`.
- Keep the `e74-*` CSS class names. `docs/index.md` uses them.

## Adding or removing a container page

Derived from commits c9652be and f68dd81. Touch all of these together:

1. `hweb-content/docs/containers/<name>.md`. It must contain `edbfi/<name>` and `ghcr.io/edbfi/<name>`.
2. `hweb-content/docs/containers/<name>-tags.json`, the seed copy (see the tag JSON invariant above).
3. `hweb-content/assets/img/image-logos/<name>.svg`, referenced as `/img/image-logos/<name>.svg`.
4. The `nav:` entry in `hweb-content/config/mkdocs.yml`.
5. A pill link in `hweb-content/docs/index.md`. Every container needs a homepage link.
6. The expected name set in `tools/test_site_overlay.py`.
7. The container list and count in `README.md` ("Canonical documentation").

## Commits

Each subject must match `^(feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert)(\(scope\))?!?: ` and the body must have an exact `Signed-off-by: <author name> <email>` line, so commit with `git commit -s`. Tests must not leave tracked files modified (`git diff --exit-code HEAD` stays clean).

## Reference docs

- `README.md`: preparation semantics, the candidate review/apply/merge procedure and the canonical-documentation rules. Read before changing `prepare_sync.py` or the page inventory.

## Full upstream refresh

`tools/refresh_upstream.py` deliberately reconstructs the upstream tree and reapplies explicit edbfi customizations. It is separate from the incremental three-way merge in `prepare_sync.py`. Run it only in its disposable clone or a clean dedicated worktree. Its CLI and manual workflow only produce candidates; neither pushes, publishes nor replaces remote history. Preserve destination website tag JSON, including empty defaults when a tag file is absent. Keep hotio's container build and smoke-test behavior; do not introduce application CI into the generated container repositories.
