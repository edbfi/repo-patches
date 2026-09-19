# Dependency updates and validation

Required application CI retains guard, hygiene, website and `ci / required`.
The website lane assembles the canonical overlay onto pinned upstream content,
runs the strict build, then serves that exact output. Its mandatory HTTP smoke
loads the homepage, FAQ, every canonical container page and tag JSON object,
checks branding, registry links and image namespaces, and fetches the pages'
local stylesheets, scripts and images. This checks served content and assets;
it does not execute JavaScript or prove browser hydration.

The separate PR policy workflow requires Conventional Commit titles, genuine
author-matching sign-offs, authentic Renovate provenance, no blocking holds,
review requests or unresolved changes requests. Require its actual emitted
check name alongside the application checks, pinned to GitHub Actions. Preserve
strict up-to-date branch protection and stronger repository review requirements.
Explicit CI dispatches validate the current PR/default SHA at the start and gate;
they cannot substitute for a missing metadata policy result.

Renovate is the only ongoing dependency merge owner. Direct automerge remains
disabled, including matching package rules, until the shared rollout proves a
native Renovate canary behind complete required CI. The legacy Actions merger
and its comment commands are retired. Shared actions, workflows and presets
use the immutable `v3.0.0` release. Merges must satisfy current CI and repository
policy; inspect the resulting default-branch run after each merge.

Upstream preparation and its tests remain read-only. Manual candidate workflows
retain their patches, bundles and revision reports; no downstream dispatch,
image publication, automatic application of candidates or PAT is introduced.
The canonical website overlay and Hotio/base-image relationship are unchanged.
