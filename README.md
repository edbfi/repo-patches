# repo-patches

Keeps `edbfi/base-image` (branches `workflows`, `alpinevpn`, `noblevpn`) and `edbfi/website` (`master`, served at https://web.edb.fi) as generated mirrors of [hotio/base](https://github.com/hotio/base) and [hotio/website](https://github.com/hotio/website). Hotio stays in charge of the design; the difference from him is always exactly one easy-to-read commit: every sync makes a branch Hotio's head plus that one commit, and only the mirrors' own bots add commits on top until the next sync. Nobody edits the mirrors by hand or through pull requests: change this repository instead.

## How a sync works

`tools/mirror.py sync` does this per branch, `workflows` before the image branches:

1. Fetch Hotio's branch head and the mirror's current head.
2. Check out Hotio's head, apply edbfi's adaptations (below) and commit them once, authored and committed by `github-actions[bot]`. The commit's only parent is Hotio's head, and its message records it (`Upstream: hotio/base@<sha>`).
3. If the result's tree equals the mirror's current tree, stop: nothing is pushed.
4. Otherwise force-push it with a lease on the mirror head read in step 1. If the mirror moved meanwhile (a bot commit), fetch again and rebuild, up to five times.

The push uses the Actions secret `PERSONAL_TOKEN`, so it triggers the mirrors' own workflows: on `alpinevpn` and `noblevpn`, base-image's `call-build` publishes `ghcr.io/edbfi/base-image:<branch>-<sha7>` and writes `base-image-tags.json` to the website, and every docker repo's hourly `call-update` then picks the new base up through `upstream_tag_sha__command`. On the website, Hotio's Pages workflow deploys. After a sync those workflows add their own bot commits (`packages.txt`, `meta.json`, "Update Tags for [...]") on top of the sync commit; the next sync replaces them all.

`tools/mirror.py watch` decides which branches need a sync: Hotio has non-bot commits since the mirror's base (the merge base of the two branches), the mirror is not Hotio's commit plus one sync commit and bot commits (hand edits, or no sync yet), or rebuilding the last sync with today's adaptations gives a different tree. Hotio's own bot commits need no sync, because the mirrors' `call-update` keeps `packages.txt` and `meta.json` current by itself.

## Workflows

- **Watch Hotio** (`watch-hotio.yml`): every 6 hours at minute 37, or by hand on `main`. Starts **Sync Hotio mirrors** on `main` for the branches `watch` lists. It holds no secret: without `PERSONAL_TOKEN`, the sync it starts fails with a clear error.
- **immortality** (`immortality.yml`): monthly, or by hand on `main`. GitHub disables a public repository's schedules after 60 days without activity, and the watcher commits nothing here, so this job re-enables this repository's workflows with the `IMMORTALITY_TOKEN` secret (a personal access token with Actions read/write), which resets that counter. The file is edbfi-ci's [templates/immortality.yml](https://github.com/edbfi/edbfi-ci/blob/main/templates/immortality.yml) byte for byte (edbfi-ci D19, `design/watchdog.md` rule 11).
- **Sync Hotio mirrors** (`sync-hotio.yml`): run by the watcher, or by hand on `main` to force a sync (dispatched on another branch, its job is skipped). Input `branches` is a space-separated subset of `base-image:workflows base-image:alpinevpn base-image:noblevpn website:master` (empty means all four); `dry_run` builds and compares without pushing, and without the token. Each run writes every candidate's commits, changed files and diff against Hotio to its run summary: 768 KiB in total at most, so a larger report is cut at a line boundary, with the command that prints it in full. It fails with a clear error when `PERSONAL_TOKEN` is not set (dry runs excepted).

The sync job holds `PERSONAL_TOKEN`, so it follows edbfi-ci's privileged-job rule ([design/security.md](https://github.com/edbfi/edbfi-ci/blob/main/design/security.md)): one job of inline shell and preinstalled tools (`git`, `python3`), with no actions, containers, services or caches; it fetches this repository's triggering commit with plain `git` (anonymously, as the repository is public) and runs only on `main`. The watcher references no secret, so it may use `actions/checkout`.

`PERSONAL_TOKEN` is a personal access token with Contents and Workflows read/write on `edbfi/base-image` and `edbfi/website` (the generated commits change workflow files). The mirrors also need their own secrets: `PERSONAL_TOKEN` (Hotio's `update-on-call` and website tag writer), `DISCORD_WEBHOOK` (Hotio's `notify` job) and `IMMORTALITY_TOKEN` (the immortality job) in `edbfi/base-image`.

To force a sync: `gh workflow run sync-hotio.yml -R edbfi/repo-patches` (all four branches), or with `-f branches="base-image:alpinevpn"` or `-f dry_run=true`.

## The adaptations

base-image, all branches: the callers' `uses:` point at `edbfi/base-image/.github/workflows/{build,update}-on-call.yml@workflows`; `renovate.json` is removed; [mirrors/base-image/README.md](mirrors/base-image/README.md) is added.

- `workflows`: `build-on-call.yml` links documentation at `https://web.edb.fi/containers/`; `maintenance.yml` fetches from `raw.githubusercontent.com/edbfi/base-image/`; the Pullfrog workflow (this repository's `.github/workflows/pullfrog.yml`) and the immortality workflow ([mirrors/base-image/immortality.yml](mirrors/base-image/immortality.yml)) are added. The immortality job keeps base-image's hourly `call-update`, which runs from `workflows`, enabled; it is this repository's `immortality.yml` without the template header and guarded by the default branch instead of `main`, because base-image's default branch is `workflows`. Hotio's `notify` job and `maintenance.yml` stay, and no `permissions` blocks are added (base-image's default workflow token is `write`, as on Hotio's account).
- `alpinevpn`, `noblevpn`: the startup banner in `root/etc/s6-overlay/s6-rc.d/init-setup/run` shows `edbfi`, Hotio's donation link as `Upstream`, the documentation at `web.edb.fi` and the image repository's GitHub issues for support. The runtime user `hotio` stays.

website: the `hweb-content/` overlay (below), the pruning of everything outside the container inventory, the tag data read from the mirror, `renovate.json` removed, [mirrors/website/README.md](mirrors/website/README.md) and the Pullfrog workflow added. Hotio's Pages workflow stays as it is.

Each edit must find Hotio's text, and a base-image candidate must not still point builds, images, documentation or support at Hotio; otherwise the sync stops before pushing. Update the edit in `tools/mirror.py` when Hotio changes those lines.

## Canonical documentation

Eight container pages are retained: base-image, caddy, obzorarr, otpravkarr, qbittorrent, qflood, sabnzbd and zondarr. The pages describe the intended image namespace; availability depends on each image's migration and publication. Navigation and index links must match the page inventory. Source logos include upstream credits in the site footer. Internal `e74-*` CSS selectors remain for compatibility.

The overlay maps config/mkdocs.yml to the website root, docs content into docs/, docs/overrides/main.html to overrides/main.html, and assets into docs/img and docs/stylesheets. Required upstream includes, JavaScript and extra-13.css remain inherited. Each retained container's tag data comes from the mirror as published: its `docs/containers/<name>-tags.json` (an empty object when missing) and the tags table Hotio's tag writer renders into its page. Hotio's tag data is never kept. Unrelated upstream guides/scripts and container pages/logos are excluded.

## Run locally

```sh
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/mirror.py watch
python3 tools/mirror.py sync --dry-run --evidence /tmp/mirror-evidence
```

`watch` and `sync --dry-run` only read the public repositories. Without `--dry-run`, `sync` pushes and needs `PERSONAL_TOKEN`.

## License

[AGPL-3.0-only](LICENSE). The mirrors keep Hotio's GPL-3.0 licence and attribution.
