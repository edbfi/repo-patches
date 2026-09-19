# Repository instructions

This repository prepares upstream update candidates and contains canonical documentation overlays. Read README.md before changing the workflow or inventory.

- Run `python3 -m unittest discover -s tools -p 'test_*.py'` and actionlint after changes.
- Use Conventional Commits with the author's matching Signed-off-by line.
- Keep upstream preparation permissions read-only. Never restore force pushes, direct downstream branch writes, downstream dispatches, automatic publication or personal-token dependencies.
- Renovate is the sole ongoing dependency merge owner after the required CI and metadata policy pass. Direct automerge remains disabled until hosted rollout evidence permits opt-in; see CI.md.
- `.upstream.json` is explicit provenance, never infer it from commit parents. Stop on shared inherited-content conflicts or missing provenance. For website preparation, canonical inventory/pages/branding and destination-owned tag JSON take precedence before the merge; excluded upstream pages must stay excluded.
- Preparation may modify only its disposable candidate clone. Retain patch, bundle and revision report for review.
- For website changes keep canonical container pages, nav, index and logos consistent; preserve upstream copyright/license notices and retained tag JSON.
- Inherited includes, JavaScript and versioned upstream CSS are checked, not vendored. Validate assembled website content before publishing.
- Internal e74 CSS names are compatibility identifiers.
- Website workflow remains staged until the destination and its reviewed provenance exist.
