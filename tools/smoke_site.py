# SPDX-License-Identifier: AGPL-3.0-only
"""Load the assembled documentation and its local assets over HTTP."""
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import ProxyHandler, build_opener

from site_overlay import container_names


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = set()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "img") and attrs.get("src"):
            self.assets.add(attrs["src"])
        if tag == "link" and attrs.get("rel") in ("stylesheet", "icon"):
            self.assets.add(attrs["href"])
        if tag == "a" and attrs.get("href"):
            self.links.add(attrs["href"])


def verify_site(base_url):
    opener = build_opener(ProxyHandler({}))
    assets = set()

    def load(url, content_type):
        with opener.open(url, timeout=5) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError("Unexpected response: " + url)
            if response.headers.get_content_type() != content_type:
                raise ValueError("Unexpected content type: " + url)
            content = response.read()
            if not content:
                raise ValueError("Empty response: " + url)
            return content

    def page(route, expected):
        url = urljoin(base_url, route)
        html = load(url, "text/html").decode()
        for text in expected:
            if text not in html:
                raise ValueError(f"Missing {text!r} on {url}")
        parsed = Page()
        parsed.feed(html)
        for asset in parsed.assets:
            resolved = urljoin(url, asset)
            if urlsplit(resolved).netloc == urlsplit(base_url).netloc:
                assets.add(resolved)
        return {urljoin(url, link) for link in parsed.links}

    names = container_names(Path(__file__).resolve().parents[1] / "hweb-content")
    links = page("", ("web.edb.fi", "Container Registry", "e74-hero"))
    for name in sorted(names):
        route = f"containers/{name}/"
        if urljoin(base_url, route) not in links:
            raise ValueError("Container missing from homepage links: " + name)
        page(route, (f"edbfi/{name}", f"ghcr.io/edbfi/{name}"))
        tags = json.loads(load(urljoin(base_url, f"containers/{name}-tags.json"), "application/json"))
        if not isinstance(tags, dict):
            raise ValueError("Invalid container tag object: " + name)
    page("faq/", ("The FAQ content is maintained on hotio.dev",))
    for asset in sorted(assets):
        with opener.open(asset, timeout=5) as response:
            if response.status != 200 or response.geturl() != asset or not response.read():
                raise ValueError("Missing local asset: " + asset)
    if not assets:
        raise ValueError("No local assets were discovered")
    print(f"Loaded homepage, FAQ, {len(names)} container pages/tag objects and {len(assets)} local assets")


if __name__ == "__main__":
    verify_site(sys.argv[1])
