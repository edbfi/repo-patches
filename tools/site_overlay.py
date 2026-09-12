# SPDX-License-Identifier: AGPL-3.0-only
"""Apply canonical documentation in a disposable website candidate."""
import json
from pathlib import Path
import shutil

OVERLAY_MAPPING = {"config/mkdocs.yml": "mkdocs.yml", "docs/index.md": "docs/index.md",
               "docs/faq.md": "docs/faq.md", "docs/CNAME": "docs/CNAME",
               "docs/overrides/main.html": "overrides/main.html",
               "assets/img/edbfi.svg": "docs/img/edbfi.svg",
               "assets/stylesheets/extra-custom.css": "docs/stylesheets/extra-custom.css"}



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


def apply_overlay(root, source):
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
    for name in names:
        shutil.copy2(source / "docs/containers" / (name + ".md"), destination)
        tags = destination / (name + "-tags.json")
        if tags.exists():
            json.loads(tags.read_text())
        else:
            tags.write_text("{}\n")
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
