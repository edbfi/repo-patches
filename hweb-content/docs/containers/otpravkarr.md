---
hide:
  - toc
title: edbfi/otpravkarr
---

[:octicons-mark-github-16: GitHub](https://github.com/edbfi/otpravkarr-docker){ class="header-links" target="_blank" rel="noopener" }
[:octicons-container-16: ghcr.io](https://github.com/users/edbfi/packages/container/package/otpravkarr-docker){ class="header-links" target="_blank" rel="noopener" }

[:octicons-link-16: Source Code](https://github.com/edbfi/otpravkarr){ class="header-links" target="_blank" rel="noopener" }

<div class="image-logo"><img src="/img/image-logos/otpravkarr.svg" alt="logo"></div>

!!! question "What is this?"

    Otpravkarr provisions Plex users into Dispatcharr and provides each user with their own IPTV credentials and playlist access.

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
<tr><td><div id="tag3002" onclick="CopyToClipboard('tag3002');return false;" class="tag-decoration">nightly</div></td><td>Nightly builds</td><td><a href="https://github.com/edbfi/otpravkarr-docker/commits/nightly" target="_blank">View commits</a></td><td><a href="https://github.com/edbfi/otpravkarr-docker/actions" target="_blank">View builds</a></td></tr>
    </tbody>
  </table>
</div>

!!! note "Persistent configuration"

    Keep both your `/config` volume and the same `OTPRAVKARR_SECRET` when replacing the container. The secret derives the encryption keys for stored configuration and user credentials. Back up both before upgrading.

    Generate the secret once with `openssl rand -base64 48`, then store it outside version control. Provide it through an environment file, as shown below. Do not generate a new value at each startup. Set `ORIGIN` to the URL users visit.

    If you explicitly configure `DATABASE_PATH`, it must point to an existing database. Fix a missing mount rather than creating a replacement database.

## Starting the container

=== "cli"

    ```shell linenums="1"
    docker run --rm \
        --name otpravkarr \
        -p 3000:3000 \
        -e PUID=1000 \
        -e PGID=1000 \
        -e UMASK=002 \
        -e TZ="Etc/UTC" \
        --env-file /<host_folder_config>/otpravkarr.env \
        -e ORIGIN="https://otpravkarr.example.com" \
        -v /<host_folder_config>:/config \
        ghcr.io/edbfi/otpravkarr-docker:nightly
    ```

=== "compose"

    ```yaml linenums="1"
    services:
      otpravkarr:
        container_name: otpravkarr
        image: ghcr.io/edbfi/otpravkarr-docker:nightly
        env_file:
          - ./otpravkarr.env
        ports:
          - "3000:3000"
        environment:
          - PUID=1000
          - PGID=1000
          - UMASK=002
          - TZ=Etc/UTC
          - ORIGIN=https://otpravkarr.example.com
        volumes:
          - /<host_folder_config>:/config
    ```

## First-run setup

The environment file must define `OTPRAVKARR_SECRET=<your-saved-secret>`. On first startup, use the one-time bootstrap token from the container logs to complete the setup wizard and configure Plex and Dispatcharr.

`/api/health` reports `degraded` until the integrations are configured. Image validation checks local startup, migration and encryption behavior; it does not connect to your live services.

--8<-- "includes/wireguard.md"
