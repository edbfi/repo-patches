# website

The source of https://web.edb.fi: a generated mirror of [hotio/website](https://github.com/hotio/website). Do not edit it by hand or through pull requests.

`master` is Hotio's latest commit plus one commit by `github-actions[bot]` with edbfi's site. [edbfi/repo-patches](https://github.com/edbfi/repo-patches) regenerates that commit and force-pushes the branch when Hotio changes its design, or when edbfi's content changes. The image workflows then add their own bot commits ("Update Tags for [...]") on top. To change the site, change `hweb-content/` in edbfi/repo-patches.

The edbfi commit applies the `hweb-content/` overlay (configuration, home page, FAQ, container pages, logos, styles and the `web.edb.fi` CNAME), removes the containers, guides and scripts edbfi does not publish, keeps each container's tag data (`docs/containers/*-tags.json` and the tags table in its page) exactly as published here, removes `renovate.json`, and adds the Pullfrog review workflow and this README. Hotio's Pages workflow deploys every push to `master`.

Hotio's content is GPL-3.0 ([LICENSE](LICENSE)); the overlay comes from edbfi/repo-patches under its AGPL-3.0 licence.
