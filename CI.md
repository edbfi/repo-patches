# Dependency updates and validation

Renovate dependency updates, including majors and shared-policy versions, merge
unattended only after all four current-head jobs pass: guard, hygiene, website,
and ci / required. The checked action verifies genuine author sign-offs and
requests full final CI for the exact merged commit. Explicit dispatches validate
the current PR or default-branch SHA at the start and aggregate gate.

Hygiene retains full workflow lint and per-commit Conventional Commit/DCO checks.
The website lane retains its strict build. No dashboard approval, branch
protections or rulesets are configured; native GitHub automerge stays disabled.
Other changes retain exact head/base, full diff, author/DCO and full CI/artifact
review through the maintainer's ghmerge process, followed by final verification.

Upstream preparation and its tests remain read-only. Manual candidate workflows
retain their patches, bundles and revision reports; no downstream dispatch,
image publication, automatic application of candidates or PAT is introduced.
The canonical website overlay and Hotio/base-image relationship are unchanged.
