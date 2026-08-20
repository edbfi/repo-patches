# AGENTS.md

This file provides guidance to AI coding agents when working with code in this
repository.

## What this repository is

A control repository. It has no application code, no package manifest, and no
local build, test, or lint tooling — do not look for `npm test` or an
equivalent. It holds:

1. GitHub Actions workflows that rewrite **other** repositories
   (`engels74/base-image`, `engels74/website`).
2. `hweb-content/` — the source of truth for engels74's customizations to the
   documentation site, copied into `engels74/website` during sync.

Nothing here runs locally; every effect happens inside an Actions run against a
remote repo.

## Commands

All three workflows are `workflow_dispatch`. Requires `gh` authenticated against
`engels74/repo-patches`.

```bash
gh workflow run sync-hweb.yml -f dry_run=true   # website sync, no push — do this first
gh workflow run sync-hweb.yml                   # force-pushes engels74/website@master
gh workflow run base-image.yml                  # syncs engels74/base-image, 3 branches
gh workflow run watch-hotio-base.yml            # run the upstream watcher now
```

`dry_run` exists only on `sync-hweb.yml`. `base-image.yml` has no dry-run mode
and force-pushes three branches.

## Architecture

| Workflow | Target | Upstream | Trigger |
|---|---|---|---|
| `sync-hweb.yml` | `engels74/website@master` | `hotio/website@master` | manual, `dry_run` input |
| `base-image.yml` | `engels74/base-image` (`workflows`, `alpinevpn`, `noblevpn`) | `hotio/base` | manual, or dispatched by the watcher |
| `watch-hotio-base.yml` | dispatches `base-image.yml` | reads `hotio/base` | cron `37 */6 * * *` + manual |

Both sync workflows are destructive by design: hard reset the target to
upstream, delete unwanted upstream content, overlay engels74 content,
`push --force`. **The target repos are outputs, never inputs** — anything edited
directly in `engels74/website` or `engels74/base-image` is destroyed on the next
run. Change `hweb-content/` (site) or the `sed` patch block in `base-image.yml`
(image branding) instead.

`watch-hotio-base.yml` treats `.parents[0].sha` of `engels74/base-image@<branch>`
as the last-synced upstream SHA, then counts commits since then not authored by
`github-actions[bot]`. Compare failures fail *open* (sync anyway).

`base-image.yml` ends by pushing an empty
`chore: Trigger downstream workflows [skip ci]` commit to this repo — most of
`git log` here is that bot commit, and local `main` goes stale after any sync.

## Path mapping (`hweb-content/` → target repo)

| Source | Lands at |
|---|---|
| `config/mkdocs.yml` | `mkdocs.yml` (target **root**) |
| `docs/index.md`, `docs/faq.md`, `docs/CNAME` | `docs/` |
| `docs/containers/<name>.md` | `docs/containers/` |
| `docs/overrides/main.html` | `overrides/main.html` (target **root**, not `docs/`) |
| `assets/img/engels74.svg` | `docs/img/` |
| `assets/img/image-logos/*` | `docs/img/image-logos/` |
| `assets/stylesheets/extra-custom.css` | `docs/stylesheets/` |

Files the site needs that are deliberately *not* here — `includes/wireguard.md`,
`docs/javascripts/tablesort.js`, `docs/javascripts/tagcopy.js`,
`docs/stylesheets/extra-13.css` — are inherited from upstream after the reset.
Do not vendor copies into this repo.

## Adding or removing a container

A container is defined in many places at once; miss one and the sync fails at
its step 6 / step 16 guards, or the page ships broken.

1. `hweb-content/docs/containers/<name>.md`
2. `hweb-content/assets/img/image-logos/<name>.svg`
3. `hweb-content/config/mkdocs.yml` — `nav:`, under Base Images / Apps / engels74
4. `hweb-content/docs/index.md` — a pill link in the matching
   `e74-registry-category` block
5. `.github/workflows/sync-hweb.yml` — six bash lists: `REQUIRED_FILES`,
   `CONTAINERS_TO_KEEP`, `TAGS_JSON_TO_KEEP`, `CONTAINERS`, `KEEP_LOGOS`,
   `EXPECTED_FILES`. Touch `KEEP_AVATARS` only if upstream ships a webhook
   avatar for it.
6. Verify with `gh workflow run sync-hweb.yml -f dry_run=true`.

`KEEP_LOGOS` and `KEEP_AVATARS` are keyed by **upstream asset filename**, which
does not always match the doc name: `overseerr-anime.md` uses `overseerr.*`, and
`qflood` needs `flood.*` kept alongside `qflood.*`.

## Conventions

- Container pages share a fixed skeleton: front matter (`hide: [toc]`,
  `title: engels74/<name>`), header link row, `<div class="image-logo">`, a
  `!!! question "What is this?"` admonition, a hand-written
  `<div id="tags-table">` block, `## Starting the container` with `=== "cli"` /
  `=== "compose"` tabs, and a trailing `--8<-- "includes/wireguard.md"`. Copy
  the closest existing page rather than composing one.
- Tag-table element IDs use a per-container thousand block in alphabetical
  order: base-image `1xxx` … tgraph-bot `8xxx`; a new container takes `9xxx`.
  They must be globally unique — `CopyToClipboard('tagNNNN')` resolves by DOM id.
- Site-specific CSS is namespaced `e74-*` and belongs only in
  `hweb-content/assets/stylesheets/extra-custom.css`.

## Gotchas

- **`hweb-content/docs/containers/*-tags.json` are never deployed.**
  `sync-hweb.yml` writes `{}` for seven containers and restores
  `base-image-tags.json` from a backup taken off the *live target repo* before
  the reset. Editing the checked-in JSON changes nothing. Tag tables render from
  the hand-written HTML in each `.md` — change tags there.
- **A new logo missing from `KEEP_LOGOS` silently disappears.** Step 12 copies
  `assets/img/image-logos/*`, step 13 then deletes anything not in `KEEP_LOGOS`,
  and step 16 does not verify logos — the sync passes with a broken image.
- **`extra-13.css` is an upstream-versioned filename pinned in two places**:
  `extra_css:` in `hweb-content/config/mkdocs.yml`, and `EXPECTED_FILES` in
  `sync-hweb.yml`. An upstream bump to `extra-14.css` needs both.
- **The site cannot be built or previewed from this repo.** `mkdocs.yml` expects
  to sit at a repo root beside `docs/`, and the build needs the upstream-only
  files listed above. Validate with a `dry_run=true` sync and read its step 16
  verification output and diff summary.
- **`base-image.yml` branding patches are branch-conditional.** The `init-setup`
  and README rewrites apply only to `alpinevpn` / `noblevpn`; the
  `call-build.yml` / `call-update.yml` repointing runs on all three branches.
  Preserve that split when editing the patch block.
- **`GH_PAT` (repo scope) is required** by `sync-hweb.yml` and `base-image.yml`
  to check out and push the target repos; `watch-hotio-base.yml` uses the
  default `GITHUB_TOKEN` with `actions: write`. A failure at checkout usually
  means an expired PAT, not a logic bug.

## Reference

- `README.md` — container inventory, and the summary of what each sync
  preserves, replaces, and removes. Read it when editing the keep/delete lists
  in `sync-hweb.yml`. It omits `watch-hotio-base.yml` and describes
  `base-image.yml` as manual-only.
