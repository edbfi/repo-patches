# SPDX-License-Identifier: AGPL-3.0-only
"""Apply the canonical documentation overlay to a website tree."""
import json
from pathlib import Path
import re
import shutil

OVERLAY_MAPPING = {"config/mkdocs.yml": "mkdocs.yml", "docs/index.md": "docs/index.md",
               "docs/faq.md": "docs/faq.md", "docs/CNAME": "docs/CNAME",
               "docs/overrides/main.html": "overrides/main.html",
               "assets/img/edbfi.svg": "docs/img/edbfi.svg",
               "assets/stylesheets/extra-custom.css": "docs/stylesheets/extra-custom.css"}

# The table body Hotio's `tags` job renders into each container page, matched
# the way its `sed -z` matches it (from the first opening tag to the last
# closing tag).
TAGS_TABLE = re.compile(rb'<tbody id="tags-table-body">.*</tbody>', re.S)


def container_names(source):
    names = {p.stem for p in (source / "docs/containers").glob("*.md")}
    if not names or "base-image" not in names:
        raise ValueError("Missing canonical container documentation")
    return names


def excluded_path(path, names):
    """Paths omitted by the canonical maintained-container inventory."""
    parts = Path(path).parts
    if parts[:2] in (("docs", "scripts"), ("docs", "guides")):
        return True
    if len(parts) == 3 and parts[:2] == ("docs", "containers"):
        name = parts[-1]
        stem = name.removesuffix("-tags.json") if name.endswith("-tags.json") else Path(name).stem
        return stem not in names
    if len(parts) == 4 and parts[:3] == ("docs", "img", "image-logos"):
        return Path(parts[-1]).stem not in names | {"flood"}
    return False


def container_page(page, published):
    """The canonical page with the tags table the destination last published."""
    if published is None:
        return page
    table = TAGS_TABLE.search(published)
    if table is None:
        return page
    ours = TAGS_TABLE.search(page)
    if ours is None:
        raise ValueError("Canonical container page has no tags table")
    return page[:ours.start()] + table.group(0) + page[ours.end():]


def apply_overlay(root, source, published):
    """Overlay `source` onto the website tree at `root`.

    `published(path)` returns the destination's current bytes for a
    repository path, or None. Tag JSON and rendered tags tables come only from
    there: Hotio's tag data is never kept, and a missing file starts as `{}`.
    """
    names = container_names(source)
    for required in ("includes/wireguard.md", "includes/annotations.md",
                     "docs/javascripts/tablesort.js", "docs/javascripts/tagcopy.js",
                     "docs/stylesheets/extra-13.css"):
        if not (root / required).is_file():
            raise ValueError("Missing inherited site dependency: " + required)
    for folder in (root / "docs/scripts", root / "docs/guides"):
        if folder.exists(): shutil.rmtree(folder)
    destination = root / "docs/containers"
    destination.mkdir(parents=True, exist_ok=True)
    for file in destination.iterdir():
        if file.is_file() and excluded_path(file.relative_to(root), names):
            file.unlink()
    for name in sorted(names):
        page = (source / "docs/containers" / (name + ".md")).read_bytes()
        page = container_page(page, published("docs/containers/" + name + ".md"))
        (destination / (name + ".md")).write_bytes(page)
        tags = published("docs/containers/" + name + "-tags.json")
        if tags is None:
            tags = b"{}\n"
        json.loads(tags)
        (destination / (name + "-tags.json")).write_bytes(tags)
    for old, new in OVERLAY_MAPPING.items():
        dest = root / new
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / old, dest)
    logos = root / "docs/img/image-logos"
    logos.mkdir(parents=True, exist_ok=True)
    kept_logos = names | {"flood"}
    for file in logos.iterdir():
        if file.is_file() and excluded_path(file.relative_to(root), names): file.unlink()
    for file in (source / "assets/img/image-logos").iterdir():
        if file.is_file() and file.stem in kept_logos: shutil.copy2(file, logos)
    if (root / "docs/CNAME").read_text().strip() != "web.edb.fi":
        raise ValueError("Unexpected documentation domain")
