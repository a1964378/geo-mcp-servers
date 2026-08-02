#!/usr/bin/env python3
"""Regenerate README.md tables from servers.yaml.

Usage:
    python scripts/generate_readme.py          # rewrite README.md in place
    python scripts/generate_readme.py --check   # exit 1 if README is stale (CI)

The script only touches the block between the AUTOGEN markers in README.md,
so prose above/below the tables is preserved.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "servers.yaml"
README = ROOT / "README.md"

START = "<!-- AUTOGEN:START -->"
END = "<!-- AUTOGEN:END -->"


def esc(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def slug(title: str) -> str:
    """GitHub heading anchor: lowercase, drop punctuation, spaces -> hyphens."""
    s = title.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)  # remove punctuation (& / , . ( ) ...)
    return s.replace(" ", "-")


def build_tables(data: dict) -> str:
    categories: dict[str, str] = data.get("categories", {})
    servers: list[dict] = data.get("servers") or []

    by_cat: dict[str, list[dict]] = {key: [] for key in categories}
    for srv in servers:
        cat = srv.get("category", "other")
        by_cat.setdefault(cat, []).append(srv)

    total = len(servers)
    lines = [f"**{total} servers tracked** across {sum(1 for v in by_cat.values() if v)} categories.\n"]

    # Table of contents
    lines.append("### Categories\n")
    for key, title in categories.items():
        count = len(by_cat.get(key, []))
        if count:
            lines.append(f"- [{title}](#{slug(title)}) ({count})")
    lines.append("")

    for key, title in categories.items():
        rows = sorted(by_cat.get(key, []), key=lambda s: s.get("name", "").lower())
        if not rows:
            continue
        lines.append(f"### {title}\n")
        lines.append("| Server | Description | Lang | By | Type |")
        lines.append("| --- | --- | --- | --- | --- |")
        for s in rows:
            name = f"[{esc(s.get('name', '?'))}]({s['url']})" if s.get("url") else esc(s.get("name", "?"))
            desc = esc(s.get("description", ""))
            lang = esc(s.get("language", "")) or "—"
            author = esc(s.get("author", "")) or "—"
            kind = "official" if s.get("official") else "community"
            lines.append(f"| {name} | {desc} | {lang} | {author} | {kind} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render(data: dict) -> str:
    block = build_tables(data)
    if README.exists():
        text = README.read_text()
        if START in text and END in text:
            pre = text.split(START)[0]
            post = text.split(END)[1]
            return f"{pre}{START}\n\n{block}\n{END}{post}"
    # No README yet: create a minimal one.
    return (
        "# Geospatial MCP Servers\n\n"
        "A curated, tracked list of Model Context Protocol (MCP) servers for "
        "geospatial, GIS, mapping, and earth-observation work.\n\n"
        "> Edit [`servers.yaml`](servers.yaml), then run "
        "`python scripts/generate_readme.py`. See [CONTRIBUTING.md](CONTRIBUTING.md).\n\n"
        f"{START}\n\n{block}\n{END}\n"
    )


def main() -> int:
    data = yaml.safe_load(DATA.read_text()) or {}
    new = render(data)
    check = "--check" in sys.argv
    current = README.read_text() if README.exists() else ""
    if check:
        if current != new:
            print("README.md is out of date. Run: python scripts/generate_readme.py")
            return 1
        print("README.md is up to date.")
        return 0
    README.write_text(new)
    print(f"Wrote {README.relative_to(ROOT)} ({len(data.get('servers') or [])} servers).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
