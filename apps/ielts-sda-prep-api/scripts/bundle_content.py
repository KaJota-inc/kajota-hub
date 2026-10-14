#!/usr/bin/env python3
"""Bundle PhD-prep markdown into the API's ``content/`` dir + a manifest.

Run LOCALLY before committing. The personal source folders do not exist on
Render, so the content is baked into the repo/image here. Because the user
chose "everything, fully public", this commits the campaign docs (including
supervisor notes) into the kajota-hub repo — intended, but worth knowing.

Usage:
    python scripts/bundle_content.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
APP = Path(__file__).resolve().parent.parent          # apps/ielts-sda-prep-api
CONTENT = APP / "content"

# (group label, source dir, glob) — order defines display order.
SOURCES = [
    ("Workflows",      HOME / "Documents/imperial-york-phd/workflows",       "*.md"),
    ("Daily plans",    HOME / "Documents/imperial-york-phd/daily",           "*.md"),
    ("Supervisors",    HOME / "Documents/imperial-york-phd/supervisors",     "*.md"),
    ("Campaign",       HOME / "Documents/imperial-york-phd",                 "*.md"),  # top-level docs
    ("Outreach",       HOME / "Documents/imperial-york-phd/outreach-drafts", "*.md"),
    ("Study materials",HOME / "Documents/ielts-sda-prep/materials",          "*.md"),
]

# Never bundle these (noise / duplicates / html).
SKIP_NAMES = {"daily-drill.template.html"}


def title_of(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^#\s+(.*)", line.strip())
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return path.stem.replace("-", " ").replace("_", " ").title()


def slugify(group: str, name: str) -> str:
    base = f"{group}-{name}".lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base


def main() -> None:
    if CONTENT.exists():
        shutil.rmtree(CONTENT)
    CONTENT.mkdir(parents=True)

    manifest: list[dict] = []
    seen: set[str] = set()

    for group, src, glob in SOURCES:
        if not src.is_dir():
            print(f"  skip (missing): {src}")
            continue
        for f in sorted(src.glob(glob)):
            if f.name in SKIP_NAMES or f.name in seen:
                continue
            # For the top-level "Campaign" scan, only take files directly in
            # the dir (glob already non-recursive) and skip ones claimed by a
            # more specific group above by filename.
            seen.add(f.name)
            slug = slugify(group, f.stem)
            out = CONTENT / f"{slug}.md"
            shutil.copyfile(f, out)
            manifest.append({
                "slug": slug,
                "title": title_of(f),
                "group": group,
                "file": out.name,
                "bytes": out.stat().st_size,
            })
            print(f"  + [{group}] {f.name} -> {out.name}")

    (CONTENT / "manifest.json").write_text(
        json.dumps({"docs": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nBundled {len(manifest)} docs into {CONTENT}")


if __name__ == "__main__":
    main()
