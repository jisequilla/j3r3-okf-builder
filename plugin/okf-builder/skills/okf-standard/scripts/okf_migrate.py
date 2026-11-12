#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_migrate.py — Migrate an OKF bundle between v0.1 and v0.2 (both directions),
and from the knowledge/2.0 profile to knowledge/3.0.

Usage:
    uv run okf_migrate.py [bundle] --to 0.2 [--actor process:okf-migrate] [--dry-run] [--out DIR]
    uv run okf_migrate.py [bundle] --to 0.1 [--keep-extensions] [--dry-run] [--out DIR]
    uv run okf_migrate.py [bundle] --profile knowledge/3.0 [--to 0.2] [--dry-run] [--out DIR]

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

knowledge/2.0 → knowledge/3.0 (--profile; okf_version is not changed):
  - every non-hidden root directory except fragments/ and projections/, and every root
    .md other than index.md, log.md, project.md and the Conflict Log, move under base/
  - links in every .md (reserved files included), sources[].resource and the ADR path
    fields supersedes and superseded_by are rewritten:
    a bundle path into a moved path (/decisions/x.md → /base/decisions/x.md), and a
    relative path whose target is on the other side of the move (recomputed); any
    other path (/standard/..., a repo-relative resource) is left as it is
  - the root index.md, base/index.md and every index below base/ are regenerated
    (# Notes kept); okf_profile "knowledge/3.0" in the root index.md; an entry in log.md
  - what lint's scan leaves out is left unedited: at the root, the paths .okfignore matches,
    every nested bundle (an operational instance included) and a root directory that holds
    nothing else but its index.md (a kind's directory of instances) stay where they are;
    inside a directory that moves they move with it, and each .okfignore entry anchored
    under that directory follows them (decisions/drafts/ → base/decisions/drafts/); a nested
    bundle is migrated on its own (okf_migrate.py <its directory>)
  With --to as well, the profile step runs first and the version step walks its result.

Both steps migrate only what lint reads: the paths .okfignore matches and nested bundles are
left byte-identical (a plain directory of Markdown without OKF frontmatter is read as today).

--out DIR writes a migrated copy and leaves the source bundle untouched (recommended for 0.2→0.1).
It edits the frontmatter text by key blocks to keep order, comments and unknown keys;
it never re-serializes the whole YAML.
"""
from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    BASE_DIR,
    CITATIONS_RE,
    LAYER_DIRS,
    OKFIGNORE,
    PROFILE_30,
    SUPPORTED_VERSIONS,
    declared_profile,
    detect_version,
    find_bundle,
    load_doc,
    parse_yaml,
    root_frontmatter,
    scan_bundle,
    split_frontmatter,
    walk_bundle,
)
from okf_index import index_targets, regenerate  # noqa: E402
from okf_profile import DOMAIN_BUNDLE  # noqa: E402

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


def set_root_key(index_path: Path, key: str, value: str) -> None:
    """Set `key: "value"` in the root index.md frontmatter; a missing key goes first."""
    text = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Index\n"
    raw, body = split_frontmatter(text)
    line = f'{key}: "{value}"'
    if raw is None:
        raw = line
    elif re.search(rf"^{key}\s*:", raw, re.M):
        raw = re.sub(rf"^{key}\s*:.*$", line, raw, flags=re.M)
    else:
        raw = line + "\n" + raw
    index_path.write_text("---\n" + raw.strip("\n") + "\n---\n\n" + body.lstrip("\n").rstrip("\n") + "\n", encoding="utf-8")


def set_root_version(index_path: Path, to: str) -> None:
    set_root_key(index_path, "okf_version", to)


def append_log(log_path: Path, to: str, n: int, entry: str | None = None) -> None:
    today = date.today().isoformat()
    entry = entry or f"* **Migration**: Bundle migrated to OKF v{to} ({n} concepts) with okf-migrate."
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


# --------------------------------------------------------------------------
# Profile knowledge/2.0 -> knowledge/3.0
# --------------------------------------------------------------------------
ROOT_KEEP = {"index.md", "log.md", "project.md"}
EXTERNAL_RE = re.compile(r"^[a-z][a-z0-9+.-]*:")
MD_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)")
RESOURCE_RE = re.compile(r"(\bresource\s*:\s*)([\"']?)([^\s\"',}\]]+)")
PATH_KEYS = {"supersedes", "superseded_by"}
PATH_VALUE_RE = re.compile(r"([\"']?)([^\s\"',\[\]{}]+)")


class Move:
    """The 2.0 -> 3.0 move, as bundle-relative posix paths (lexical: nothing is read from disk)."""

    def __init__(self, dirs: list[str], files: list[str]):
        self.dirs, self.files = set(dirs), set(files)

    def moved(self, rel: str) -> bool:
        if rel == ".." or rel.startswith("../"):
            return False
        return rel.split("/")[0] in self.dirs or rel in self.files

    def new(self, rel: str) -> str:
        return f"{BASE_DIR}/{rel}" if self.moved(rel) else rel

    def target(self, target: str, doc_rel: str) -> str | None:
        """The rewritten link target, or None when it stays as it is."""
        if EXTERNAL_RE.match(target) or target.startswith("#"):
            return None
        path, sep, anchor = target.partition("#")
        if not path:
            return None
        slash = "/" if path.endswith("/") and path != "/" else ""
        if path.startswith("/"):
            rel = posixpath.normpath(path.lstrip("/"))
            return f"/{self.new(rel)}{slash}{sep}{anchor}" if self.moved(rel) else None
        doc_dir = posixpath.dirname(doc_rel)
        rel = posixpath.normpath(posixpath.join(doc_dir, path))
        if self.moved(rel) == self.moved(doc_rel):
            return None
        new_dir = posixpath.dirname(self.new(doc_rel)) or "."
        return posixpath.relpath(self.new(rel), new_dir) + slash + sep + anchor


def left_out(bundle: Path) -> list[str]:
    """The paths lint's scan leaves out that migrate leaves alone: what .okfignore excludes and every nested bundle
    (an operational instance included), a directory with a trailing '/'. Non-OKF directories are not among them."""
    sc = scan_bundle(bundle)
    return [*sc.ignored, *sc.nested]


def _under(rel: str, out: list[str]) -> bool:
    return any(rel == o or (o.endswith("/") and rel.startswith(o)) for o in out)


def bundle_docs(bundle: Path, out: list[str] | None = None) -> list:
    """The .md walk_bundle reads, less those under a left_out path: the documents migrate edits."""
    out = left_out(bundle) if out is None else out
    return [d for d in walk_bundle(bundle) if not _under(d.rel, out)]


def is_instance(bundle: Path) -> bool:
    """A nested bundle is an operational instance when its root index.md declares a kind other than Domain Bundle,
    read as the raw value (a 2.0 bundle being migrated has no kinds to resolve it against)."""
    kind = root_frontmatter(bundle).get("kind")
    return kind is not None and str(kind) != DOMAIN_BUNDLE


def profile_moves(bundle: Path) -> tuple[list[str], list[str]]:
    """(root directories, root concepts) that move under base/. A left_out path stays at the root, and so does a
    directory that holds at least one operational instance and no document migrate reads besides its own index.md
    (the directory of a kind's instances, ADR-0039 decision 3). A directory that holds only ignored paths or nested
    bundles without kind moves, carrying them."""
    sc = scan_bundle(bundle)
    out = [*sc.ignored, *sc.nested]
    read = {d.rel for d in bundle_docs(bundle, out)}
    instances = [n for n in sc.nested if is_instance(bundle / n)]

    def stays(name: str) -> bool:
        pre = name + "/"
        if _under(pre, out):
            return True
        holds = any(i.startswith(pre) and i != pre for i in instances)
        return holds and not any(r.startswith(pre) and r != pre + "index.md" for r in read)

    dirs = [p.name for p in sorted(bundle.iterdir())
            if p.is_dir() and not p.name.startswith(".") and p.name not in LAYER_DIRS and not stays(p.name)]
    files = [p.name for p in sorted(bundle.iterdir())
             if p.is_file() and p.suffix == ".md" and p.name not in ROOT_KEEP and not _under(p.name, out)
             and (load_doc(bundle, p).frontmatter or {}).get("type") != "Conflict Log"]
    return dirs, files


def rewrite_paths(text: str, doc_rel: str, move: Move) -> str:
    """Rewrite the body links, the sources[].resource and the PATH_KEYS values of one .md,
    keeping every other byte."""
    def sub(m: re.Match, group: int) -> str:
        new = move.target(m.group(group), doc_rel)
        if new is None:
            return m.group(0)
        start, end = m.start(group) - m.start(0), m.end(group) - m.start(0)
        return m.group(0)[:start] + new + m.group(0)[end:]

    lines = text.split("\n")
    body_start = 0
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            block = None
            for i in range(1, end):
                key = re.match(r"^([A-Za-z_][\w-]*)\s*:", lines[i])
                if key:
                    block = key.group(1)
                if block == "sources":
                    lines[i] = RESOURCE_RE.sub(lambda m: sub(m, 3), lines[i])
                elif block in PATH_KEYS:
                    start = key.end() if key else 0
                    value, hash_, comment = lines[i][start:].partition(" #")
                    lines[i] = lines[i][:start] + PATH_VALUE_RE.sub(lambda m: sub(m, 2), value) + hash_ + comment
            body_start = end + 1
    body = MD_LINK_RE.sub(lambda m: sub(m, 2), "\n".join(lines[body_start:]))
    return "\n".join([*lines[:body_start], body])


def rewrite_okfignore(text: str, dirs: list[str]) -> str:
    """Prefix base/ to each .okfignore entry anchored under a moved root directory, so the path it names stays
    ignored at its new place (decisions/drafts/ → base/decisions/drafts/). An entry with no '/' but a trailing one
    matches a name at any depth and is kept, as are comments, blank lines and entries whose first segment is a glob."""
    def entry(line: str) -> str:
        body = line.rstrip()
        if not body or body.startswith("#"):
            return line
        prefix = body[0] if body[0] in "!\\" else ""
        pat = body[len(prefix):]
        lead = "/" if pat.startswith("/") else ""
        rest = pat[len(lead):]
        if "/" not in rest.rstrip("/") and not lead:
            return line
        if rest.split("/", 1)[0] not in dirs:
            return line
        return prefix + lead + BASE_DIR + "/" + rest + line[len(body):]

    return "\n".join(entry(line) for line in text.split("\n"))


def migrate_profile(bundle: Path, target: str, dry_run: bool) -> int:
    dirs, files = profile_moves(bundle)
    clash = [n for n in dirs + files if (bundle / BASE_DIR / n).exists()]
    if clash:
        print(f"ERROR: base/ already holds {', '.join(clash)}; move them by hand first.", file=sys.stderr)
        return 1
    move = Move(dirs, files)
    rewritten = {}
    for doc in bundle_docs(bundle):
        text = doc.path.read_text(encoding="utf-8")
        new = rewrite_paths(text, doc.rel, move)
        if new != text:
            rewritten[doc.rel] = new
    ignore = bundle / OKFIGNORE
    ignore_text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    new_ignore = rewrite_okfignore(ignore_text, dirs)
    dry = "(dry) " if dry_run else ""
    for n in dirs:
        print(f"{dry}move {n}/ → {BASE_DIR}/{n}/")
    for n in files:
        print(f"{dry}move {n} → {BASE_DIR}/{n}")
    for rel in rewritten:
        print(f"{dry}rewrote links in {move.new(rel)}")
    if new_ignore != ignore_text:
        print(f"{dry}rewrote {OKFIGNORE}")
    if not dry_run:
        if new_ignore != ignore_text:
            ignore.write_text(new_ignore, encoding="utf-8")
        (bundle / BASE_DIR).mkdir(exist_ok=True)
        for n in dirs + files:
            shutil.move(str(bundle / n), str(bundle / BASE_DIR / n))
        for rel, text in rewritten.items():
            (bundle / move.new(rel)).write_text(text, encoding="utf-8")
        set_root_key(bundle / "index.md", "okf_profile", target)
        regenerate(bundle, [bundle, *index_targets(bundle, bundle / BASE_DIR)])
        append_log(bundle / "log.md", "", 0, entry=(
            f"* **Migration**: Bundle migrated to profile {target} ({len(dirs)} directories and {len(files)} "
            f"root concepts moved under base/; links rewritten in {len(rewritten)} files) with okf-migrate."))
    print(f"\nProfile {target}: {len(dirs)} directories and {len(files)} root concepts moved under base/, "
          f"links rewritten in {len(rewritten)} files{' (dry-run)' if dry_run else ''} → {bundle}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="path to the bundle (default: search upwards for knowledge/)")
    ap.add_argument("--to", choices=SUPPORTED_VERSIONS, help="target OKF version")
    ap.add_argument("--profile", choices=(PROFILE_30,), help="target knowledge profile (moves the typed directories under base/)")
    ap.add_argument("--actor", default="process:okf-migrate", help="generated.by for concepts without an author (0.1→0.2)")
    ap.add_argument("--keep-extensions", action="store_true", help="0.2→0.1: keep v0.2 keys as extensions")
    ap.add_argument("--out", help="write a migrated copy to this directory (the source is left untouched)")
    ap.add_argument("--dry-run", action="store_true", help="report the changes without writing them")
    ap.add_argument("--force", action="store_true", help="migrate even if the bundle already is at the target")
    ap.add_argument("--file", action="append", default=[],
                    help="migrate only this concept (path relative to the bundle); repeatable. Leaves index/log alone")
    args = ap.parse_args(argv)
    if args.file and args.profile:
        ap.error("--profile migrates the whole bundle; it cannot be combined with --file")
    if args.file and not args.to:
        ap.error("--file needs --to")
    if not args.to and not args.profile:
        ap.error("at least one of --to or --profile is required")

    src = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if src is None or not src.is_dir():
        print("ERROR: bundle not found (knowledge/index.md). Pass its path.", file=sys.stderr)
        return 2
    if args.file:
        detected, origin = detect_version(src)
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
    profile_todo = version_todo = False
    if args.profile:
        current = declared_profile(src)
        print(f"Source: {src} · profile {current or 'none (knowledge/2.0)'} → target {args.profile}")
        profile_todo = current != args.profile or args.force
        if not profile_todo:
            print(f"Already {args.profile}; nothing to do for the profile (use --force to rewrite).")
    if args.to:
        detected, origin = detect_version(src)
        print(f"Source: {src} · detected version {detected} ({origin}) → target {args.to}")
        version_todo = not (detected == args.to and origin == "declared" and not args.force)
        if not version_todo:
            print("Already at the target version; nothing to do (use --force to rewrite).")
    if not profile_todo and not version_todo:
        return 0

    dst = src
    if args.out:
        dst = Path(args.out).resolve()
        if not args.dry_run:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    # Every step reads and writes `work`: the copy when --out, the source otherwise (read-only under --dry-run)
    work = dst if not args.dry_run else src

    if profile_todo:
        rc = migrate_profile(work, args.profile, args.dry_run)
        if rc or not version_todo:
            return rc

    notes: list[str] = []
    changed = 0
    for doc in bundle_docs(work):
        if doc.is_reserved:
            continue
        new = migrate_concept(doc.path.read_text(encoding="utf-8"), args.to, args.actor, args.keep_extensions, notes, doc.rel,
                              bundle=work, doc_path=doc.path)
        if new != doc.path.read_text(encoding="utf-8"):
            changed += 1
            print(f"{'(dry) ' if args.dry_run else ''}migrated {doc.rel}")
            if not args.dry_run:
                (work / doc.rel).write_text(new, encoding="utf-8")
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


_FRAGMENT_02 = """---
type: Knowledge Fragment
title: Weekly meeting
status: draft
occurred_at: 2026-10-31
origin: Weekly meeting
participants: [human:alice, okf-builder/claude-opus-5-5]
distillation_status: pending
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T18:00:00Z }
---

# Record

Text.
"""
_FRAGMENT_KEYS = ("occurred_at", "origin", "participants", "distillation_status")


def test_fragment_fields_survive_round_trip_02_01_02():
    want = {k: _parse(_FRAGMENT_02)[0][k] for k in _FRAGMENT_KEYS}
    down = migrate_concept(_FRAGMENT_02, "0.1", "process:okf-migrate", False, [], "fragments/f.md")
    assert {k: _parse(down)[0].get(k) for k in _FRAGMENT_KEYS} == want
    again = migrate_concept(down, "0.2", "process:okf-migrate", False, [], "fragments/f.md")
    assert {k: _parse(again)[0].get(k) for k in _FRAGMENT_KEYS} == want


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


# --------------------------------------------------------------------------
# Profile tests
# --------------------------------------------------------------------------
_GEN = "generated: { by: okf-builder/test, at: 2026-10-31T18:00:00Z }\n"


def _concept(t: str, title: str, extra: str = "", body: str = "Text.\n") -> str:
    return f"---\ntype: {t}\ntitle: {title}\ndescription: {title}.\n{_GEN}{extra}---\n\n{body}"


def _bundle_20(tmp: Path) -> Path:
    """A knowledge/2.0 bundle with every kind of path the profile migration must (or must not) touch."""
    k = tmp / "knowledge"
    for d in ("decisions", "references/skills", "fragments", ".obsidian"):
        (k / d).mkdir(parents=True)
    (k / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\n---\n\n# Project\n\n'
                                "* [P](project.md) - P.\n\n# Notes\n\nKept by hand.\n", encoding="utf-8")
    (k / "log.md").write_text("# Bundle history\n\n## 2026-10-31\n"
                              "* **Creation**: [ADR-0001](decisions/ADR-0001-x.md) and [glossary](glossary.md).\n",
                              encoding="utf-8")
    (k / "project.md").write_text(_concept(
        "Project", "P",
        "sources:\n  - id: s1\n    resource: /standard/OKF-STANDARD.md\n  - { id: s2, resource: /tools }\n"
        "  - id: s3\n    resource: tools/export_m365.py\n",
        "See [the ADR](/decisions/ADR-0001-x.md#context), [decisions](decisions/index.md), "
        "[site](https://example.com/decisions/x.md) and [top](#purpose).\n"), encoding="utf-8")
    (k / "conflict-log.md").write_text(_concept("Conflict Log", "Conflicts", body="[ADR](decisions/ADR-0001-x.md)\n"),
                                       encoding="utf-8")
    (k / "glossary.md").write_text(_concept("Glossary", "Glossary", body="Back to [P](project.md).\n"), encoding="utf-8")
    (k / "decisions" / "index.md").write_text("# decisions\n\n> Decisions.\n\n* [X](ADR-0001-x.md) - X.\n",
                                              encoding="utf-8")
    (k / "decisions" / "ADR-0001-x.md").write_text(_concept(
        "Architecture Decision", "X",
        "sources:\n  - id: f\n    resource: /fragments/2026-10-31-m.md\n  - id: r\n    resource: \"../fragments/2026-10-31-m.md\"\n"
        "  - id: d\n    resource: docs/bench.md\n",
        "[P](../project.md), [ref](../references/okf.md), [abs](/references/okf.md), [frag](../fragments/2026-10-31-m.md)"
        " and ![img](../references/okf.md).\n"), encoding="utf-8")
    (k / "decisions" / "ADR-0002-y.md").write_text(_concept(
        "Architecture Decision", "Y",
        "decision_status: superseded\nsuperseded_by: /decisions/ADR-0001-x.md  # the newer one\n"
        "supersedes:\n  - \"/decisions/ADR-0000-z.md#context\"\n  - /standard/OKF-STANDARD.md\n  - ADR-0000-z.md\n"),
        encoding="utf-8")
    (k / "references" / "index.md").write_text("# references\n\n* [OKF](okf.md) - OKF.\n", encoding="utf-8")
    (k / "references" / "okf.md").write_text(_concept("Reference", "OKF"), encoding="utf-8")
    (k / "references" / "skills" / "index.md").write_text("# skills\n\n_(empty)_\n", encoding="utf-8")
    (k / "fragments" / "index.md").write_text("# fragments\n\n* [M](2026-10-31-m.md) - M.\n", encoding="utf-8")
    (k / "fragments" / "2026-10-31-m.md").write_text(_concept(
        "Knowledge Fragment", "M",
        "occurred_at: 2026-10-31\norigin: Weekly\nparticipants: [human:alice]\ndistillation_status: distilled\n"
        "sources:\n  - { id: a, resource: /decisions/ADR-0001-x.md, title: X }\n",
        "Distilled into [X](../decisions/ADR-0001-x.md).\n"), encoding="utf-8")
    (k / ".obsidian" / "notes.md").write_text("[x](/decisions/ADR-0001-x.md)\n", encoding="utf-8")
    return k


def _tree(k: Path) -> dict[str, str]:
    return {p.relative_to(k).as_posix(): p.read_text(encoding="utf-8") for p in sorted(k.rglob("*")) if p.is_file()}


def test_profile_moves_dirs_and_root_concepts(tmp_path):
    k = _bundle_20(tmp_path)
    assert main([str(k), "--profile", "knowledge/3.0"]) == 0
    assert sorted(p.name for p in k.iterdir()) == [".obsidian", "base", "conflict-log.md", "fragments", "index.md",
                                                   "log.md", "project.md"]
    assert sorted(p.name for p in (k / "base").iterdir()) == ["decisions", "glossary.md", "index.md", "references"]
    assert (k / "base" / "references" / "skills" / "index.md").is_file()
    root = (k / "index.md").read_text(encoding="utf-8")
    assert 'okf_profile: "knowledge/3.0"' in root and 'okf_version: "0.2"' in root
    assert "* [base](base/index.md) - The project's knowledge, in typed directories." in root
    assert "* [fragments](fragments/index.md) - " in root and "Kept by hand." in root
    base = (k / "base" / "index.md").read_text(encoding="utf-8")
    assert "* [decisions](decisions/index.md) - Decisions." in base and "* [Glossary](glossary.md)" in base
    log = (k / "log.md").read_text(encoding="utf-8")
    assert log.count("**Migration**") == 1


def test_profile_rewrites_absolute_links(tmp_path):
    k = _bundle_20(tmp_path)
    main([str(k), "--profile", "knowledge/3.0"])
    project = (k / "project.md").read_text(encoding="utf-8")
    assert "[the ADR](/base/decisions/ADR-0001-x.md#context)" in project
    assert "[decisions](base/decisions/index.md)" in project
    assert "(https://example.com/decisions/x.md)" in project and "[top](#purpose)" in project
    adr = (k / "base" / "decisions" / "ADR-0001-x.md").read_text(encoding="utf-8")
    assert "[abs](/base/references/okf.md)" in adr and "[ref](../references/okf.md)" in adr
    assert "![img](../references/okf.md)" in adr
    assert "[x](/decisions/ADR-0001-x.md)" in (k / ".obsidian" / "notes.md").read_text(encoding="utf-8")


def test_profile_rewrites_relative_links_across_the_move(tmp_path):
    k = _bundle_20(tmp_path)
    main([str(k), "--profile", "knowledge/3.0"])
    frag = (k / "fragments" / "2026-10-31-m.md").read_text(encoding="utf-8")
    assert "Distilled into [X](../base/decisions/ADR-0001-x.md)." in frag
    adr = (k / "base" / "decisions" / "ADR-0001-x.md").read_text(encoding="utf-8")
    assert "[P](../../project.md)" in adr and "[frag](../../fragments/2026-10-31-m.md)" in adr
    assert "Back to [P](../project.md)." in (k / "base" / "glossary.md").read_text(encoding="utf-8")
    log = (k / "log.md").read_text(encoding="utf-8")
    assert "[ADR-0001](base/decisions/ADR-0001-x.md) and [glossary](base/glossary.md)" in log
    assert "[ADR](base/decisions/ADR-0001-x.md)" in (k / "conflict-log.md").read_text(encoding="utf-8")


def test_profile_rewrites_sources_and_leaves_repo_paths(tmp_path):
    k = _bundle_20(tmp_path)
    main([str(k), "--profile", "knowledge/3.0"])
    frag, _ = _parse((k / "fragments" / "2026-10-31-m.md").read_text(encoding="utf-8"))
    assert frag["sources"] == [{"id": "a", "resource": "/base/decisions/ADR-0001-x.md", "title": "X"}]
    adr, _ = _parse((k / "base" / "decisions" / "ADR-0001-x.md").read_text(encoding="utf-8"))
    assert [s["resource"] for s in adr["sources"]] == ["/fragments/2026-10-31-m.md", "../../fragments/2026-10-31-m.md",
                                                       "docs/bench.md"]
    proj, _ = _parse((k / "project.md").read_text(encoding="utf-8"))
    assert [s["resource"] for s in proj["sources"]] == ["/standard/OKF-STANDARD.md", "/tools", "tools/export_m365.py"]


def test_profile_rewrites_adr_path_fields(tmp_path):
    k = _bundle_20(tmp_path)
    main([str(k), "--profile", "knowledge/3.0"])
    text = (k / "base" / "decisions" / "ADR-0002-y.md").read_text(encoding="utf-8")
    assert "superseded_by: /base/decisions/ADR-0001-x.md  # the newer one\n" in text
    adr, _ = _parse(text)
    assert adr["supersedes"] == ["/base/decisions/ADR-0000-z.md#context", "/standard/OKF-STANDARD.md", "ADR-0000-z.md"]


def test_profile_result_lints_clean(tmp_path):
    from okf_lint import lint

    k = _bundle_20(tmp_path)
    main([str(k), "--profile", "knowledge/3.0"])
    rep, _, _ = lint(k)
    assert rep.errors == [] and not rep.profile_outdated
    assert not [i for i in rep.items if i["code"] in ("BROKEN_LINK", "INDEX_BROKEN", "INDEX_STALE")], rep.items


def test_profile_idempotent_on_30(tmp_path, capsys):
    k = _bundle_20(tmp_path)
    main([str(k), "--profile", "knowledge/3.0"])
    before = _tree(k)
    capsys.readouterr()
    assert main([str(k), "--profile", "knowledge/3.0"]) == 0
    assert "Already knowledge/3.0" in capsys.readouterr().out
    assert _tree(k) == before
    assert main([str(k), "--profile", "knowledge/3.0", "--to", "0.2"]) == 0
    assert _tree(k) == before


def test_profile_dry_run_and_out_leave_source(tmp_path):
    k = _bundle_20(tmp_path)
    before = _tree(k)
    assert main([str(k), "--profile", "knowledge/3.0", "--dry-run"]) == 0
    assert _tree(k) == before
    out = tmp_path / "out"
    assert main([str(k), "--profile", "knowledge/3.0", "--out", str(out)]) == 0
    assert _tree(k) == before and (out / "base" / "decisions" / "ADR-0001-x.md").is_file()


def test_profile_then_version_walks_the_destination(tmp_path):
    from okf_lint import lint

    k = _bundle_20(tmp_path)
    out = tmp_path / "out"
    assert main([str(k), "--profile", "knowledge/3.0", "--to", "0.1", "--keep-extensions", "--out", str(out)]) == 0
    assert not (out / "decisions").exists()
    fm, _ = _parse((out / "base" / "decisions" / "ADR-0001-x.md").read_text(encoding="utf-8"))
    assert "timestamp" in fm
    root = (out / "index.md").read_text(encoding="utf-8")
    assert 'okf_version: "0.1"' in root and 'okf_profile: "knowledge/3.0"' in root
    assert (out / "log.md").read_text(encoding="utf-8").count("**Migration**") == 2
    rep, _, _ = lint(out)
    assert not [i for i in rep.items if i["code"] == "PROFILE_OUTSIDE_LAYER"]


def test_option_combinations(tmp_path, capsys):
    import pytest

    k = _bundle_20(tmp_path)
    for argv, msg in (([], "at least one of --to or --profile"),
                      (["--profile", "knowledge/3.0", "--to", "0.2", "--file", "project.md"],
                       "--profile migrates the whole bundle"),
                      (["--file", "project.md"], "--file needs --to")):
        with pytest.raises(SystemExit):
            main([str(k), *argv])
        assert msg in capsys.readouterr().err


# --------------------------------------------------------------------------
# What lint's scan leaves out (.okfignore, nested bundles, instances) stays alone
# --------------------------------------------------------------------------
def _lines(out: str, *prefixes: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith(prefixes)]


def _changed(before: dict[str, str], after: dict[str, str]) -> set[str]:
    return {rel for rel in after if after[rel] != before.get(rel)}


def test_version_step_skips_ignored_and_nested(tmp_path, capsys):
    from okf_lint import _OPEN, _domain, _tree_bundle

    v = _domain(tmp_path, {"requests/req-1": _OPEN,
                           "incidents/inc-1": "kind: Incident\nstate: open\nparent: ../..\n",
                           "releases/rel-1": "kind: Release\nstate: open\nparent: ../..\n",
                           "releases/rel-1/requests/req-9": _OPEN})
    (v / ".okfignore").write_text("base/scratch/\nbase/wip.md\n", encoding="utf-8")
    (v / "base" / "scratch").mkdir()
    (v / "base" / "scratch" / "draft.md").write_text(_concept("Term", "Draft"), encoding="utf-8")
    (v / "base" / "wip.md").write_text(_concept("Term", "WIP"), encoding="utf-8")
    _tree_bundle(v / "base" / "other-bundle")
    before = _tree(v)
    out = tmp_path / "out"
    capsys.readouterr()
    assert main([str(v), "--to", "0.1", "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert _lines(printed, "migrated ") == ["migrated project.md", "migrated base/profile.md"]
    assert f"2 concepts migrated to OKF v0.1 → {out}" in printed.splitlines()
    assert _changed(before, _tree(out)) == {"index.md", "log.md", "project.md", "base/profile.md"}
    assert _tree(v) == before


def _bundle_01(k: Path, plants: bool) -> Path:
    k.mkdir(parents=True)
    (k / "index.md").write_text('---\nokf_version: "0.1"\n---\n\n# Tables\n\n* [Orders](orders.md) - x\n',
                                encoding="utf-8")
    (k / "orders.md").write_text(_V01, encoding="utf-8")
    if plants:
        (k / ".okfignore").write_text("scratch/\n", encoding="utf-8")
        (k / "scratch").mkdir()
        (k / "scratch" / "s.md").write_text(_V01, encoding="utf-8")
        (k / "nested").mkdir()
        (k / "nested" / "index.md").write_text('---\nokf_version: "0.1"\n---\n\n# Tables\n\n* [N](n.md) - n\n',
                                               encoding="utf-8")
        (k / "nested" / "n.md").write_text(_V01, encoding="utf-8")
    return k


def test_version_step_01_to_02_skips_ignored_and_nested(tmp_path, capsys):
    runs = {}
    for plants in (False, True):
        src = _bundle_01(tmp_path / f"src-{plants}", plants)
        out = tmp_path / f"out-{plants}"
        capsys.readouterr()
        assert main([str(src), "--to", "0.2", "--out", str(out)]) == 0
        runs[plants] = (_lines(capsys.readouterr().out, "migrated "), _tree(src), _tree(out))
    assert runs[True][0] == runs[False][0] == ["migrated orders.md"]
    src_tree, out_tree = runs[True][1], runs[True][2]
    assert ({r: t for r, t in out_tree.items() if r.split("/")[0] in ("scratch", "nested")}
            == {r: t for r, t in src_tree.items() if r.split("/")[0] in ("scratch", "nested")})


_PLANTED = ("nested", "requests", "scratch", "notes.md", ".okfignore")


def _plant_20(k: Path) -> Path:
    """_bundle_20 plus what the profile step must leave at the root: ignored paths, a nested bundle, a kind's
    directory of instances."""
    (k / ".okfignore").write_text("scratch/\nnotes.md\n", encoding="utf-8")
    (k / "scratch").mkdir()
    (k / "scratch" / "s.md").write_text(_concept("Term", "S", body="[x](/decisions/ADR-0001-x.md)\n"), encoding="utf-8")
    (k / "notes.md").write_text(_concept("Term", "Notes", body="[x](decisions/ADR-0001-x.md)\n"), encoding="utf-8")
    for rel, keys in (("nested", ""), ("requests/req-1", "kind: Request\nstate: open\nparent: ../..\n")):
        b = k / rel
        (b / "decisions").mkdir(parents=True)
        (b / "index.md").write_text(f'---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\n{keys}---\n\n'
                                    "# Subdirectories\n\n* [decisions](decisions/index.md) - D.\n", encoding="utf-8")
        (b / "log.md").write_text("# Bundle history\n\n## 2026-11-11\n* **Initialization**: test.\n", encoding="utf-8")
        (b / "decisions" / "index.md").write_text("# decisions\n\n* [Y](ADR-0001-y.md) - Y.\n", encoding="utf-8")
        up = "../" * (rel.count("/") + 2)
        (b / "decisions" / "ADR-0001-y.md").write_text(_concept(
            "Architecture Decision", "Y",
            body=f"[own](/decisions/ADR-0001-y.md) and [up]({up}decisions/ADR-0001-x.md).\n"), encoding="utf-8")
    (k / "requests" / "index.md").write_text("# requests\n\n* [req-1](req-1/index.md) - R.\n", encoding="utf-8")
    return k


def _planted(tree: dict[str, str]) -> dict[str, str]:
    return {rel: text for rel, text in tree.items() if rel.split("/")[0] in _PLANTED}


def _profile_lines(k: Path, capsys, *extra: str) -> list[str]:
    capsys.readouterr()
    assert main([str(k), "--profile", "knowledge/3.0", *extra]) == 0
    return _lines(capsys.readouterr().out, "move ", "rewrote ", "(dry) move ", "(dry) rewrote ")


def test_profile_leaves_ignored_and_nested_at_the_root(tmp_path, capsys):
    plain = _profile_lines(_bundle_20(tmp_path / "a"), capsys)
    p = _plant_20(_bundle_20(tmp_path / "b"))
    before = _planted(_tree(p))
    lines = _profile_lines(p, capsys)
    assert [x for x in lines if x.startswith("move ")] == [x for x in plain if x.startswith("move ")]
    assert [x for x in lines if x.startswith("rewrote ")] == [x for x in plain if x.startswith("rewrote ")]
    assert _planted(_tree(p)) == before
    assert "[own](/decisions/ADR-0001-y.md)" in before["nested/decisions/ADR-0001-y.md"]


def test_profile_dry_run_leaves_ignored_and_nested(tmp_path, capsys):
    plain = _profile_lines(_bundle_20(tmp_path / "a"), capsys)
    p = _plant_20(_bundle_20(tmp_path / "b"))
    before = _tree(p)
    assert _profile_lines(p, capsys, "--dry-run") == ["(dry) " + x for x in plain]
    assert _tree(p) == before


_Z = _concept("Architecture Decision", "Z", body="[abs](/decisions/ADR-0001-x.md) and [up](../ADR-0001-x.md).\n")


def _plant_sub(k: Path) -> Path:
    """A nested bundle decisions/sub/ beside the ADR of _bundle_20, linking a path the profile step moves."""
    sub = k / "decisions" / "sub"
    sub.mkdir()
    (sub / "index.md").write_text('---\nokf_version: "0.2"\n---\n\n# Decisions\n\n* [Z](z.md) - Z.\n',
                                  encoding="utf-8")
    (sub / "z.md").write_text(_Z, encoding="utf-8")
    return k


def test_profile_moves_a_directory_that_also_holds_documents(tmp_path, capsys):
    plain = _profile_lines(_bundle_20(tmp_path / "a"), capsys)
    k = _plant_sub(_bundle_20(tmp_path / "b"))
    lines = _profile_lines(k, capsys)
    assert "move decisions/ → base/decisions/" in lines
    assert lines == plain
    assert (k / "base" / "decisions" / "sub" / "z.md").read_text(encoding="utf-8") == _Z


_SUB = '---\nokf_version: "0.2"\n---\n\n# Notes\n\nKept by hand.\n'


def _plant_holders(k: Path) -> Path:
    """_bundle_20 plus two root directories that hold no instance: policies/ with only an ignored drafts/, and
    external/ with only a nested bundle that declares no kind."""
    (k / ".okfignore").write_text("policies/drafts/\n", encoding="utf-8")
    (k / "policies" / "drafts").mkdir(parents=True)
    (k / "policies" / "index.md").write_text("# policies\n\n_(empty)_\n", encoding="utf-8")
    (k / "policies" / "drafts" / "p.md").write_text(_concept("Policy", "Draft"), encoding="utf-8")
    (k / "external" / "sub").mkdir(parents=True)
    (k / "external" / "index.md").write_text("# external\n\n_(empty)_\n", encoding="utf-8")
    (k / "external" / "sub" / "index.md").write_text(_SUB, encoding="utf-8")
    return k


def _lint_pairs(k: Path) -> list[tuple[str, str]]:
    from okf_lint import lint

    rep, _, _ = lint(k)
    return sorted((i["code"], i["path"]) for i in rep.items)


def test_profile_moves_a_directory_that_holds_no_instance(tmp_path):
    plain = _bundle_20(tmp_path / "a")
    assert main([str(plain), "--profile", "knowledge/3.0"]) == 0
    k = _plant_holders(_bundle_20(tmp_path / "b"))
    before = _tree(k)
    assert main([str(k), "--profile", "knowledge/3.0"]) == 0
    assert sorted(p.name for p in k.iterdir() if p.is_dir()) == [".obsidian", "base", "fragments"]
    assert (k / ".okfignore").read_text(encoding="utf-8") == "base/policies/drafts/\n"
    assert _lint_pairs(k) == _lint_pairs(plain) == [("FRAGMENT_NO_LEDGER", "fragments/2026-10-31-m.md")]
    after = _tree(k)
    assert after["base/policies/drafts/p.md"] == before["policies/drafts/p.md"]
    assert ({r: t for r, t in after.items() if r.startswith("base/external/sub/")}
            == {"base/" + r: t for r, t in before.items() if r.startswith("external/sub/")})
    assert "base/external/sub/" in scan_bundle(k).nested


def test_profile_leaves_a_directory_of_instances_beside_a_bundle_without_kind(tmp_path, capsys):
    plain = _profile_lines(_bundle_20(tmp_path / "a"), capsys)
    k = _plant_20(_bundle_20(tmp_path / "b"))
    (k / "requests" / "other").mkdir()
    (k / "requests" / "other" / "index.md").write_text(_SUB, encoding="utf-8")
    before = _planted(_tree(k))
    lines = _profile_lines(k, capsys)
    assert [x for x in lines if x.startswith("move ")] == [x for x in plain if x.startswith("move ")]
    assert _planted(_tree(k)) == before and (k / "requests" / "other" / "index.md").is_file()


def test_version_step_leaves_a_nested_bundle_inside_a_layer_directory(tmp_path, capsys):
    runs = {}
    for plants in (False, True):
        src = _bundle_20(tmp_path / f"src-{plants}")
        if plants:
            _plant_sub(src)
        out = tmp_path / f"out-{plants}"
        capsys.readouterr()
        assert main([str(src), "--to", "0.1", "--out", str(out)]) == 0
        runs[plants] = (_lines(capsys.readouterr().out, "migrated "), _tree(out))
    assert runs[True][0] == runs[False][0]
    assert {r: t for r, t in runs[True][1].items() if r.startswith("decisions/sub/")} == {
        "decisions/sub/index.md": '---\nokf_version: "0.2"\n---\n\n# Decisions\n\n* [Z](z.md) - Z.\n',
        "decisions/sub/z.md": _Z}


def test_profile_moves_a_non_okf_directory_and_rewrites_its_links(tmp_path, capsys):
    k = _bundle_20(tmp_path)
    (k / "plain").mkdir()
    (k / "plain" / "a.md").write_text("See [x](/decisions/ADR-0001-x.md).\n", encoding="utf-8")
    lines = _profile_lines(k, capsys)
    assert "move plain/ → base/plain/" in lines and "rewrote links in base/plain/a.md" in lines
    assert (k / "base" / "plain" / "a.md").read_text(encoding="utf-8") == "See [x](/base/decisions/ADR-0001-x.md).\n"



_D = "---\ntype: Term\ntitle: D\ndescription: d\n---\n\nSee [a](/decisions/ADR-0001-adopt-kafka.md).\n"


def test_profile_moves_an_ignored_path_inside_a_moved_directory_with_its_okfignore_entry(tmp_path, capsys):
    import pytest

    fixture = Path(__file__).resolve().parents[5] / "examples" / "fixtures" / "knowledge-2.0"
    if not fixture.is_dir():
        pytest.skip("examples/fixtures/knowledge-2.0 not present (script copied outside the repo)")
    k = tmp_path / "knowledge"
    shutil.copytree(fixture, k)
    (k / ".okfignore").write_text("# drafts\ndecisions/drafts/\n*.tmp\nscratch/\n", encoding="utf-8")
    (k / "decisions" / "drafts").mkdir()
    (k / "decisions" / "drafts" / "d.md").write_text(_D, encoding="utf-8")
    lines = _profile_lines(k, capsys)
    assert (k / ".okfignore").read_text(encoding="utf-8") == "# drafts\nbase/decisions/drafts/\n*.tmp\nscratch/\n"
    assert (k / "base" / "decisions" / "drafts" / "d.md").read_text(encoding="utf-8") == _D
    assert not (k / "decisions").exists()
    assert scan_bundle(k).ignored == ["base/decisions/drafts/"]
    assert "rewrote .okfignore" in lines


def test_rewrite_okfignore_follows_only_anchored_entries_under_a_moved_directory():
    text = ("# c\n\ndecisions/drafts/\n/decisions\n!decisions/drafts/keep.md\n\\#odd/x\n"
            "drafts/\nother/\n*.tmp\n**/wip/\nfragments/old/\nnotes.md\nother/x/\n")
    assert rewrite_okfignore(text, ["decisions", "other"]) == (
        "# c\n\nbase/decisions/drafts/\n/base/decisions\n!base/decisions/drafts/keep.md\n\\#odd/x\n"
        "drafts/\nother/\n*.tmp\n**/wip/\nfragments/old/\nnotes.md\nbase/other/x/\n")
    assert rewrite_okfignore(text, []) == text


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
