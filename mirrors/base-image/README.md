<p align="center">
  <img src="assets/base-image.svg" alt="base-image logo" width="256" height="256">
</p>
<h1 align="center">base-image</h1>
<p align="center"><strong>Shared Hotio-derived container build workflows and VPN base images.</strong></p>
<p align="center">
  <a href="https://github.com/edbfi/base-image/blob/workflows/LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=flat" alt="License: GPL-3.0"></a>
  <a href="https://github.com/actions/runner" title="GitHub Actions runner source"><img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat&amp;logo=githubactions&amp;logoColor=white" alt="GitHub Actions"></a>
  <a href="https://github.com/moby/moby" title="Docker Engine foundation source (Moby)"><img src="https://img.shields.io/badge/Docker-2496ED?style=flat&amp;logo=docker&amp;logoColor=white" alt="Docker"></a>
  <a href="https://github.com/just-containers/s6-overlay"><img src="https://img.shields.io/badge/s6--overlay-222222?style=flat" alt="s6-overlay"></a>
</p>

A generated mirror of [hotio/base](https://github.com/hotio/base). Do not edit it by hand or through pull requests.

Each branch (`workflows`, `alpinevpn`, `noblevpn`) is Hotio's latest commit plus one commit by `github-actions[bot]` with edbfi's adaptations. [edbfi/repo-patches](https://github.com/edbfi/repo-patches) regenerates that commit and force-pushes the branch when Hotio changes its design, or when the adaptations change. The image workflows then add their own bot commits (`meta.json`, `packages.txt`) on top. To change anything here, change edbfi/repo-patches.

The adaptations:

- The callers (`call-build.yml`, `call-update.yml`) use `edbfi/base-image/.github/workflows/...@workflows`.
- `build-on-call.yml` links the image documentation at `https://web.edb.fi/containers/`; `maintenance.yml` fetches from `edbfi/base-image`.
- The startup banner shows `edbfi`, Hotio's donation link as `Upstream`, the documentation at `web.edb.fi` and the image repository's GitHub issues for support.
- `renovate.json` is removed; `workflows` adds the Pullfrog review workflow and a monthly immortality workflow that keeps the schedules from being disabled after 60 days without activity; this README.

Everything else is Hotio's, including the internal `hotio` runtime user. Pushes to `alpinevpn` and `noblevpn` publish `ghcr.io/edbfi/base-image:<branch>` and update https://web.edb.fi/containers/base-image/. The workflows need the Actions secrets `PERSONAL_TOKEN`, `DISCORD_WEBHOOK` and `IMMORTALITY_TOKEN`.

GPL-3.0, as Hotio's [LICENSE](LICENSE).
