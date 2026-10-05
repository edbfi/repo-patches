# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Stdlib-only Python tools (`tools/`) and two workflows that keep `edbfi/base-image` (`workflows`, `alpinevpn`, `noblevpn`) and `edbfi/website` (`master`) as generated mirrors of `hotio/base` and `hotio/website`: Hotio's latest commit plus one `github-actions[bot]` commit with edbfi's adaptations, force-pushed. Also the canonical website overlay (`hweb-content/`) and the mirrors' READMEs (`mirrors/`). No dependencies to install.

## Commands

- All tests: `python3 -m unittest discover -s tools -p 'test_*.py'`
- One file: `python3 -m unittest discover -s tools -p 'test_mirror.py'`
- One case: `cd tools && python3 -m unittest test_mirror.WatchTests.test_watch_lifecycle`
- Tests import modules by bare name (`from site_overlay import ...`), so `python3 -m unittest tools.test_mirror` from the root fails with an import error; use `discover -s tools` or run from `tools/`.
- Tests run against local bare repositories standing in for GitHub (`MirrorFixture` in `tools/test_mirror.py`, `--github <folder>` on the CLI). `python3 tools/mirror.py watch` and `sync --dry-run --evidence <dir>` read the real public repositories and never push.

## Invariants

- Only `sync-hotio.yml` (via `tools/mirror.py sync` without `--dry-run`) pushes, and only to `edbfi/base-image` and `edbfi/website`, with the `PERSONAL_TOKEN` secret. Never push to the mirrors from anywhere else, and never edit them by hand or through PRs: every change goes into this repository and reaches them through a sync.
- A pushed branch is exactly Hotio's head plus one commit, authored and committed by `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`, whose message carries `Upstream: <hotio repo>@<sha>`. `verify_candidate()` enforces this before every push, and `watch` finds the last sync through it and the merge base. Don't add a second commit or a recorded-revision file.
- Every push is a lease on the mirror head the candidate was built from. A lease failure means a bot wrote meanwhile: fetch, rebuild, retry. Never force-push without the lease; it would drop newer tag data or bot commits.
- Skip the push when the candidate's tree equals the mirror's current tree.
- Edit Hotio's files as bytes (Hotio's `deploy-pages.yml` has CRLF line endings). Each edit in `tools/mirror.py` must find its text; a missing text stops the sync. Keep the base-image guard (`BASE_IMAGE_FORBIDDEN`) in step with the edits.
- The adaptations are only those listed in `README.md` ("The adaptations"). Hotio's `notify` job, `maintenance.yml`, Pages workflow and runtime user `hotio` stay; no `permissions` blocks, no Renovate, no application CI in the mirrors.
- The container inventory is the set of `hweb-content/docs/containers/*.md` files (`container_names()` in `tools/site_overlay.py`). Anything upstream that isn't in it, plus `docs/guides/` and `docs/scripts/`, is pruned.
- Tag data always comes from the mirror's current head: `docs/containers/<name>-tags.json` (`{}` when missing) and the `<tbody id="tags-table-body">` table Hotio's tag writer renders into each container page. Hotio's tag data is never kept. `hweb-content/docs/containers/*-tags.json` and the seed tables are never published; to change published tags, change the mirror's builds, not these files.
- Only the paths in `OVERLAY_MAPPING` (`tools/site_overlay.py`), the container pages and matching logos get overlaid. A new file under `hweb-content/` has no effect until you add it to `OVERLAY_MAPPING`.
- Logos are kept only when the file stem equals a container name, or is `flood`. Any other logo is deleted from the candidate.
- `includes/*.md`, `docs/javascripts/*.js` and `extra-13.css` come from upstream and are checked, never vendored. Don't add copies to `hweb-content/`. If you change the required list in `apply_overlay()`, update the fixture file lists in `tools/test_site_overlay.py` and `tools/test_mirror.py`.
- Keep the `e74-*` CSS class names. `docs/index.md` uses them.
- A change to `hweb-content/`, `mirrors/`, this repository's `pullfrog.yml` or the edits reaches the mirrors at the next watcher run (it detects changed adaptations), or at once with a dispatched sync.

## Adding or removing a container page

Derived from commits c9652be and f68dd81. Touch all of these together:

1. `hweb-content/docs/containers/<name>.md`, with a `<tbody id="tags-table-body">` tags table. It must contain `edbfi/<name>` and `ghcr.io/edbfi/<name>`.
2. `hweb-content/docs/containers/<name>-tags.json`, the seed copy (see the tag data invariant above).
3. `hweb-content/assets/img/image-logos/<name>.svg`, referenced as `/img/image-logos/<name>.svg`.
4. The `nav:` entry in `hweb-content/config/mkdocs.yml`.
5. A pill link in `hweb-content/docs/index.md`. Every container needs a homepage link.
6. The expected name set in `tools/test_site_overlay.py`.
7. The container list and count in `README.md` ("Canonical documentation").

## Commits

Each subject must match `^(feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert)(\(scope\))?!?: ` and the body must have an exact `Signed-off-by: <author name> <email>` line, so commit with `git commit -s`. Tests must not leave tracked files modified (`git diff --exit-code HEAD` stays clean).

## Reference docs

- `README.md`: the sync and watch semantics, the workflows and their secret, the adaptations and the canonical-documentation rules. Read before changing `tools/mirror.py` or the page inventory.
