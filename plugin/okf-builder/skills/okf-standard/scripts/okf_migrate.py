#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_migrate.py — Migrate an OKF bundle between v0.1 and v0.2 (both directions).

Usage:
    uv run okf_migrate.py [bundle] --to 0.2 [--actor process:okf-migrate] [--dry-run] [--out DIR]
    uv run okf_migrate.py [bundle] --to 0.1 [--keep-extensions] [--dry-run] [--out DIR]

0.1 → 0.2 (lossless):
  - timestamp            → generated: { by: <actor>, at: <timestamp> }
  - # Citations (body)   → sources[] (id cit-n, resource, title) + footnotes [^cit-n]
  - okf_version "0.2" in the root index.md; an entry in log.md

0.2 → 0.1 (lossy unless --keep-extensions):
  - generated.at         → timestamp
  - sources[]            → # Citations with [n] [title](resource); [^id] → [n]
  - verified, status, stale_after, usage_window, generated, sources are removed
    (with --keep-extensions they are kept as extra keys, legal in both specs)
  - okf_version "0.1" in the root index.md; an entry in log.md

--out DIR writes a migrated copy and leaves the source bundle untouched (recommended for 0.2→0.1).
It edits the frontmatter text by key blocks to keep order, comments and unknown keys;
it never re-serializes the whole YAML.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    CITATIONS_RE,
    SUPPORTED_VERSIONS,
    detect_version,
    find_bundle,
    parse_yaml,
    split_frontmatter,
    walk_bundle,
)

DROP_ON_DOWNGRADE = ["verified", "status", "stale_after", "usage_window"]


# --------------------------------------------------------------------------
# Frontmatter as top-level key blocks (keeps the original text)
# --------------------------------------------------------------------------
def fm_blocks(raw: str) -> list[tuple[str | None, list[str]]]:
    """[(key|None for loose comments, lines)] in order."""
    blocks: list[tuple[str | None, list[str]]] = []
    for line in raw.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:", line)
        if m and not line.startswith((" ", "\t")):
            blocks.append((m.group(1), [line]))
        elif blocks and blocks[-1][0] is not None and (line.startswith((" ", "\t", "-")) or not line.strip()):
            blocks[-1][1].append(line)
        else:
            blocks.append((None, [line]))
    # trim trailing blank lines of each block
    out = []
    for k, ls in blocks:
        while ls and not ls[-1].strip():
            ls = ls[:-1]
        if ls:
            out.append((k, ls))
    return out


def blocks_to_raw(blocks: list[tuple[str | None, list[str]]]) -> str:
    return "\n".join(l for _, ls in blocks for l in ls)


def get_block(blocks, key):
    for i, (k, _) in enumerate(blocks):
        if k == key:
            return i
    return -1


def yaml_str(v) -> str:
    s = str(v)
    if re.search(r"[:#{}\[\],&*?|<>=!%@`'\"]|^\s|\s$", s) or s.lower() in ("true", "false", "null", "~", ""):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def norm_ts(ts) -> str:
    """ISO 8601 with an explicit offset; a naive value is assumed to be UTC (and reported)."""
    s = ts.isoformat() if hasattr(ts, "isoformat") else str(ts).strip().strip("'\"")
    if re.search(r"(Z|[+-]\d{2}:\d{2})$", s):
        return s.replace("+00:00", "Z")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s + "T00:00:00Z"
    return s + "Z"


# --------------------------------------------------------------------------
# v0.1 citations <-> v0.2 sources
# --------------------------------------------------------------------------
CIT_ITEM_RE = re.compile(r"^\s*(?:\[(\d+)\]|[-*])\s+(.*\S)\s*$")
MDLINK_RE = re.compile(r"^\[([^\]]*)\]\(([^)\s]+)\)\s*(.*)$")


def parse_citations(body: str):
    """Return (body_without_section, [(n, title, url)])."""
    m = re.search(r"^#\s+Citations\s*$\n?(.*?)(?=^#\s|\Z)", body, re.M | re.S)
    if not m:
        return body, []
    items = []
    n = 0
    for line in m.group(1).splitlines():
        im = CIT_ITEM_RE.match(line)
        if not im:
            continue
        n = int(im.group(1)) if im.group(1) else n + 1
        text = im.group(2)
        lm = MDLINK_RE.match(text)
        if lm:
            title, url = lm.group(1).strip(), lm.group(2)
        elif re.match(r"^\S+$", text):
            title, url = "", text
        else:
            # "url - description" or free text
            parts = text.split(None, 1)
            url, title = (parts[0], parts[1].lstrip("-– ").strip()) if re.match(r"^[a-z]+:|^/|^\.", parts[0]) else ("", text)
            if not url:
                url, title = text, ""
        items.append((n, title, url))
    body = body[: m.start()] + body[m.end():]
    return body.rstrip() + "\n", items


def upgrade_citation_refs(body: str, ids: dict[int, str]) -> str:
    # a bare [n] (not followed by '(' or ':' and not preceded by '^') → [^cit-n]
    def rep(m):
        n = int(m.group(1))
        return f"[^{ids[n]}]" if n in ids else m.group(0)
    return re.sub(r"(?<![\^\[])\[(\d+)\](?![\(:])", rep, body)


def downgrade_footnotes(body: str, id_to_n: dict[str, int]) -> str:
    # remove [^id]: ... definitions
    body = re.sub(r"^\[\^([^\]]+)\]:[^\n]*\n?", lambda m: "" if m.group(1) in id_to_n else m.group(0), body, flags=re.M)
    body = re.sub(r"\[\^([^\]]+)\]", lambda m: f"[{id_to_n[m.group(1)]}]" if m.group(1) in id_to_n else m.group(0), body)
    return body


# --------------------------------------------------------------------------
# Migrating one concept
# --------------------------------------------------------------------------
def migrate_concept(text: str, to: str, actor: str, keep_ext: bool, notes: list[str], rel: str,
                    bundle: Path | None = None, doc_path: Path | None = None) -> str:
    raw, body = split_frontmatter(text)
    if raw is None:
        return text
    fm = parse_yaml(raw)
    blocks = fm_blocks(raw)

    if to == "0.2":
        if "timestamp" in fm and "generated" not in fm:
            i = get_block(blocks, "timestamp")
            ts = norm_ts(fm["timestamp"])
            if not re.search(r"(Z|[+-]\d{2}:\d{2})$", str(fm["timestamp"]).strip("'\"")) and not hasattr(fm["timestamp"], "tzinfo"):
                notes.append(f"{rel}: timestamp has no offset; assumed UTC")
            blocks[i] = ("generated", [f"generated: {{ by: {actor}, at: {ts} }}"])
        elif "timestamp" in fm:
            i = get_block(blocks, "timestamp")
            del blocks[i]
        body2, cits = parse_citations(body)
        if cits and "sources" not in fm:
            ids = {n: f"cit-{n}" for n, _, _ in cits}
            lines = ["sources:"]
            for n, title, url in cits:
                lines.append(f"  - id: {ids[n]}")
                lines.append(f"    resource: {yaml_str(url)}")
                if title:
                    lines.append(f"    title: {yaml_str(title)}")
            blocks.append(("sources", lines))
            body2 = upgrade_citation_refs(body2, ids)
            used = set(re.findall(r"\[\^(cit-\d+)\]", body2))
            defs = [f"[^{ids[n]}]: {title or url}" for n, title, url in cits if ids[n] in used]
            if defs:
                body2 = body2.rstrip() + "\n\n" + "\n".join(defs) + "\n"
            body = body2
        elif cits:
            srcs = [x for x in fm.get("sources") or [] if isinstance(x, dict)]
            by_res = {str(x.get("resource", "")).lstrip("/"): x for x in srcs}
            if all(url.lstrip("/") in by_res for _, _, url in cits):
                # Citations written by an earlier downgrade: restore the footnotes and drop the section
                ids = {n: str(by_res[url.lstrip("/")].get("id") or f"cit-{n}") for n, _, url in cits}
                body2 = upgrade_citation_refs(body2, ids)
                used = set(re.findall(r"\[\^([^\]]+)\]", body2))
                defs = [f"[^{ids[n]}]: {title or url}" for n, title, url in cits
                        if ids[n] in used and not re.search(rf"^\[\^{re.escape(ids[n])}\]:", body2, re.M)]
                if defs:
                    body2 = body2.rstrip() + "\n\n" + "\n".join(defs) + "\n"
                body = body2
            else:
                notes.append(f"{rel}: sources and # Citations differ; Citations section kept as is")
    else:  # to 0.1
        gen = fm.get("generated")
        if isinstance(gen, dict) and gen.get("at") is not None and "timestamp" not in fm:
            i = get_block(blocks, "generated")
            ts_line = f"timestamp: {norm_ts(gen['at'])}"
            if keep_ext:
                blocks.insert(i, ("timestamp", [ts_line]))
            else:
                blocks[i] = ("timestamp", [ts_line])
                notes.append(f"{rel}: generated.by '{gen.get('by')}' dropped")
        elif isinstance(gen, dict) and not keep_ext:
            del blocks[get_block(blocks, "generated")]
        sources = fm.get("sources")
        if isinstance(sources, list) and sources and not CITATIONS_RE.search(body):
            id_to_n, lines = {}, ["# Citations", ""]
            for n, s in enumerate(sources, 1):
                if not isinstance(s, dict):
                    continue
                url = str(s.get("resource", ""))
                if bundle and doc_path and url and not re.match(r"^[a-z][a-z0-9+.-]*:|^/", url):
                    if not (doc_path.parent / url).exists() and (bundle / url).exists():
                        url = "/" + url
                title = s.get("title") or url
                if s.get("id"):
                    id_to_n[str(s["id"])] = n
                lines.append(f"[{n}] [{title}]({url})")
            body = downgrade_footnotes(body, id_to_n).rstrip() + "\n\n" + "\n".join(lines) + "\n"
            if not keep_ext:
                del blocks[get_block(blocks, "sources")]
                if any(k in s for s in sources if isinstance(s, dict) for k in ("author", "usage_count", "last_modified")):
                    notes.append(f"{rel}: credibility signals of sources dropped")
        if not keep_ext:
            for k in DROP_ON_DOWNGRADE:
                i = get_block(blocks, k)
                if i >= 0:
                    del blocks[i]
                    notes.append(f"{rel}: '{k}' dropped")
        if fm.get("type") == "Attested Computation":
            notes.append(f"{rel}: type 'Attested Computation' becomes a generic type in 0.1 (computation keys kept)")

    return "---\n" + blocks_to_raw(blocks) + "\n---\n\n" + body.lstrip("\n")


def set_root_version(index_path: Path, to: str) -> None:
    text = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Index\n"
    raw, body = split_frontmatter(text)
    if raw is None:
        raw = f'okf_version: "{to}"'
    elif re.search(r"^okf_version\s*:", raw, re.M):
        raw = re.sub(r"^okf_version\s*:.*$", f'okf_version: "{to}"', raw, flags=re.M)
    else:
        raw = f'okf_version: "{to}"\n' + raw
    index_path.write_text("---\n" + raw.strip("\n") + "\n---\n\n" + body.lstrip("\n").rstrip("\n") + "\n", encoding="utf-8")


def append_log(log_path: Path, to: str, n: int) -> None:
    today = date.today().isoformat()
    entry = f"* **Migration**: Bundle migrated to OKF v{to} ({n} concepts) with okf-migrate."
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8")
        if f"## {today}" in text:
            text = text.replace(f"## {today}\n", f"## {today}\n{entry}\n", 1)
        else:
            m = re.search(r"^## ", text, re.M)
            text = (text[: m.start()] + f"## {today}\n{entry}\n\n" + text[m.start():]) if m else text.rstrip() + f"\n\n## {today}\n{entry}\n"
    else:
        text = f"# Bundle history\n\n## {today}\n{entry}\n"
    log_path.write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="path to the bundle (default: search upwards for knowledge/)")
    ap.add_argument("--to", required=True, choices=SUPPORTED_VERSIONS, help="target OKF version")
    ap.add_argument("--actor", default="process:okf-migrate", help="generated.by for concepts without an author (0.1→0.2)")
    ap.add_argument("--keep-extensions", action="store_true", help="0.2→0.1: keep v0.2 keys as extensions")
    ap.add_argument("--out", help="write a migrated copy to this directory (the source is left untouched)")
    ap.add_argument("--dry-run", action="store_true", help="report the changes without writing them")
    ap.add_argument("--force", action="store_true", help="migrate even if the detected version already is the target")
    ap.add_argument("--file", action="append", default=[],
                    help="migrate only this concept (path relative to the bundle); repeatable. Leaves index/log alone")
    args = ap.parse_args(argv)

    src = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if src is None or not src.is_dir():
        print("ERROR: bundle not found (knowledge/index.md). Pass its path.", file=sys.stderr)
        return 2
    detected, origin = detect_version(src)
    if args.file:
        notes: list[str] = []
        for rel in args.file:
            fp = src / rel
            new = migrate_concept(fp.read_text(encoding="utf-8"), args.to, args.actor, args.keep_extensions, notes, rel,
                                  bundle=src, doc_path=fp)
            if not args.dry_run:
                fp.write_text(new, encoding="utf-8")
            print(f"{'(dry) ' if args.dry_run else ''}migrated {rel} → {args.to}")
        for n in notes:
            print("  note:", n)
        return 0
    print(f"Source: {src} · detected version {detected} ({origin}) → target {args.to}")
    if detected == args.to and origin == "declared" and not args.force:
        print("Already at the target version; nothing to do (use --force to rewrite).")
        return 0

    dst = src
    if args.out:
        dst = Path(args.out).resolve()
        if not args.dry_run:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    notes: list[str] = []
    changed = 0
    for doc in walk_bundle(src):
        if doc.is_reserved:
            continue
        new = migrate_concept(doc.path.read_text(encoding="utf-8"), args.to, args.actor, args.keep_extensions, notes, doc.rel,
                              bundle=src, doc_path=doc.path)
        if new != doc.path.read_text(encoding="utf-8"):
            changed += 1
            print(f"{'(dry) ' if args.dry_run else ''}migrated {doc.rel}")
            if not args.dry_run:
                (dst / doc.rel).write_text(new, encoding="utf-8")
    if not args.dry_run:
        set_root_version(dst / "index.md", args.to)
        append_log(dst / "log.md", args.to, changed)
    for n in notes:
        print("  note:", n)
    print(f"\n{changed} concepts migrated to OKF v{args.to}{' (dry-run)' if args.dry_run else ''} → {dst}")
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_migrate.py --test)
# --------------------------------------------------------------------------
_V01 = """---
type: Table
title: Orders
# kept comment
timestamp: 2024-05-01T10:00:00Z
owner: data-team
---

Orders, see [1].

# Citations

[1] [Schema](https://example.com/schema)
"""


def _parse(text: str) -> tuple[dict, str]:
    raw, body = split_frontmatter(text)
    return parse_yaml(raw), body


def test_upgrade_01_to_02():
    notes: list[str] = []
    fm, body = _parse(migrate_concept(_V01, "0.2", "process:okf-migrate", False, notes, "orders.md"))
    assert "timestamp" not in fm
    assert fm["generated"]["by"] == "process:okf-migrate"
    assert str(fm["generated"]["at"]).startswith("2024-05-01")
    assert fm["sources"] == [{"id": "cit-1", "resource": "https://example.com/schema", "title": "Schema"}]
    assert fm["owner"] == "data-team"
    assert "[^cit-1]" in body and "# Citations" not in body


def test_round_trip_02_01_02():
    up = migrate_concept(_V01, "0.2", "process:okf-migrate", False, [], "orders.md")
    down = migrate_concept(up, "0.1", "process:okf-migrate", True, [], "orders.md")
    fm_down, body_down = _parse(down)
    assert "timestamp" in fm_down and "# Citations" in body_down and "[1]" in body_down
    again = migrate_concept(down, "0.2", "process:okf-migrate", False, [], "orders.md")
    assert _parse(again) == _parse(up)
    assert "[^cit-1]" in _parse(again)[1]
    assert "# kept comment" in again


def test_main_out_leaves_source_untouched(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.md").write_text('---\nokf_version: "0.1"\n---\n\n# Tables\n\n* [Orders](orders.md) - x\n',
                                  encoding="utf-8")
    (src / "orders.md").write_text(_V01, encoding="utf-8")
    out = tmp_path / "out"
    assert main([str(src), "--to", "0.2", "--out", str(out)]) == 0
    assert (src / "orders.md").read_text(encoding="utf-8") == _V01
    assert "generated:" in (out / "orders.md").read_text(encoding="utf-8")
    assert 'okf_version: "0.2"' in (out / "index.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
