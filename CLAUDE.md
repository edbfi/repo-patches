# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Stdlib-only Python tools (`tools/`) that prepare upstream-merge candidates for `edbfi/base-image` and `edbfi/website`, plus the canonical website overlay (`hweb-content/`). No dependencies to install.

## Commands

- All tests: `python3 -m unittest discover -s tools -p 'test_*.py'`
- One file: `python3 -m unittest discover -s tools -p 'test_site_overlay.py'`
- One case: `cd tools && python3 -m unittest test_site_overlay.OverlayTests.test_corrupt_tags_rejected`
- Workflow lint: `actionlint` (reads `.github/actionlint.yaml`)
- Tests import modules by bare name (`from site_overlay import ...`), so `python3 -m unittest tools.test_site_overlay` from the root fails with an import error; use `discover -s tools` or run from `tools/`.
- The website build/smoke lane only runs in CI (`website` job in `.github/workflows/ci.yml`): it overlays onto a pinned `hotio/website` ref and builds with `zensical build --strict` (zensical 0.0.60, not `mkdocs`, despite the `mkdocs.yml` name), then runs `tools/smoke_site.py` against the served output.
- `python3 tools/prepare_sync.py ...` clones the real destination over the network. To test preparation logic, call `prepare()` against a local fixture repo the way `SyncFixture` in `tools/test_prepare_sync.py` does.

## Invariants

- Preparation stays read-only: workflows keep `permissions: contents: read` and must not push, dispatch, publish or need a PAT. Their output is `result.json`, `candidate.patch` and `candidate.bundle`, uploaded as an artifact.
- `.upstream.json` in the destination is the only merge-base source. Don't infer the upstream revision from commit history.
- The container inventory is the set of `hweb-content/docs/containers/*.md` files (`container_names()` in `tools/site_overlay.py`). Anything upstream that isn't in it, plus `docs/guides/` and `docs/scripts/`, is pruned before merging and again during overlay.
- `hweb-content/docs/containers/*-tags.json` are never copied into candidates. Tag JSON always comes from the destination repo, and a missing file is created as `{}`. To change published tags, change the destination, not these files.
- Only the paths in `OVERLAY_MAPPING` (`tools/site_overlay.py`), the container pages and matching logos get overlaid. A new file under `hweb-content/` has no effect until you add it to `OVERLAY_MAPPING`, which `prepare_sync.py` also reads.
- Logos are kept only when the file stem equals a container name, or is `flood`. Any other logo is deleted from the candidate.
- `includes/*.md`, `docs/javascripts/*.js` and `extra-13.css` come from upstream and are checked, never vendored. Don't add copies to `hweb-content/`. If you change the required list in `apply_overlay()`, update the fixture file lists in both `tools/test_site_overlay.py` and `tools/test_prepare_sync.py`.
- Keep the `e74-*` CSS class names. `docs/index.md` uses them, and `smoke_site.py` requires `e74-hero` on the homepage.

## Adding or removing a container page

Derived from commits c9652be and f68dd81. Touch all of these together:

1. `hweb-content/docs/containers/<name>.md`. It must contain `edbfi/<name>` and `ghcr.io/edbfi/<name>`, because the smoke test checks for both.
2. `hweb-content/docs/containers/<name>-tags.json`, the seed copy (see the tag JSON invariant above).
3. `hweb-content/assets/img/image-logos/<name>.svg`, referenced as `/img/image-logos/<name>.svg`.
4. The `nav:` entry in `hweb-content/config/mkdocs.yml`.
5. A pill link in `hweb-content/docs/index.md`. The smoke test requires a homepage link to every container.
6. The expected name set in `tools/test_site_overlay.py`.
7. The container list and count in `README.md` ("Canonical documentation").

## Values kept in sync by hand

- Base-image branches: `TARGETS` in `tools/prepare_sync.py`, the `options` in `.github/workflows/base-image.yml` and the `matrix` in `.github/workflows/watch-hotio-base.yml`.
- Runner label `ubuntu-26.04`: every `runs-on` and `.github/actionlint.yaml`. Actionlint rejects any label that isn't listed there.

## Commits

CI (`hygiene` job) checks every commit in the push or PR range. Each subject must match `^(feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert)(\(scope\))?!?: ` and the body must have an exact `Signed-off-by: <author name> <email>` line, so commit with `git commit -s`. The job also runs `git diff --exit-code HEAD`, so tests must not leave tracked files modified.

## Reference docs

- `README.md`: preparation semantics, the candidate review/apply/merge procedure and the canonical-documentation rules. Read before changing `prepare_sync.py`, the workflows or the page inventory.
