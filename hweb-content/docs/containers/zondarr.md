---
hide:
  - toc
title: edbfi/zondarr
---

[:octicons-mark-github-16: GitHub](https://github.com/edbfi/zondarr-docker){ class="header-links" target="_blank" rel="noopener" }
[:octicons-container-16: ghcr.io](https://github.com/users/edbfi/packages/container/package/zondarr-docker){ class="header-links" target="_blank" rel="noopener" }

[:octicons-link-16: Source Code](https://github.com/edbfi/zondarr){ class="header-links" target="_blank" rel="noopener" }

<div class="image-logo"><img src="/img/image-logos/zondarr.svg" alt="logo"></div>

!!! question "What is this?"

    Zondarr manages invitations and users for Plex and Jellyfin. The image runs its Python backend and Bun frontend together under s6.

!!! note "Branches and Tags"

    **`:nightly`** is available for amd64 and arm64. It is built from a reviewed, pinned application revision and published after native runtime checks.

    No stable application release has been selected. The `release` and `latest` image tags are not published in this namespace.

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
<tr><td><div id="tag3002" onclick="CopyToClipboard('tag3002');return false;" class="tag-decoration">nightly</div></td><td>Nightly builds</td><td><a href="https://github.com/edbfi/zondarr-docker/commits/nightly" target="_blank">View commits</a></td><td><a href="https://github.com/edbfi/zondarr-docker/actions" target="_blank">View builds</a></td></tr>
    </tbody>
  </table>
</div>

!!! note "Persistent configuration"

    Back up the entire `/config` volume before replacing the container. It contains the SQLite database and the generated `.secret_key` and `.bootstrap_token` files under `/config/data`. Keep the same explicitly supplied `SECRET_KEY`, if you use one.

    Leave `PUBLIC_API_URL` empty to use the frontend's same-origin API proxy. Only the frontend port needs publishing. For HTTPS behind a reverse proxy, set `ORIGIN` and `CSRF_ORIGIN` to the public URL and enable `SECURE_COOKIES`.

## Starting the container

=== "cli"

    ```shell linenums="1"
    docker run --rm \
        --name zondarr \
        -p 3000:3000 \
        -e PUID=1000 \
        -e PGID=1000 \
        -e UMASK=002 \
        -e TZ="Etc/UTC" \
        -v /<host_folder_config>:/config \
        ghcr.io/edbfi/zondarr-docker:nightly
    ```

=== "compose"

    ```yaml linenums="1"
    services:
      zondarr:
        container_name: zondarr
        image: ghcr.io/edbfi/zondarr-docker:nightly
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

## First-run setup

Open the frontend to create the first administrator using the setup token. The container keeps the token in `/config/data/.bootstrap_token` so the frontend can use it during setup. Then configure Plex or Jellyfin.

Native image validation checks both services, setup through the API proxy, migrations, persistence and clean shutdown. It does not connect to your live media servers or validate PostgreSQL.

--8<-- "includes/wireguard.md"
