# Dependency updates and validation

Required application CI retains hygiene, website and `ci / required`.
The website lane assembles the canonical overlay onto pinned upstream content,
runs the strict build, then serves that exact output. Its mandatory HTTP smoke
loads the homepage, FAQ, every canonical container page and tag JSON object,
checks branding, registry links and image namespaces, and fetches the pages'
local stylesheets, scripts and images. This checks served content and assets;
it does not execute JavaScript or prove browser hydration.

The separate PR policy workflow requires Conventional Commit titles, genuine
author-matching sign-offs, authentic Renovate provenance, no blocking holds,
review requests or unresolved changes requests. After a pass, it re-runs the
other event's older failed verdict for the same head, which needs `actions: write`.
Require its actual emitted check name alongside the application checks, pinned to
GitHub Actions. Preserve strict up-to-date branch protection and stronger
repository review requirements. Explicit CI dispatches cannot substitute for a
missing metadata policy result.

Renovate is the only dependency merger. The shared `automerge.json` preset arms
GitHub auto-merge with rebase merges, preserving signed commits; GitHub merges only
once every required CI and policy check passes on the current head. Current
branches, release ages, reviews and hold labels remain required. Shared automation
configuration updates remain manual. The legacy Actions merger and its comment
commands are retired. Shared actions, workflows and presets use immutable `v4.0.0`
references. Inspect default-branch CI after each merge.

Upstream preparation and its tests remain read-only. Manual candidate workflows
retain their patches, bundles and revision reports; no downstream dispatch,
image publication, automatic application of candidates or PAT is introduced.
The canonical website overlay and Hotio/base-image relationship are unchanged.
