<p align="center">
  <img src="docs/img/edbfi.svg" alt="website logo" width="160" height="160">
</p>
<h1 align="center">website</h1>
<p align="center"><strong>Documentation for edbfi Docker images.</strong></p>
<p align="center">
  <a href="https://github.com/edbfi/website/blob/master/LICENSE"><img src="https://img.shields.io/badge/Upstream_license-GPL--3.0-blue?style=flat" alt="Upstream license: GPL-3.0"></a>
  <a href="https://github.com/squidfunk/mkdocs-material"><img src="https://img.shields.io/badge/MkDocs_Material-526CFE?style=flat&amp;logo=materialformkdocs&amp;logoColor=white" alt="MkDocs Material"></a>
  <a href="https://github.com/python/cpython" title="CPython implementation source"><img src="https://img.shields.io/badge/Python-3776AB?style=flat&amp;logo=python&amp;logoColor=white" alt="Python"></a>
</p>

The source of https://web.edb.fi: a generated mirror of [hotio/website](https://github.com/hotio/website). Do not edit it by hand or through pull requests.

`master` is Hotio's latest commit plus one commit by `github-actions[bot]` with edbfi's site. [edbfi/repo-patches](https://github.com/edbfi/repo-patches) regenerates that commit and force-pushes the branch when Hotio changes its design, or when edbfi's content changes. The image workflows then add their own bot commits ("Update Tags for [...]") on top. To change the site, change `hweb-content/` in edbfi/repo-patches.

The edbfi commit applies the `hweb-content/` overlay (configuration, home page, FAQ, container pages, logos, styles and the `web.edb.fi` CNAME), removes the containers, guides and scripts edbfi does not publish, keeps each container's tag data (`docs/containers/*-tags.json` and the tags table in its page) exactly as published here, removes `renovate.json`, and adds the Pullfrog review workflow and this README. Hotio's Pages workflow deploys every push to `master`.

Hotio's content is GPL-3.0 ([LICENSE](LICENSE)). Original overlay code from [edbfi/repo-patches](https://github.com/edbfi/repo-patches#license) is licensed under the GNU Affero General Public License, version 3 or (at your option) any later version (`AGPL-3.0-or-later`). Upstream-derived content and third-party artwork retain their existing licences and attribution.
