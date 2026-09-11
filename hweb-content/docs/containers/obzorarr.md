---
hide:
  - toc
title: edbfi/obzorarr
---

[:octicons-mark-github-16: GitHub](https://github.com/edbfi/obzorarr-docker){ class="header-links" target="_blank" rel="noopener" }
[:octicons-container-16: ghcr.io](https://github.com/orgs/edbfi/packages/container/package/obzorarr-docker){ class="header-links" target="_blank" rel="noopener" }

[:octicons-link-16: Source Code](https://github.com/edbfi/obzorarr){ class="header-links" target="_blank" rel="noopener" }

<div class="image-logo"><img src="/img/image-logos/obzorarr.svg" alt="logo"></div>

!!! question "What is this?"

    Obzorarr is a "Plex Wrapped" application that syncs viewing history from your Plex Media Server and generates yearly statistics with an animated slideshow presentation - similar to Spotify Wrapped. It doesn't require Tautulli; it only relies on the Plex API.

!!! note "Branches and Tags"

    This project maintains multiple branches, each with its own Docker tag:

    - **`:release` (or `:latest`)**:
      Stable releases built from tagged versions of the [obzorarr](https://github.com/edbfi/obzorarr) repository.

    - **`:nightly`**:
      Built from every commit to the main branch, providing the latest development features.

    - **`:pr`**:
      Built from the [`pr`](https://github.com/edbfi/obzorarr-docker/tree/pr) branch. This tag is used for testing pull request changes and experimental builds before they are merged into the main codebase.

<div id="tags-table">
  <table>
    <thead>
      <tr>
        <th>Tags <span class="twemoji" title="Click Tag to Copy"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M11 9h2V7h-2m1 13c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8m0-18A10 10 0 0 0 2 12a10 10 0 0 0 10 10 10 10 0 0 0 10-10A10 10 0 0 0 12 2m-1 15h2v-6h-2z"></path></svg></span></th>
        <th>Description</th>
        <th>Commit</th>
        <th>Last Updated</th>
      </tr>
    </thead>
    <tbody id="tags-table-body">
<tr><td><div class="tag-decoration-latest">latest</div><div id="tag3001" onclick="CopyToClipboard('tag3001');return false;" class="tag-decoration">release</div></td><td>Releases</td><td><a href="https://github.com/edbfi/obzorarr-docker/commits/release" target="_blank">View commits</a></td><td><a href="https://github.com/edbfi/obzorarr-docker/actions" target="_blank">View builds</a></td></tr>
<tr><td><div id="tag3002" onclick="CopyToClipboard('tag3002');return false;" class="tag-decoration">nightly</div></td><td>Nightly builds</td><td><a href="https://github.com/edbfi/obzorarr-docker/commits/nightly" target="_blank">View commits</a></td><td><a href="https://github.com/edbfi/obzorarr-docker/actions" target="_blank">View builds</a></td></tr>
<tr><td><div id="tag3003" onclick="CopyToClipboard('tag3003');return false;" class="tag-decoration">pr</div></td><td>Pull request testing</td><td><a href="https://github.com/edbfi/obzorarr-docker/commits/pr" target="_blank">View commits</a></td><td><a href="https://github.com/edbfi/obzorarr-docker/actions" target="_blank">View builds</a></td></tr>
    </tbody>
  </table>
</div>

## Starting the container

=== "cli"

    ```shell linenums="1"
    docker run --rm \
        --name obzorarr \
        -p 3000:3000 \
        -e PUID=1000 \
        -e PGID=1000 \
        -e UMASK=002 \
        -e TZ="Etc/UTC" \
        -v /<host_folder_config>:/config \
        ghcr.io/edbfi/obzorarr-docker
    ```

=== "compose"

    ```yaml linenums="1"
    services:
      obzorarr:
        container_name: obzorarr
        image: ghcr.io/edbfi/obzorarr-docker
        ports:
          - "3000:3000"
        environment:
          - PUID=1000
          - PGID=1000
          - UMASK=002
          - TZ=Etc/UTC
        volumes:
          - /<host_folder_config>:/config
    ```

--8<-- "includes/wireguard.md"
