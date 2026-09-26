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
