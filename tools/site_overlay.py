# SPDX-License-Identifier: AGPL-3.0-only
"""Apply canonical documentation in a disposable website candidate."""
import json
from pathlib import Path
import shutil


def apply_overlay(root, source):
    names = {p.stem for p in (source / "docs/containers").glob("*.md")}
    if not names or "base-image" not in names:
        raise ValueError("Missing canonical container documentation")
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
        stem = file.name.removesuffix("-tags.json") if file.name.endswith("-tags.json") else file.stem
        if file.is_file() and stem not in names:
            file.unlink()
    for name in names:
        shutil.copy2(source / "docs/containers" / (name + ".md"), destination)
        tags = destination / (name + "-tags.json")
        if tags.exists():
            json.loads(tags.read_text())
        else:
            tags.write_text("{}\n")
    mapping = {"config/mkdocs.yml": "mkdocs.yml", "docs/index.md": "docs/index.md",
               "docs/faq.md": "docs/faq.md", "docs/CNAME": "docs/CNAME",
               "docs/overrides/main.html": "overrides/main.html",
               "assets/img/edbfi.svg": "docs/img/edbfi.svg",
               "assets/stylesheets/extra-custom.css": "docs/stylesheets/extra-custom.css"}
    for old, new in mapping.items():
        dest = root / new
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / old, dest)
    logos = root / "docs/img/image-logos"
    logos.mkdir(parents=True, exist_ok=True)
    kept_logos = names | {"flood"}
    for file in logos.iterdir():
        if file.is_file() and file.stem not in kept_logos: file.unlink()
    for file in (source / "assets/img/image-logos").iterdir():
        if file.is_file() and file.stem in kept_logos: shutil.copy2(file, logos)
    if (root / "docs/CNAME").read_text().strip() != "dc.edb.fi":
        raise ValueError("Unexpected documentation domain")
