# Repository update candidates

Prepare reviewed upstream updates for `edbfi/base-image` and the documentation site at `web.edb.fi`. Every run works in a disposable clone and retains a patch, recovery bundle and revision report. Preparation never pushes branches, bypasses protection, publishes images or sends messages. No personal access token is required.

`tools/prepare_sync.py` merges upstream changes using the exact `.upstream.json` revision recorded in the destination. It preserves destination changes and stops on conflicts or invalid provenance. For website updates, the canonical container inventory filters excluded pages, tags, logos, guides and scripts from all three merge inputs first. Upstream edits to intentionally excluded content therefore cannot restore it or block preparation. Canonical pages, navigation and branding are applied to all three inputs, and retained image-tag JSON comes only from the destination. Hotio tag updates cannot overwrite edbfi publication data. Conflicts in shared inherited content still stop for review. Website candidates additionally apply the canonical `hweb-content/` overlay, retaining tag data for supported containers and inherited runtime assets. The original GPL/AGPL licenses and upstream attribution remain applicable.

## Run locally

```sh
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/prepare_sync.py --target base-image --branch alpinevpn --output /tmp/base-candidate
python3 tools/prepare_sync.py --target website --branch master --output /tmp/site-candidate
```

Output directories must be empty. Website preparation requires the destination repository and reviewed `.upstream.json` bootstrap; it is staged until those exist.

Review `result.json` and `candidate.patch`, verify the destination still equals the recorded base, then apply the patch on a maintainer branch and create a Conventional Commit with your matching Signed-off-by line. The bundle retains the generated candidate for recovery. Open a PR, run the destination's local checks, and merge through the maintainer's reviewed ghmerge flow after exact head/base, full diff and author/sign-off are verified. Publishing is a separate manual operation in the image repository.

## Canonical documentation

Eight container pages are retained: base-image, caddy, obzorarr, otpravkarr, qbittorrent, qflood, sabnzbd and zondarr. The pages describe the intended image namespace; availability depends on each image's migration and publication. Navigation and index links must match the page inventory. Source logos include upstream credits in the site footer. Internal `e74-*` CSS selectors remain for compatibility.

The overlay maps config/mkdocs.yml to the website root, docs content into docs/, docs/overrides/main.html to overrides/main.html, and assets into docs/img and docs/stylesheets. Required upstream includes, JavaScript and extra-13.css remain inherited. Existing tag JSON is preserved for every retained container; missing data starts as an empty object. Unrelated upstream guides/scripts and container pages/logos are excluded from the assembled candidate.

## Refresh upstream files and inherited CI

Use a full refresh when the destination has drifted from hotio's design:

```sh
python3 tools/refresh_upstream.py --target base-image --branch workflows --output /tmp/base-workflows-refresh
python3 tools/refresh_upstream.py --target base-image --branch alpinevpn --output /tmp/base-alpine-refresh
python3 tools/refresh_upstream.py --target base-image --branch noblevpn --output /tmp/base-noble-refresh
python3 tools/refresh_upstream.py --target website --branch master --output /tmp/website-refresh
```

The manual **Prepare hotio refresh** workflow runs the same command and retains the artifacts. It does not push or publish. Review and apply each candidate through a PR against its recorded destination branch, updating `workflows` before the image branches. This recreates the upstream file tree, not the branch history. Destination changes outside the explicit customizations are removed, unlike the incremental merge performed by `prepare_sync.py`.

Base-image retains edbfi startup branding, workflow references and documentation URLs, with explicit write permissions for hotio's publishing flow. Hotio's build, update and smoke-test design is retained. Retired Renovate, account-wide maintenance and Discord notifications are excluded. The README is retained; obsolete replacement CI and its helper tools are removed.

Website retains the canonical overlay, destination tag JSON, README, overlay license, pinned requirements and site validation tool. Its Pages workflow comes from upstream and installs the existing requirements. Missing destination tag data starts empty; upstream publication data is never imported.

Configure `PERSONAL_TOKEN` and appropriate branch-write access separately for hotio's metadata updates and website tag writer. The refresh preparation itself needs neither credentials nor repository write access.
