---
hide:
  - toc
title: edbfi/obzorarr
---

[:octicons-mark-github-16: GitHub](https://github.com/edbfi/obzorarr-docker){ class="header-links" target="_blank" rel="noopener" }
[:octicons-container-16: ghcr.io](https://github.com/users/edbfi/packages/container/package/obzorarr-docker){ class="header-links" target="_blank" rel="noopener" }

[:octicons-link-16: Source Code](https://github.com/edbfi/obzorarr){ class="header-links" target="_blank" rel="noopener" }

<div class="image-logo"><img src="/img/image-logos/obzorarr.svg" alt="logo"></div>

!!! question "What is this?"

    Obzorarr is a "Plex Wrapped" application that syncs viewing history from your Plex Media Server and generates yearly statistics with an animated slideshow presentation - similar to Spotify Wrapped. It doesn't require Tautulli; it only relies on the Plex API.

!!! note "Branches and Tags"

    **`:nightly`** is available for amd64 and arm64. It is built from a reviewed, pinned application revision and published after native runtime checks.

    Stable version **0.1.11** is preserved. The `release`, `latest` and `pr` image tags are not yet published in this namespace.

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
<tr><td><div id="tag3002" onclick="CopyToClipboard('tag3002');return false;" class="tag-decoration">nightly</div></td><td>Nightly builds</td><td><a href="https://github.com/edbfi/obzorarr-docker/commits/nightly" target="_blank">View commits</a></td><td><a href="https://github.com/edbfi/obzorarr-docker/actions" target="_blank">View builds</a></td></tr>
    </tbody>
  </table>
</div>

!!! note "Persistent configuration"

    Keep your `/config` volume when replacing the container. Back it up before upgrading; it contains the application database and settings.

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
        ghcr.io/edbfi/obzorarr-docker:nightly
    ```

=== "compose"

    ```yaml linenums="1"
    services:
      obzorarr:
        container_name: obzorarr
        image: ghcr.io/edbfi/obzorarr-docker:nightly
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
