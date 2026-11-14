#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_migrate.py — Migrate an OKF bundle between v0.1 and v0.2 (both directions),
from the knowledge/2.0 profile to knowledge/3.0, and move each decision of a knowledge/3.0
bundle to the directory its type declares.

Usage:
    uv run okf_migrate.py [bundle] --to 0.2 [--actor process:okf-migrate] [--dry-run] [--out DIR]
    uv run okf_migrate.py [bundle] --to 0.1 [--keep-extensions] [--dry-run] [--out DIR]
    uv run okf_migrate.py [bundle] --profile knowledge/3.0 [--to 0.2] [--dry-run] [--out DIR]
    uv run okf_migrate.py [bundle] --move-decisions [--dry-run]

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
  - the root index.md, base/index.md, every index below base/ and the index.md of each
    root directory kept for its instances (below) are regenerated (# Notes kept);
    okf_profile "knowledge/3.0" in the root index.md; an entry in log.md
  - what lint's scan leaves out is left unedited: at the root, the paths .okfignore matches
    and every nested bundle (an operational instance included) stay where they are; a root
    directory stays at the root only when it holds operational instances (nested bundles
    whose root index.md declares a kind) and no other document besides its index.md (a
    kind's directory of instances); a root directory holding only ignored paths or nested
    bundles without kind moves under base/ with them; inside a directory that moves they
    move with it, and each .okfignore entry anchored under that directory follows them
    (decisions/drafts/ → base/decisions/drafts/); a nested bundle is migrated on its own
    (okf_migrate.py <its directory>)
  - an anchored .okfignore entry whose first segment is a glob matching a moved directory
    (*/drafts/) is kept as written and reported on a NOTICE line: it no longer matches the
    moved paths, so it is fixed by hand
  With --to as well, the profile step runs first and the version step walks its result.

Decisions to the directory of their type (--move-decisions; knowledge/3.0 only, opt-in, a step
of its own: never with --to, --profile, --file or --out; --actor, --keep-extensions and --force
have no effect on it):
  - every concept whose type is a Decision (the type or one that extends it, a local type name
    read through the Domain Profile's aliases) and whose file is not directly in the directory
    in force of its type (the one the type declares, else that of the nearest type it extends
    that declares one) moves there, keeping its file name
  - in every .md of the bundle the links, the sources[].resource and the values of the keys the
    concept's type declares as a path (supersedes, superseded_by, blocks, answered_by, asked_in
    and those of a local type; the key under its declared name or a local one) that point to a
    moved decision are rewritten, and the relative ones of a moved decision are recomputed;
    a link is an inline link as CommonMark defines it (okf_common.inline_links), an image
    included; of a link only its target changes, so a fragment's # Record keeps every other
    character; a reference-style definition ([ref]: target) stays as written
  - the index.md of each directory a decision left or entered, and of the directories above
    them, are regenerated; one **Migration** entry in log.md names both paths of each decision
  - it stops with exit 1, before writing anything, when a new path already exists, when
    .okfignore matches it or it lies in a nested bundle, and when the bundle is closed
    (state: closed: a closed bundle is never edited); exit 2 for a bundle that is not
    knowledge/3.0 (run --profile knowledge/3.0 first)
  - a decision .okfignore matches is no concept of the bundle and stays where it is, and
    .okfignore is never rewritten; a nested bundle is never entered: run the step on it

Every step migrates only what lint reads: the paths .okfignore matches and nested bundles are
left byte-identical (a plain directory of Markdown without OKF frontmatter is read as today).

--out DIR writes a migrated copy and leaves the source bundle untouched (recommended for 0.2→0.1).
It edits the frontmatter text by key blocks to keep order, comments and unknown keys;
it never re-serializes the whole YAML.
"""
from __future__ import annotations

import argparse
import fnmatch
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
    OkfIgnore,
    SUPPORTED_VERSIONS,
    declared_profile,
    detect_version,
    find_bundle,
    inline_links,
    load_doc,
    parse_yaml,
    root_frontmatter,
    scan_bundle,
    split_frontmatter,
    walk_bundle,
)
from okf_index import index_targets, regenerate  # noqa: E402
from okf_lint import Report, find_tree  # noqa: E402
from okf_profile import (  # noqa: E402
    DECISION,
    DOMAIN_BUNDLE,
    Resolved,
    canonical_type,
    directory_in_force,
    is_a,
    load_profile,
    type_in_force,
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
SOURCE_KEYS = {"sources"}
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


def _root_dirs(bundle: Path) -> list[str]:
    return [p.name for p in sorted(bundle.iterdir())
            if p.is_dir() and not p.name.startswith(".") and p.name not in LAYER_DIRS]


def instance_dirs(bundle: Path) -> list[str]:
    """The root directories kept at the root for their instances: each holds at least one operational instance and no
    document migrate reads besides its own index.md (the directory of a kind's instances, ADR-0039 decision 3). A root
    directory left out as a whole (.okfignore, a nested bundle) stays too, but is not one of them."""
    sc = scan_bundle(bundle)
    out = [*sc.ignored, *sc.nested]
    read = {d.rel for d in bundle_docs(bundle, out)}
    instances = [n for n in sc.nested if is_instance(bundle / n)]

    def holds(pre: str) -> bool:
        return (not _under(pre, out) and any(i.startswith(pre) and i != pre for i in instances)
                and not any(r.startswith(pre) and r != pre + "index.md" for r in read))

    return [n for n in _root_dirs(bundle) if holds(n + "/")]


def profile_moves(bundle: Path) -> tuple[list[str], list[str]]:
    """(root directories, root concepts) that move under base/. A left_out path stays at the root, and so does each
    directory of instance_dirs. A directory that holds only ignored paths or nested bundles without kind moves,
    carrying them."""
    sc = scan_bundle(bundle)
    out = [*sc.ignored, *sc.nested]
    kept = instance_dirs(bundle)
    dirs = [n for n in _root_dirs(bundle) if not _under(n + "/", out) and n not in kept]
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


def glob_first_entries(text: str, dirs: list[str]) -> list[str]:
    """The .okfignore entries, as written and in file order, that rewrite_okfignore keeps although they name a path
    under a moved directory: past its '!' or '\\' prefix and a leading '/', the entry holds a '/' before its trailing
    one, and its first segment is a glob other than '**' that matches the name of a moved directory."""
    found = []
    for line in text.split("\n"):
        body = line.rstrip()
        if not body or body.startswith("#"):
            continue
        pat = body[1:] if body[0] in "!\\" else body
        first, sep, _ = pat.removeprefix("/").rstrip("/").partition("/")
        if (sep and first != "**" and any(c in first for c in "*?[")
                and any(fnmatch.fnmatchcase(d, first) for d in dirs)):
            found.append(body)
    return found


def migrate_profile(bundle: Path, target: str, dry_run: bool) -> int:
    dirs, files = profile_moves(bundle)
    kept = instance_dirs(bundle)
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
    for e in glob_first_entries(ignore_text, dirs):
        print(f"NOTICE {OKFIGNORE} entry '{e}' starts with a glob: kept as written, it no longer matches the "
              f"directories moved under {BASE_DIR}/; fix it by hand")
    if not dry_run:
        if new_ignore != ignore_text:
            ignore.write_text(new_ignore, encoding="utf-8")
        (bundle / BASE_DIR).mkdir(exist_ok=True)
        for n in dirs + files:
            shutil.move(str(bundle / n), str(bundle / BASE_DIR / n))
        for rel, text in rewritten.items():
            (bundle / move.new(rel)).write_text(text, encoding="utf-8")
        set_root_key(bundle / "index.md", "okf_profile", target)
        regenerate(bundle, [bundle, *index_targets(bundle, bundle / BASE_DIR), *(bundle / d for d in kept)])
        append_log(bundle / "log.md", "", 0, entry=(
            f"* **Migration**: Bundle migrated to profile {target} ({len(dirs)} directories and {len(files)} "
            f"root concepts moved under base/; links rewritten in {len(rewritten)} files) with okf-migrate."))
    print(f"\nProfile {target}: {len(dirs)} directories and {len(files)} root concepts moved under base/, "
          f"links rewritten in {len(rewritten)} files{' (dry-run)' if dry_run else ''} → {bundle}")
    return 0


# --------------------------------------------------------------------------
# Decisions to the directory their type declares (--move-decisions)
# --------------------------------------------------------------------------
class FileMove:
    """Files that move, as a map of bundle-relative posix paths old → new: any file to any path, renames included.
    rewrite_moved rewrites the paths of one .md with it. exists(rel) says a bundle-relative path is in the bundle
    before the move; with it, a relative target that names nothing there is left as written (a
    repository-relative resource in a file that moves is not a path relative to that file)."""

    def __init__(self, files: dict[str, str], exists=None):
        self.files, self.exists = dict(files), exists

    def new(self, rel: str) -> str:
        return self.files.get(rel, rel)

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
            return f"/{self.files[rel]}{slash}{sep}{anchor}" if rel in self.files else None
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(doc_rel), path))
        if rel not in self.files and (doc_rel not in self.files or (self.exists is not None and not self.exists(rel))):
            return None
        new = posixpath.relpath(self.new(rel), posixpath.dirname(self.new(doc_rel)) or ".")
        return None if new == posixpath.normpath(path) else new + slash + sep + anchor


_QUOTED_KEY_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\'')
_KEY_COLON_RE = re.compile(r"[ \t]*:(?=\s|$)")


def frontmatter_key(line: str) -> tuple[str, int] | None:
    """(the key, the index after its colon) of a frontmatter line that opens a top-level key, or None: the key
    written plain, whatever its first letter (`ámbito:`), or in quotes (`"superseded_by":`)."""
    if not line or line[0] in " \t#-":
        return None
    if line[0] in "\"'":
        quoted = _QUOTED_KEY_RE.match(line)
        colon = _KEY_COLON_RE.match(line, quoted.end()) if quoted else None
        try:
            keys = list(parse_yaml(quoted.group(0) + ": 0")) if colon else []
        except Exception:  # noqa: BLE001
            keys = []
        return (str(keys[0]), colon.end()) if len(keys) == 1 else None
    plain = re.match(r"(.*?)[ \t]*:(?=\s|$)", line)
    return (plain.group(1), plain.end()) if plain and plain.group(1) else None


_RESOURCE_KEY_RE = re.compile(r"""(?:(?<![\w"'.-])resource[ \t]*:(?=[ \t\r]|$)|"resource"[ \t]*:|'resource'[ \t]*:)[ \t]*""")
_RESOURCE_VALUE_RE = re.compile(r"([\"']?)([^\s\"',}\]]+)")
_RESOURCE_NEXT_LINE_RE = re.compile(r"(?:[>|][+\-1-9]{0,2}[ \t]*)?(?:#.*)?\r?$")
_RESOURCE_ALONE_RE = re.compile(r"[\"']?[ \t]*(?:#.*)?\r?$")


def rewrite_resource(line: str, pending: bool, new_target) -> tuple[str, bool]:
    """(the line, whether its last `resource` leaves its path to the next line) for one line of a sources block:
    each `resource` subkey, written plain or in quotes, has its path rewritten with new_target, the path plain or in
    quotes on the line of the key. With pending, the line is read first as the path alone that a `resource:` left
    open or a block scalar (`resource: >-`) announced on the line before."""
    def put(text: str, value: re.Match) -> str:
        new = new_target(value.group(2))
        return text if new is None else text[:value.start(2)] + new + text[value.end(2):]

    if pending:
        if not line.strip():
            return line, True
        indent = re.match(r"[ \t]+(?=\S)", line)
        value = _RESOURCE_VALUE_RE.match(line, indent.end()) if indent else None
        if value and _RESOURCE_ALONE_RE.match(line, value.end()):
            return put(line, value), False
    keys = list(_RESOURCE_KEY_RE.finditer(line))
    opens = bool(keys) and _RESOURCE_NEXT_LINE_RE.match(line, keys[-1].end()) is not None
    for key in reversed(keys[:-1] if opens else keys):
        value = _RESOURCE_VALUE_RE.match(line, key.end())
        if value:
            line = put(line, value)
    return line, opens


def rewrite_moved(text: str, doc_rel: str, move: "FileMove", path_keys=PATH_KEYS, source_keys=SOURCE_KEYS) -> str:
    """Rewrite, in one .md, every path that names a file of a FileMove: the target of each inline link of the body
    as CommonMark defines it (okf_common.inline_links: an image and a linked image included, the target plain or in
    angle brackets, whatever the link text and the title), the sources[].resource (rewrite_resource: the subkey
    plain or in quotes, its path on the same line or alone on the next) and the values of the path keys,
    a key read under any name it is written with (frontmatter_key). Every other byte is kept, the line endings of
    a text read without newline translation included; a reference-style definition (`[ref]: target`) is not an
    inline link and stays as written."""
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
            block, pending = None, False
            for i in range(1, end):
                key = frontmatter_key(lines[i])
                if key:
                    block, pending = key[0], False
                if block in source_keys:
                    lines[i], pending = rewrite_resource(lines[i], pending, lambda t: move.target(t, doc_rel))
                elif block in path_keys:
                    start = key[1] if key else 0
                    value, hash_, comment = lines[i][start:].partition(" #")
                    lines[i] = lines[i][:start] + PATH_VALUE_RE.sub(lambda m: sub(m, 2), value) + hash_ + comment
            body_start = end + 1
    body = "\n".join(lines[body_start:])
    for link in reversed(inline_links(body)):
        new = move.target(body[link.start:link.end], doc_rel)
        if new is not None:
            body = body[:link.start] + new + body[link.end:]
    return "\n".join([*lines[:body_start], body])


def profile_in_force(bundle: Path) -> Resolved:
    """The Domain Profile in force in a knowledge/3.0 bundle; for an operational instance, composed on the profile of
    the domain bundle its parent chain reaches, as lint and okf_index.py read it."""
    tree = find_tree(bundle, Report())
    return load_profile(bundle, domain=tree.domain if tree is not None else None)


def keys_with_paths(r: Resolved, fm: dict | None) -> tuple[set[str], set[str]]:
    """(the keys whose values are paths, the keys that hold sources) of a concept: PATH_KEYS and every field its type
    declares as a path or a list of paths, each under its declared name and under the local names aliases give it."""
    t = canonical_type(r, (fm or {}).get("type"))
    fields = type_in_force(r, t)["fields"] if isinstance(t, str) and t in r.types else {}
    paths = set(PATH_KEYS) | {k for k, d in fields.items()
                              if d.get("type") == "path" or (d.get("type") == "list" and d.get("of") == "path")}

    def named(keys: set[str]) -> set[str]:
        return keys | {name for name, a in r.aliases["fields"].items() if a["to"] in keys}

    return named(paths), named(set(SOURCE_KEYS))


def decision_moves(bundle: Path, r: Resolved) -> dict[str, str]:
    """old → new for every decision of the bundle that is not directly in the directory in force of its type: a
    concept lint reads (never a path .okfignore matches nor one inside a nested bundle) whose type, read through the
    aliases, is a Decision. The file keeps its name."""
    moves = {}
    for doc in bundle_docs(bundle):
        if doc.is_reserved or not isinstance(doc.frontmatter, dict):
            continue
        t = canonical_type(r, doc.frontmatter.get("type"))
        if not isinstance(t, str) or not is_a(r, t, DECISION):
            continue
        home = (directory_in_force(r, t) or "").strip("/")
        if home and posixpath.dirname(doc.rel) != home:
            moves[doc.rel] = f"{home}/{posixpath.basename(doc.rel)}"
    return moves


def _left_out_destination(ign: OkfIgnore, nested: list[str], rel: str) -> str | None:
    """Why a decision cannot move to rel: .okfignore matches it or a directory above it, or it lies in a nested bundle."""
    parts = rel.split("/")
    if ign.match(rel, False) or any(ign.match("/".join(parts[:i]), True) for i in range(1, len(parts))):
        return f"{OKFIGNORE} matches it"
    return "it lies in a nested bundle" if _under(rel, nested) else None


def _dirs_up(rels) -> list[str]:
    """The directory of each path and every directory above it, the bundle root ('') included."""
    dirs = set()
    for rel in rels:
        d = posixpath.dirname(rel)
        while d not in dirs:
            dirs.add(d)
            d = posixpath.dirname(d)
    return sorted(dirs)


def _n(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


def move_decisions(bundle: Path, dry_run: bool) -> int:
    if str(root_frontmatter(bundle).get("state")) == "closed":
        print(f"ERROR: {bundle} is closed (state: closed): a closed bundle is never edited.", file=sys.stderr)
        return 1
    current = declared_profile(bundle)
    if current != PROFILE_30:
        print(f"ERROR: {bundle} declares profile {current or 'none (knowledge/2.0)'}: --move-decisions needs a "
              f"{PROFILE_30} bundle; run okf_migrate.py --profile {PROFILE_30} first.", file=sys.stderr)
        return 2
    r = profile_in_force(bundle)
    sc = scan_bundle(bundle)
    if sc.nested:
        print(f"NOTICE nested bundles not entered: {', '.join(sc.nested)} (run okf_migrate.py --move-decisions on each)")
    moves = decision_moves(bundle, r)
    if not moves:
        print(f"nothing to move: every decision of {bundle} is in the directory its type declares")
        return 0
    ign = OkfIgnore.load(bundle)
    stops, taken = [], {}
    for old, new in moves.items():
        why = _left_out_destination(ign, sc.nested, new)
        if (bundle / new).exists():
            stops.append(f"{old} cannot move to {new}: {new} already exists")
        elif new in taken:
            stops.append(f"{old} cannot move to {new}: {taken[new]} moves there too")
        elif why:
            stops.append(f"{old} cannot move to {new}: {why}")
        taken.setdefault(new, old)
    if stops:
        for stop in stops:
            print(f"ERROR: {stop}", file=sys.stderr)
        print("Nothing was written; settle each by hand and run the step again.", file=sys.stderr)
        return 1
    move = FileMove(moves, exists=lambda rel: (bundle / rel).exists())
    rewritten = {}
    for doc in bundle_docs(bundle):
        text = doc.path.read_bytes().decode("utf-8")
        new = rewrite_moved(text, doc.rel, move, *keys_with_paths(r, doc.frontmatter))
        if new != text:
            rewritten[doc.rel] = new
    for old, new in moves.items():
        print(f"MOVE {old} -> {new}")
    for rel in rewritten:
        print(f"LINKS {move.new(rel)}")
    if not dry_run:
        for old, new in moves.items():
            (bundle / new).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(bundle / old), str(bundle / new))
        for rel, text in rewritten.items():
            (bundle / move.new(rel)).write_bytes(text.encode("utf-8"))
        regenerate(bundle, [bundle / d for d in _dirs_up([*moves, *moves.values()])])
        for d in sorted({posixpath.dirname(old) for old in moves}):
            if not any(q.is_file() and q.name != "index.md" for q in (bundle / d).rglob("*")):
                print(f"NOTICE {d}/ holds nothing but its index.md now; remove the directory by hand if it is not "
                      "wanted")
        pairs = "; ".join(f"`{old}` → `{new}`" for old, new in moves.items())
        append_log(bundle / "log.md", "", 0, entry=(
            f"* **Migration**: {_n(len(moves), 'decision')} moved, each to the directory of its type, links rewritten in "
            f"{_n(len(rewritten), 'file')}, with okf-migrate --move-decisions: {pairs}."))
    print(f"\n{_n(len(moves), 'decision')} moved, each to the directory of its type, links rewritten in "
          f"{_n(len(rewritten), 'file')}{' (dry-run)' if dry_run else ''} → {bundle}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="path to the bundle (default: search upwards for knowledge/)")
    ap.add_argument("--to", choices=SUPPORTED_VERSIONS, help="target OKF version")
    ap.add_argument("--profile", choices=(PROFILE_30,), help="target knowledge profile (moves the typed directories under base/)")
    ap.add_argument("--actor", default="process:okf-migrate", help="generated.by for concepts without an author (0.1→0.2)")
    ap.add_argument("--keep-extensions", action="store_true", help="0.2→0.1: keep v0.2 keys as extensions")
    ap.add_argument("--out", help="write a migrated copy to this directory (the source is left untouched)")
    ap.add_argument("--move-decisions", action="store_true",
                    help="move each decision to the directory its type declares and rewrite the links to it (a step "
                         "of its own, knowledge/3.0 only)")
    ap.add_argument("--dry-run", action="store_true", help="report the changes without writing them")
    ap.add_argument("--force", action="store_true", help="migrate even if the bundle already is at the target")
    ap.add_argument("--file", action="append", default=[],
                    help="migrate only this concept (path relative to the bundle); repeatable. Leaves index/log alone")
    args = ap.parse_args(argv)
    if args.move_decisions and (args.to or args.profile or args.file or args.out):
        ap.error("--move-decisions is a step of its own; it cannot be combined with --to, --profile, --file or --out")
    if args.file and args.profile:
        ap.error("--profile migrates the whole bundle; it cannot be combined with --file")
    if args.file and not args.to:
        ap.error("--file needs --to")
    if not args.to and not args.profile and not args.move_decisions:
        ap.error("at least one of --to or --profile is required, or --move-decisions on its own")

    src = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if src is None or not src.is_dir():
        print("ERROR: bundle not found (knowledge/index.md). Pass its path.", file=sys.stderr)
        return 2
    if args.move_decisions:
        return move_decisions(src, args.dry_run)
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


def _bytes(k: Path) -> dict[str, bytes]:
    return {p.relative_to(k).as_posix(): p.read_bytes() for p in sorted(k.rglob("*")) if p.is_file()}


def _without_requests_index(tree: dict[str, str]) -> dict[str, str]:
    return {rel: text for rel, text in tree.items() if rel != "requests/index.md"}


def _freshly_regenerated(k: Path, tmp: Path, rel: str) -> str:
    """rel/index.md as regenerate writes it on a copy of k, now."""
    fresh = tmp / ("fresh-" + rel.replace("/", "-"))
    shutil.copytree(k, fresh)
    regenerate(fresh, [fresh / rel])
    return (fresh / rel / "index.md").read_text(encoding="utf-8")


def _profile_run(k: Path, capsys) -> tuple[list[str], str]:
    """The profile step's non-blank stdout lines, with k written <k>, and its stderr."""
    capsys.readouterr()
    assert main([str(k), "--profile", "knowledge/3.0"]) == 0
    got = capsys.readouterr()
    return [x for x in got.out.replace(str(k), "<k>").splitlines() if x.strip()], got.err


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
    assert _without_requests_index(_planted(_tree(p))) == _without_requests_index(before)
    assert (p / "requests" / "index.md").read_text(encoding="utf-8") == _freshly_regenerated(p, tmp_path, "requests")
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


def _plant_other(k: Path) -> Path:
    """_plant_20 plus requests/other/, a nested bundle without kind beside the instance requests/req-1/."""
    _plant_20(k)
    (k / "requests" / "other").mkdir()
    (k / "requests" / "other" / "index.md").write_text(_SUB, encoding="utf-8")
    return k


def test_profile_leaves_a_directory_of_instances_beside_a_bundle_without_kind(tmp_path, capsys):
    plain, plain_err = _profile_run(_bundle_20(tmp_path / "a"), capsys)
    k = _plant_other(_bundle_20(tmp_path / "b"))
    before = _planted(_tree(k))
    lines, err = _profile_run(k, capsys)
    assert [x for x in lines if x.startswith("move ")] == [x for x in plain if x.startswith("move ")]
    assert lines.count("WROTE requests/index.md") == 1
    assert [x for x in lines if x != "WROTE requests/index.md"] == plain
    assert (plain_err, err) == ("", "")
    assert _without_requests_index(_planted(_tree(k))) == _without_requests_index(before)
    assert (k / "requests" / "index.md").read_text(encoding="utf-8") == _freshly_regenerated(k, tmp_path, "requests")
    assert (k / "requests" / "other" / "index.md").is_file()


def test_profile_regenerates_a_directory_it_keeps_for_its_instances_in_a_bundle_with_no_kind(tmp_path, capsys):
    from okf_index import main as index_main

    k = _plant_other(_bundle_20(tmp_path / "b"))
    left = ("requests/req-1/", "requests/other/", "nested/", "scratch/")
    before = {r: t for r, t in _bytes(k).items() if r.startswith(left)}
    _profile_lines(k, capsys)
    got = (k / "requests" / "index.md").read_text(encoding="utf-8")
    assert got == _freshly_regenerated(k, tmp_path, "requests")
    assert got == ("> Concepts in requests.\n\n# Subdirectories\n\n* [other](other/index.md) - Concepts in other.\n"
                   "* [req-1](req-1/index.md) - Concepts in req-1.\n")
    assert {r: t for r, t in _bytes(k).items() if r.startswith(left)} == before
    capsys.readouterr()
    assert index_main([str(k), "--dir", "requests", "--check"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "0 index.md out of date"


def test_profile_moves_a_directory_that_holds_an_instance_beside_a_document(tmp_path, capsys):
    plain = _profile_lines(_bundle_20(tmp_path / "a"), capsys)
    k = _bundle_20(tmp_path / "b")
    inst = k / "decisions" / "req-9"
    inst.mkdir()
    (inst / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\nkind: Request\n'
                                   "state: open\nparent: ../..\n---\n\n# Notes\n\nKept by hand.\n", encoding="utf-8")
    before = {r: t for r, t in _tree(k).items() if r.startswith("decisions/req-9/")}
    lines = _profile_lines(k, capsys)
    assert "move decisions/ → base/decisions/" in lines
    assert [x for x in lines if x.startswith("move ")] == [x for x in plain if x.startswith("move ")]
    assert not (k / "decisions").exists()
    assert {r: t for r, t in _tree(k).items() if r.startswith("base/decisions/req-9/")} == {
        "base/" + r: t for r, t in before.items()}


_REQ_PROFILE = ("---\ntype: Domain Profile\ntitle: DP\ndescription: DP.\n" + _GEN
                + "kinds:\n  Request: { extends: Operational Bundle, description: A request, directory: requests/ }\n"
                "---\n\n# What this bundle holds\n\nText.\n")


def test_profile_regenerates_the_index_of_a_kind_directory_it_keeps(tmp_path, capsys):
    from okf_index import main as index_main

    k = _bundle_20(tmp_path / "b")
    (k / "profile.md").write_text(_REQ_PROFILE, encoding="utf-8")
    inst = k / "requests" / "r1"
    (inst / "decisions").mkdir(parents=True)
    (inst / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\nkind: Request\n'
                                   "state: open\nparent: ../..\n---\n\n# Notes\n\nKept by hand.\n", encoding="utf-8")
    (inst / "decisions" / "index.md").write_text("# decisions\n\n_(empty)_\n", encoding="utf-8")
    (k / "requests" / "index.md").write_text("# requests\n\n* [r1](r1/index.md) - by hand.\n", encoding="utf-8")
    before = {r: t for r, t in _tree(k).items() if r.startswith("requests/r1/")}
    lines = _profile_lines(k, capsys)
    assert "move profile.md → base/profile.md" in lines and (k / "requests").is_dir()
    assert {r: t for r, t in _tree(k).items() if r.startswith("requests/r1/")} == before
    fresh = tmp_path / "fresh"
    shutil.copytree(k, fresh)
    regenerate(fresh, [fresh / "requests"])
    got = (k / "requests" / "index.md").read_text(encoding="utf-8")
    assert got == (fresh / "requests" / "index.md").read_text(encoding="utf-8")
    assert "A request" in got and "* [r1](r1/index.md) _(state: open)_" in got
    capsys.readouterr()
    assert index_main([str(k), "--dir", "requests", "--check"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "0 index.md out of date"


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
    k = _bundle_20(tmp_path)
    (k / ".okfignore").write_text("# drafts\ndecisions/drafts/\n*.tmp\nscratch/\n", encoding="utf-8")
    (k / "decisions" / "drafts").mkdir()
    (k / "decisions" / "drafts" / "d.md").write_text(_D, encoding="utf-8")
    lines = _profile_lines(k, capsys)
    assert (k / ".okfignore").read_text(encoding="utf-8") == "# drafts\nbase/decisions/drafts/\n*.tmp\nscratch/\n"
    assert (k / "base" / "decisions" / "drafts" / "d.md").read_text(encoding="utf-8") == _D
    assert not (k / "decisions").exists()
    assert scan_bundle(k).ignored == ["base/decisions/drafts/"]
    assert "rewrote .okfignore" in lines


_GLOBS = "*/drafts/\n**/wip/\n?ecisions/x/\nfr*/old/\n*.tmp\n!*/drafts/keep.md\n"
_GLOB_NOTICES = [f"NOTICE .okfignore entry '{e}' starts with a glob: kept as written, it no longer matches the "
                 "directories moved under base/; fix it by hand"
                 for e in ("*/drafts/", "?ecisions/x/", "!*/drafts/keep.md")]


def _notices(out: str) -> list[str]:
    return [x for x in out.splitlines() if x.startswith("NOTICE .okfignore entry ")]


def test_profile_keeps_and_reports_each_glob_first_okfignore_entry(tmp_path, capsys):
    for extra in ([], ["--dry-run"]):
        k = _bundle_20(tmp_path / (extra[0] if extra else "real"))
        (k / ".okfignore").write_text(_GLOBS, encoding="utf-8")
        before = _bytes(k)
        capsys.readouterr()
        assert main([str(k), "--profile", "knowledge/3.0", *extra]) == 0
        assert _notices(capsys.readouterr().out) == _GLOB_NOTICES, extra
        assert (k / ".okfignore").read_bytes() == _GLOBS.encode(), extra
        if extra:
            assert _bytes(k) == before


def test_profile_reports_a_glob_first_entry_it_cannot_rewrite(tmp_path, capsys):
    k = _bundle_20(tmp_path)
    (k / ".okfignore").write_text("*/drafts/\n**/wip/\n", encoding="utf-8")
    (k / "decisions" / "drafts").mkdir()
    (k / "decisions" / "drafts" / "d.md").write_text(_D, encoding="utf-8")
    capsys.readouterr()
    assert main([str(k), "--profile", "knowledge/3.0"]) == 0
    assert [x for x in capsys.readouterr().out.splitlines() if "NOTICE" in x] == _GLOB_NOTICES[:1]
    assert (k / ".okfignore").read_bytes() == b"*/drafts/\n**/wip/\n"


def test_profile_dry_run_writes_nothing_in_a_bundle_that_declares_a_kind(tmp_path, capsys):
    k = _bundle_20(tmp_path)
    (k / "profile.md").write_text(_REQ_PROFILE, encoding="utf-8")
    inst = k / "requests" / "r1"
    (inst / "decisions").mkdir(parents=True)
    (inst / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\nkind: Request\n'
                                   "state: open\nparent: ../..\n---\n\n# Notes\n\nKept by hand.\n", encoding="utf-8")
    (inst / "decisions" / "index.md").write_text("# decisions\n\n_(empty)_\n", encoding="utf-8")
    (k / "requests" / "index.md").write_text("# requests\n\n* [r1](r1/index.md) - by hand.\n", encoding="utf-8")
    before = _bytes(k)
    lines = _profile_lines(k, capsys, "--dry-run")
    assert "(dry) move profile.md → base/profile.md" in lines
    assert _bytes(k) == before


def test_profile_dry_run_writes_nothing_beside_a_rewritten_okfignore(tmp_path, capsys):
    k = _plant_holders(_bundle_20(tmp_path))
    before = _bytes(k)
    lines = _profile_lines(k, capsys, "--dry-run")
    assert "(dry) rewrote .okfignore" in lines
    assert (k / ".okfignore").read_text(encoding="utf-8") == "policies/drafts/\n"
    assert _bytes(k) == before


def test_rewrite_okfignore_follows_only_anchored_entries_under_a_moved_directory():
    text = ("# c\n\ndecisions/drafts/\n/decisions\n!decisions/drafts/keep.md\n\\#odd/x\n"
            "drafts/\nother/\n*.tmp\n**/wip/\nfragments/old/\nnotes.md\nother/x/\n")
    assert rewrite_okfignore(text, ["decisions", "other"]) == (
        "# c\n\nbase/decisions/drafts/\n/base/decisions\n!base/decisions/drafts/keep.md\n\\#odd/x\n"
        "drafts/\nother/\n*.tmp\n**/wip/\nfragments/old/\nnotes.md\nbase/other/x/\n")
    assert rewrite_okfignore(text, []) == text


# --------------------------------------------------------------------------
# --move-decisions: each decision to the directory its type declares
# --------------------------------------------------------------------------
_OLD, _NEW = "base/decisions", "base/decisions/architecture"
_ROOT_30 = '---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n---\n\n# Index\n'
_FRAGMENT = "occurred_at: 2026-11-01\norigin: Weekly\nparticipants: [human:alice]\ndistillation_status: distilled\n"


def _b1(moved: bool) -> dict[str, str]:
    """B1 without its indexes: two architecture decisions in base/decisions/ and every kind of path to them. With
    moved, the same bundle after the step: the text it must have, each path to a moved decision renamed."""
    d = _NEW if moved else _OLD
    up = "../../" if moved else "../"  # from a decision to base/
    return {
        "log.md": ("# Bundle history\n\n## 2026-11-01\n"
                   f"* **Creation**: [ADR-0001]({d}/ADR-0001-x.md), also [by bundle path](/{d}/ADR-0001-x.md).\n"),
        "project.md": _concept("Project", "P"),
        f"{d}/ADR-0001-x.md": _concept(
            "Architecture Decision", "X",
            "adr_id: ADR-0001\ndecision_status: accepted\n"
            "sources:\n  - { id: f, resource: /fragments/2026-11-01-m.md }\n"
            f"  - id: r\n    resource: \"{up}../fragments/2026-11-01-m.md\"\n  - {{ id: d, resource: docs/bench.md }}\n",
            f"[pay]({up}systems/pay.md), [abs](/base/systems/pay.md), [next](ADR-0002-y.md#context), "
            f"[frag]({up}../fragments/2026-11-01-m.md), [gone](nowhere.md), "
            "[site](https://example.com/base/decisions/ADR-0001-x.md) and [top](#context).\n"),
        f"{d}/ADR-0002-y.md": _concept(
            "Architecture Decision", "Y",
            f"adr_id: ADR-0002\ndecision_status: accepted\nsupersedes: /{d}/ADR-0001-x.md  # the older one\n",
            "Replaces [X](ADR-0001-x.md).\n"),
        "base/systems/pay.md": _concept(
            "System", "Pay", f"sources:\n  - {{ id: a, resource: /{d}/ADR-0001-x.md, title: X }}\n",
            f"See [abs](/{d}/ADR-0001-x.md#context) and "
            f"[rel](../decisions/{'architecture/' if moved else ''}ADR-0001-x.md).\n"),
        "base/questions/why.md": _concept(
            "Open Question", "Why",
            "owner: human:alice\nquestion_status: open\nasked_in: /fragments/2026-11-01-m.md\n"
            f"blocks: [/{d}/ADR-0001-x.md, /base/systems/pay.md]\n"),
        "fragments/2026-11-01-m.md": _concept(
            "Knowledge Fragment", "M",
            _FRAGMENT + f"sources:\n  - {{ id: a, resource: /{d}/ADR-0001-x.md, title: X }}\n",
            "# Record\n\n"
            f"Alice: we follow [ADR-0001](../{d}/ADR-0001-x.md) and "
            f"[base/decisions/ADR-0001-x.md](/{d}/ADR-0001-x.md \"X\"), kept at `/base/decisions/ADR-0001-x.md`.\n"),
    }


def _bundle_30(tmp: Path, files: dict[str, str]) -> Path:
    """A knowledge/3.0 bundle holding `files`, its indexes written by okf_index.py."""
    return _bundle_at(tmp / "knowledge", files)


def _bundle_at(k: Path, files: dict[str, str]) -> Path:
    for rel, text in {"index.md": _ROOT_30, **files}.items():
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
    regenerate(k, index_targets(k))
    return k


def _no_indexes(tree: dict[str, str]) -> dict[str, str]:
    return {rel: text for rel, text in tree.items() if rel.rpartition("/")[2] != "index.md"}


def _findings(k: Path) -> list[tuple]:
    from okf_lint import lint

    rep, _, _ = lint(k)
    return sorted((i["level"], i["code"], i["path"], i["message"]) for i in rep.items)


def _move(k: Path, capsys, *extra: str) -> tuple[int, str, str]:
    capsys.readouterr()
    rc = main([str(k), "--move-decisions", *extra])
    io = capsys.readouterr()
    return rc, io.out, io.err


_B1_MOVES = (f"MOVE {_OLD}/ADR-0001-x.md -> {_NEW}/ADR-0001-x.md\nMOVE {_OLD}/ADR-0002-y.md -> {_NEW}/ADR-0002-y.md\n"
             f"LINKS log.md\nLINKS {_NEW}/ADR-0001-x.md\nLINKS {_NEW}/ADR-0002-y.md\nLINKS {_OLD}/index.md\n"
             "LINKS base/questions/why.md\nLINKS base/systems/pay.md\nLINKS fragments/2026-11-01-m.md\n")
_B1_WROTE = f"WROTE {_OLD}/index.md\nWROTE {_NEW}/index.md\n"
_B1_SUMMARY = "\n2 decisions moved, each to the directory of its type, links rewritten in 7 files{dry} → {k}\n"
_B1_ENTRY = ("* **Migration**: 2 decisions moved, each to the directory of its type, links rewritten in 7 files, with okf-migrate "
             f"--move-decisions: `{_OLD}/ADR-0001-x.md` → `{_NEW}/ADR-0001-x.md`; "
             f"`{_OLD}/ADR-0002-y.md` → `{_NEW}/ADR-0002-y.md`.\n")


def test_move_decisions_moves_each_decision_and_rewrites_every_path_to_it(tmp_path, capsys):
    from okf_index import main as index_main

    k = _bundle_30(tmp_path, _b1(False))
    before = _findings(k)
    rc, out, err = _move(k, capsys)
    assert (rc, out, err) == (0, _B1_MOVES + _B1_WROTE + _B1_SUMMARY.format(dry="", k=k), "")
    after = _b1(True)
    after["log.md"] = after["log.md"].replace(
        "## 2026-11-01\n", f"## {date.today().isoformat()}\n{_B1_ENTRY}\n## 2026-11-01\n")
    assert _no_indexes(_tree(k)) == after
    assert index_main([str(k), "--check"]) == 0
    assert capsys.readouterr().out == "0 index.md out of date\n"
    renamed = sorted((level, code, path.replace(f"{_OLD}/ADR-", f"{_NEW}/ADR-"), msg.replace(f"{_OLD}/ADR-", f"{_NEW}/ADR-"))
                     for level, code, path, msg in before)
    assert before and _findings(k) == renamed


def _outside_link_targets(before: str, after: str) -> list[tuple[str, str]]:
    """The spans a character diff finds changed that do not lie inside the parentheses of a link, on both sides."""
    import difflib

    def inside(text: str, i: int, j: int) -> bool:
        return any(m.start(1) <= i and j <= m.end(1) for m in re.finditer(r"\]\(([^)]*)\)", text))

    ops = difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
    return [(before[i1:i2], after[j1:j2]) for tag, i1, i2, j1, j2 in ops
            if tag != "equal" and not (inside(before, i1, i2) and inside(after, j1, j2))]


def test_move_decisions_changes_a_fragment_record_only_inside_the_target_of_a_link(tmp_path, capsys):
    k = _bundle_30(tmp_path, _b1(False))
    rel = "fragments/2026-11-01-m.md"
    before = _tree(k)[rel].partition("# Record\n")[2]
    assert _move(k, capsys)[0] == 0
    after = _tree(k)[rel].partition("# Record\n")[2]
    assert before and after != before
    assert _outside_link_targets(before, after) == []
    assert _outside_link_targets("[a/x.md](/a/x.md)", "[b/x.md](/b/x.md)") == [("a", "b")]


def test_move_decisions_keeps_the_line_endings_of_each_file_it_rewrites(tmp_path, capsys):
    crlf = ["fragments/2026-11-01-m.md", "base/systems/pay.md", f"{_OLD}/ADR-0001-x.md"]
    mixed = f"{_OLD}/ADR-0002-y.md"
    k = _bundle_30(tmp_path / "crlf", _b1(False))
    for rel in crlf:
        (k / rel).write_bytes(_b1(False)[rel].replace("\n", "\r\n").encode())
    (k / mixed).write_bytes(_b1(False)[mixed].replace("\n", "\r\n", 3).encode())
    assert _findings(k) == _findings(_bundle_30(tmp_path / "lf", _b1(False)))
    assert _move(k, capsys)[0] == 0
    after = _b1(True)
    got = _bytes(k)
    for rel in crlf:
        new = rel.replace(f"{_OLD}/ADR-", f"{_NEW}/ADR-")
        assert got[new] == after[new].replace("\n", "\r\n").encode(), rel
    assert got[f"{_NEW}/ADR-0002-y.md"] == after[f"{_NEW}/ADR-0002-y.md"].replace("\n", "\r\n", 3).encode()
    assert got["base/questions/why.md"] == after["base/questions/why.md"].encode()


_ANGLE = ("# Record\n\nBob: [a](<{abs}/ADR-0001-x.md>), [b](<../{rel}/ADR-0001-x.md#context> \"X\"), "
          "![i](<{abs}/ADR-0001-x.md>), [spaced](<../base/systems/my pay.md>) and [c][r].\n\n"
          "[r]: /base/decisions/ADR-0001-x.md\n")


def test_move_decisions_rewrites_a_target_in_angle_brackets_and_leaves_a_reference_definition(tmp_path, capsys):
    rel = "fragments/2026-11-02-n.md"

    def bundle(d: str) -> dict[str, str]:
        return {**_b1(d == _NEW), rel: _concept("Knowledge Fragment", "N", _FRAGMENT.replace("2026-11-01", "2026-11-02"),
                                               _ANGLE.format(abs=f"/{d}", rel=d))}

    k = _bundle_30(tmp_path, bundle(_OLD))
    before = _findings(k)
    assert _move(k, capsys)[0] == 0
    assert _tree(k)[rel] == bundle(_NEW)[rel]
    assert _outside_link_targets(bundle(_OLD)[rel], bundle(_NEW)[rel]) == []
    renamed = sorted((level, code, path.replace(f"{_OLD}/ADR-", f"{_NEW}/ADR-"), msg.replace(f"{_OLD}/ADR-", f"{_NEW}/ADR-"))
                     for level, code, path, msg in before)
    assert before and _findings(k) == renamed


_UNCLOSED = ("# Record\n\nBob pasted a cut line: [ADR-0001](/base/decisions/ADR-0001-x.md\n\n"
             "Then [cut](</base/decisions/ADR-0001-x.md> and [titled](/base/decisions/ADR-0001-x.md \"X\"\n\n"
             "Closed: [ADR-0001](/{d}/ADR-0001-x.md), [t](/{d}/ADR-0001-x.md 'X'), [p](/{d}/ADR-0001-x.md (X)) "
             "and [s](/{d}/ADR-0001-x.md ).\n")


def test_move_decisions_leaves_a_link_whose_parenthesis_is_never_closed(tmp_path, capsys):
    from okf_common import extract_links

    rel = "fragments/2026-11-02-n.md"

    def bundle(d: str) -> dict[str, str]:
        return {**_b1(d == _NEW), rel: _concept("Knowledge Fragment", "N", _FRAGMENT.replace("2026-11-01", "2026-11-02"),
                                               _UNCLOSED.format(d=d))}

    cut = _UNCLOSED.partition("Closed:")[0]
    assert extract_links(cut) == []
    k = _bundle_30(tmp_path, bundle(_OLD))
    before = _tree(k)[rel]
    assert _move(k, capsys)[0] == 0
    after = _tree(k)[rel]
    assert after == bundle(_NEW)[rel] and after != before
    assert after.partition("Closed:")[0] == before.partition("Closed:")[0]
    assert _outside_link_targets(before, after) == []
    text = "---\ntype: Reference\n---\n" + cut
    assert rewrite_moved(text, rel, FileMove({f"{_OLD}/ADR-0001-x.md": f"{_NEW}/ADR-0001-x.md"})) == text


def test_move_decisions_dry_run_lists_the_moves_and_writes_nothing(tmp_path, capsys):
    k = _bundle_30(tmp_path, _b1(False))
    before = _bytes(k)
    rc, out, err = _move(k, capsys, "--dry-run")
    assert (rc, out, err) == (0, _B1_MOVES + _B1_SUMMARY.format(dry=" (dry-run)", k=k), "")
    assert _bytes(k) == before


def _nothing(k: Path) -> str:
    return f"nothing to move: every decision of {k} is in the directory its type declares\n"


def test_move_decisions_leaves_a_decision_already_in_the_directory_of_its_type(tmp_path, capsys):
    for name, files in (("placed", _b1(True)), ("none", {"log.md": _b1(True)["log.md"], "project.md": _concept("Project", "P")})):
        k = _bundle_30(tmp_path / name, files)
        before = _bytes(k)
        assert _move(k, capsys) == (0, _nothing(k), "")
        assert _bytes(k) == before


def test_move_decisions_run_twice_moves_nothing_the_second_time(tmp_path, capsys):
    k = _bundle_30(tmp_path, _b1(False))
    assert _move(k, capsys)[0] == 0
    before = _bytes(k)
    assert _move(k, capsys) == (0, _nothing(k), "")
    assert _bytes(k) == before


_LOG_30 = "# Bundle history\n\n## 2026-11-01\n* **Creation**: test.\n"
_DEC = _concept("Decision", "How", "decision_id: DEC-0001\ndecision_status: accepted\n")


def test_move_decisions_moves_a_plain_decision_out_of_the_architecture_directory(tmp_path, capsys):
    from okf_index import main as index_main

    k = _bundle_30(tmp_path, {"log.md": _LOG_30, "project.md": _concept("Project", "P"), f"{_NEW}/DEC-0001-how.md": _DEC})
    rc, out, err = _move(k, capsys)
    assert (rc, out, err) == (0, (
        f"MOVE {_NEW}/DEC-0001-how.md -> {_OLD}/DEC-0001-how.md\nLINKS {_NEW}/index.md\n"
        f"WROTE {_OLD}/index.md\nWROTE {_NEW}/index.md\n"
        f"NOTICE {_NEW}/ holds nothing but its index.md now; remove the directory by hand if it is not wanted\n"
        f"\n1 decision moved, each to the directory of its type, links rewritten in 1 file → {k}\n"), "")
    tree = _tree(k)
    assert sorted(rel for rel in tree if rel.startswith(_OLD)) == [
        f"{_OLD}/DEC-0001-how.md", f"{_NEW}/index.md", f"{_OLD}/index.md"]
    assert tree[f"{_OLD}/DEC-0001-how.md"] == _DEC
    assert tree[f"{_NEW}/index.md"] == _freshly_regenerated(k, tmp_path, _NEW)
    assert "DEC-0001-how.md" not in tree[f"{_NEW}/index.md"]
    assert tree[f"{_OLD}/index.md"] == _freshly_regenerated(k, tmp_path, _OLD)
    assert "(DEC-0001-how.md)" in tree[f"{_OLD}/index.md"]
    assert index_main([str(k), "--check"]) == 0


_LOCAL_TYPES = ("---\ntype: Domain Profile\ntitle: DP\ndescription: DP.\n" + _GEN + "types:\n"
                "  Standard Decision: { extends: Decision, description: A decision about the standard, "
                "directory: /base/decisions/standard/, prefix: SDR }\n"
                "  Product ADR: { extends: Architecture Decision, description: A product decision }\n"
                "{aliases}---\n\n# What this bundle holds\n\nText.\n")


def _decisions(k: Path) -> list[str]:
    return sorted(rel for rel in _no_indexes(_tree(k)) if rel.startswith(_OLD + "/"))


def test_move_decisions_takes_a_local_type_to_the_directory_it_declares(tmp_path, capsys):
    k = _bundle_30(tmp_path, {
        "log.md": _LOG_30, "project.md": _concept("Project", "P"), "base/profile.md": _LOCAL_TYPES.replace("{aliases}", ""),
        f"{_OLD}/SDR-0001-format.md": _concept("Standard Decision", "Format", "decision_id: SDR-0001\n"),
        f"{_OLD}/DEC-0001-how.md": _DEC})
    assert _move(k, capsys)[0] == 0
    assert _decisions(k) == [f"{_OLD}/DEC-0001-how.md", f"{_OLD}/standard/SDR-0001-format.md"]


def test_move_decisions_takes_a_local_type_without_a_directory_to_that_of_the_type_it_extends(tmp_path, capsys):
    k = _bundle_30(tmp_path, {
        "log.md": _LOG_30, "project.md": _concept("Project", "P"), "base/profile.md": _LOCAL_TYPES.replace("{aliases}", ""),
        f"{_OLD}/ADR-0001-p.md": _concept("Product ADR", "P", "adr_id: ADR-0001\n"),
        f"{_OLD}/DEC-0001-how.md": _DEC})
    assert _move(k, capsys)[0] == 0
    assert _decisions(k) == [f"{_OLD}/DEC-0001-how.md", f"{_NEW}/ADR-0001-p.md"]


def test_move_decisions_reads_local_type_and_key_names_through_the_aliases(tmp_path, capsys):
    aliases = "aliases:\n  types: { Decisión de producto: Product ADR }\n  fields: { reemplaza: supersedes, fuentes: sources }\n"
    files = {
        "log.md": _LOG_30, "project.md": _concept("Project", "P"),
        "base/profile.md": _LOCAL_TYPES.replace("{aliases}", aliases),
        f"{_OLD}/ADR-0001-p.md": _concept("Decisión de producto", "P", "adr_id: ADR-0001\n"),
        "base/decisions/standard/SDR-0001-format.md": _concept(
            "Standard Decision", "Format",
            f"decision_id: SDR-0001\nreemplaza: /{_OLD}/ADR-0001-p.md\n"
            f"fuentes:\n  - {{ id: p, resource: /{_OLD}/ADR-0001-p.md }}\n")}
    k = _bundle_30(tmp_path, files)
    assert _move(k, capsys)[0] == 0
    assert _decisions(k) == [f"{_NEW}/ADR-0001-p.md", f"{_OLD}/standard/SDR-0001-format.md"]
    assert _tree(k)[f"{_OLD}/standard/SDR-0001-format.md"] == files["base/decisions/standard/SDR-0001-format.md"].replace(
        f"/{_OLD}/ADR-0001-p.md", f"/{_NEW}/ADR-0001-p.md")


def test_move_decisions_of_an_open_instance_reads_the_profile_of_its_domain_bundle(tmp_path, capsys):
    kinds = "kinds:\n  Request: { extends: Operational Bundle, description: A request, directory: requests/ }\n"
    k = _bundle_30(tmp_path, {"log.md": _LOG_30, "project.md": _concept("Project", "P"),
                              "base/profile.md": _LOCAL_TYPES.replace("{aliases}", kinds)})
    inst = _bundle_at(k / "requests" / "req-1", {
        "index.md": _ROOT_30.replace("---\n\n", "kind: Request\nstate: open\nparent: ../..\n---\n\n"),
        "log.md": _LOG_30, "project.md": _concept("Project", "R"),
        f"{_OLD}/SDR-0001-format.md": _concept("Standard Decision", "Format", "decision_id: SDR-0001\n")})
    regenerate(k, index_targets(k))
    domain = _bytes(k)
    assert _move(inst, capsys)[0] == 0
    assert sorted(rel for rel in _no_indexes(_tree(inst)) if rel.startswith("base/")) == [f"{_OLD}/standard/SDR-0001-format.md"]
    assert {rel: b for rel, b in _bytes(k).items() if not rel.startswith("requests/req-1/")} == {
        rel: b for rel, b in domain.items() if not rel.startswith("requests/req-1/")}


_DRAFT = _concept("Architecture Decision", "Draft", "adr_id: ADR-0009\n",
                  "[X](ADR-0001-x.md) and [abs](/base/decisions/ADR-0001-x.md).\n")


def test_move_decisions_leaves_a_decision_okfignore_matches(tmp_path, capsys):
    ignored = {".okfignore": "base/decisions/ADR-0009-draft.md\nbase/decisions/drafts/\n",
               f"{_OLD}/ADR-0009-draft.md": _DRAFT, f"{_OLD}/drafts/ADR-0008-draft.md": _DRAFT}
    k = _bundle_30(tmp_path, {**_b1(False), **ignored})
    rc, out, err = _move(k, capsys)
    assert {rel: b for rel, b in _bytes(k).items() if rel in ignored} == {rel: t.encode() for rel, t in ignored.items()}
    assert sorted(rel for rel in _tree(k) if "draft" in rel) == [f"{_OLD}/ADR-0009-draft.md", f"{_OLD}/drafts/ADR-0008-draft.md"]
    assert (rc, out, err) == (0, _B1_MOVES + _B1_WROTE + _B1_SUMMARY.format(dry="", k=k), "")


def _instance(k: Path, rel: str, keys: str, name: str = "ADR-0001-n.md") -> None:
    """A nested bundle of k at rel, hand-made, holding an architecture decision outside the directory of its type."""
    b = k / rel
    (b / _OLD).mkdir(parents=True)
    (b / "index.md").write_text(f'---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n{keys}---\n\n# Subdirectories\n\n'
                                "* [base](base/index.md) - B.\n", encoding="utf-8")
    (b / "log.md").write_text(_LOG_30, encoding="utf-8")
    (b / "base" / "index.md").write_text("# base\n\n* [decisions](decisions/index.md) - D.\n", encoding="utf-8")
    (b / _OLD / "index.md").write_text(f"# decisions\n\n* [N]({name}) - N.\n", encoding="utf-8")
    (b / _OLD / name).write_text(_concept(
        "Architecture Decision", "N", "adr_id: ADR-0001\n", "[up](../../../../base/decisions/ADR-0001-x.md)\n"), encoding="utf-8")


_NESTED_NOTICE = ("NOTICE nested bundles not entered: nested/, requests/req-1/ (run okf_migrate.py --move-decisions on "
                  "each)\n")


def test_move_decisions_never_enters_a_nested_bundle(tmp_path, capsys):
    k = tmp_path / "knowledge"
    _instance(k, "requests/req-1", "kind: Request\nstate: open\nparent: ../..\n")
    _instance(k, "nested", "", "ADR-0003-m.md")
    k = _bundle_30(tmp_path, _b1(False))
    inside = {rel: b for rel, b in _bytes(k).items() if rel.startswith(("requests/req-1/", "nested/"))}
    rc, out, err = _move(k, capsys)
    assert len(inside) == 10
    assert {rel: b for rel, b in _bytes(k).items() if rel.startswith(("requests/req-1/", "nested/"))} == inside
    assert (rc, out, err) == (0, _NESTED_NOTICE + _B1_MOVES + _B1_WROTE + _B1_SUMMARY.format(dry="", k=k), "")
    assert _move(k, capsys) == (0, _NESTED_NOTICE + _nothing(k), "")


def test_move_decisions_stops_before_writing_when_a_new_path_is_taken_or_left_out(tmp_path, capsys):
    taken = _concept("Architecture Decision", "Other X", "adr_id: ADR-0001\n")
    cannot = f"ERROR: {_OLD}/ADR-0001-x.md cannot move to {_NEW}/ADR-0001-x.md: "
    cannot_y = f"ERROR: {_OLD}/ADR-0002-y.md cannot move to {_NEW}/ADR-0002-y.md: "
    nothing = "Nothing was written; settle each by hand and run the step again.\n"
    nested = f"NOTICE nested bundles not entered: {_NEW}/ (run okf_migrate.py --move-decisions on each)\n"
    cases = {
        "exists": ({f"{_NEW}/ADR-0001-x.md": taken}, "", cannot + f"{_NEW}/ADR-0001-x.md already exists\n" + nothing),
        "ignored": ({".okfignore": "base/decisions/architecture/\n"}, "",
                    cannot + ".okfignore matches it\n" + cannot_y + ".okfignore matches it\n" + nothing),
        "nested": ({f"{_NEW}/index.md": _ROOT_30}, nested,
                   cannot + "it lies in a nested bundle\n" + cannot_y + "it lies in a nested bundle\n" + nothing),
        "same": ({f"{_OLD}/old/ADR-0001-x.md": taken}, "",
                 f"ERROR: {_OLD}/old/ADR-0001-x.md cannot move to {_NEW}/ADR-0001-x.md: {_OLD}/ADR-0001-x.md moves "
                 "there too\n" + nothing)}
    for name, (extra, out, err) in cases.items():
        k = _bundle_30(tmp_path / name, {**_b1(False), **extra})
        for rel, text in extra.items():
            (k / rel).write_text(text, encoding="utf-8")
        before = _bytes(k)
        for flags in ((), ("--dry-run",)):
            result = _move(k, capsys, *flags)
            assert _bytes(k) == before
            assert result == (1, out, err)


def test_move_decisions_refuses_a_closed_bundle_and_one_that_is_not_knowledge_30(tmp_path, capsys):
    closed = tmp_path / "closed" / "requests" / "req-1"
    _instance(tmp_path / "closed", "requests/req-1",
              "kind: Request\nstate: closed\nclosed_at: 2026-11-08T10:00:00Z\nparent: ../..\n")
    closed_20 = tmp_path / "closed20" / "requests" / "req-1"
    _instance(tmp_path / "closed20", "requests/req-1", "kind: Request\nstate: closed\nparent: ../..\n")
    idx = closed_20 / "index.md"
    idx.write_text(idx.read_text(encoding="utf-8").replace('okf_profile: "knowledge/3.0"\n', ""), encoding="utf-8")
    old = _bundle_20(tmp_path / "old")
    bare = _bundle_20(tmp_path / "bare")
    idx = bare / "index.md"
    idx.write_text(idx.read_text(encoding="utf-8").replace('okf_profile: "knowledge/2.0"\n', ""), encoding="utf-8")
    is_closed = "ERROR: {k} is closed (state: closed): a closed bundle is never edited.\n"
    not_30 = ("ERROR: {k} declares profile {p}: --move-decisions needs a knowledge/3.0 bundle; run okf_migrate.py "
              "--profile knowledge/3.0 first.\n")
    expected = {closed: (1, "", is_closed.format(k=closed)), closed_20: (1, "", is_closed.format(k=closed_20)),
                old: (2, "", not_30.format(k=old, p="knowledge/2.0")),
                bare: (2, "", not_30.format(k=bare, p="none (knowledge/2.0)"))}
    for k, result in expected.items():
        before = _bytes(k)
        for flags in ((), ("--dry-run",)):
            found = _move(k, capsys, *flags)
            assert _bytes(k) == before
            assert found == result


def test_move_decisions_is_a_step_of_its_own(tmp_path, capsys):
    import pytest

    k = _bundle_30(tmp_path, _b1(False))
    before = _bytes(k)
    capsys.readouterr()
    found = {}
    for flags in (("--to", "0.2"), ("--profile", "knowledge/3.0"), ("--file", "project.md"), ("--out", str(tmp_path / "out")),
                  ("--to", "0.1", "--out", str(tmp_path / "out"))):
        with pytest.raises(SystemExit) as stop:
            main([str(k), "--move-decisions", *flags])
        found[flags] = (stop.value.code, capsys.readouterr().err.splitlines()[-1].partition(": error: ")[2])
    assert found == {flags: (2, "--move-decisions is a step of its own; it cannot be combined with --to, --profile, "
                                "--file or --out") for flags in found}
    assert len(found) == 5 and _bytes(k) == before and not (tmp_path / "out").exists()
    with pytest.raises(SystemExit) as stop:
        main([str(k)])
    assert (stop.value.code, capsys.readouterr().err.splitlines()[-1].partition(": error: ")[2]) == (
        2, "at least one of --to or --profile is required, or --move-decisions on its own")


def test_file_move_rewrites_a_target_for_any_map_of_old_to_new_paths():
    a, b, c = "base/decisions/ADR-0001-x.md", "base/decisions/ADR-0002-y.md", "base/decisions/ADR-0003-z.md"
    move = FileMove({a: "base/decisions/standard/SDR-0001-x.md", b: "base/decisions/DEC-0001-y.md",
                     c: "base/decisions/architecture/ADR-0003-z.md"},
                    exists=lambda rel: rel in (a, b, c, "base/systems/pay.md", "base/systems"))
    cases = {
        ("/" + a + "#context", "log.md"): "/base/decisions/standard/SDR-0001-x.md#context",
        ("base/decisions/ADR-0002-y.md", "log.md"): "base/decisions/DEC-0001-y.md",
        ("../decisions/ADR-0001-x.md", "base/systems/pay.md"): "../decisions/standard/SDR-0001-x.md",
        ("ADR-0002-y.md", a): "../DEC-0001-y.md",
        ("ADR-0001-x.md#why", b): "standard/SDR-0001-x.md#why",
        ("ADR-0001-x.md", c): "../standard/SDR-0001-x.md",
        ("../systems/pay.md", a): "../../systems/pay.md",
        ("../systems/", a): "../../systems/",
        ("../systems/pay.md", b): None,
        ("docs/bench.md", a): None,
        ("-", a): None,
        ("/base/systems/pay.md", a): None,
        ("https://example.com/" + a, "log.md"): None,
        ("#context", a): None,
    }
    assert {case: move.target(*case) for case in cases} == cases
    assert FileMove({a: "base/decisions/standard/SDR-0001-x.md"}).target("docs/bench.md", a) == "../docs/bench.md"


def test_rewrite_moved_reads_a_target_in_angle_brackets_whole_and_keeps_the_brackets():
    a = "base/decisions/ADR-0001-x.md"
    move = FileMove({a: "base/decisions/architecture/ADR-0001-x.md"})
    cases = {
        ("[a](</base/decisions/ADR-0001-x.md>)", "log.md"): "[a](</base/decisions/architecture/ADR-0001-x.md>)",
        ("![a](<base/decisions/ADR-0001-x.md#why> 'T')\r\n", "log.md"): "![a](<base/decisions/architecture/ADR-0001-x.md#why> 'T')\r\n",
        ("[a](<my notes/x y.md>) [b](<../systems/pay.md>)", a): "[a](<../my notes/x y.md>) [b](<../../systems/pay.md>)",
        ("[a](<>) [b](</base/decisions/ADR-0001-x.md) [c](<https://example.com/x y>)", "log.md"):
            "[a](<>) [b](</base/decisions/ADR-0001-x.md) [c](<https://example.com/x y>)",
        ("[r]: /base/decisions/ADR-0001-x.md\n[r]: </base/decisions/ADR-0001-x.md>\n", "log.md"):
            "[r]: /base/decisions/ADR-0001-x.md\n[r]: </base/decisions/ADR-0001-x.md>\n",
    }
    assert {case: rewrite_moved(*case, move) for case in cases} == cases


def test_move_decisions_regenerates_the_index_of_each_directory_above_a_destination_outside_the_one_left(tmp_path, capsys):
    from okf_index import main as index_main

    k = _bundle_30(tmp_path, {
        "log.md": _LOG_30, "project.md": _concept("Project", "P"),
        "base/profile.md": _LOCAL_TYPES.replace("{aliases}", "").replace("/base/decisions/standard/", "/base/standard/decisions/"),
        f"{_OLD}/SDR-0001-format.md": _concept("Standard Decision", "Format", "decision_id: SDR-0001\n"),
        f"{_OLD}/DEC-0001-how.md": _DEC})
    rc, out, err = _move(k, capsys)
    assert (rc, out, err) == (0, (
        f"MOVE {_OLD}/SDR-0001-format.md -> base/standard/decisions/SDR-0001-format.md\nLINKS {_OLD}/index.md\n"
        f"WROTE base/index.md\nWROTE {_OLD}/index.md\nWROTE base/standard/index.md\n"
        "WROTE base/standard/decisions/index.md\n"
        f"\n1 decision moved, each to the directory of its type, links rewritten in 1 file → {k}\n"), "")
    tree = _tree(k)
    assert sorted(rel for rel in tree if rel.startswith("base/standard")) == [
        "base/standard/decisions/SDR-0001-format.md", "base/standard/decisions/index.md", "base/standard/index.md"]
    for rel in ("base", _OLD, "base/standard", "base/standard/decisions"):
        assert tree[f"{rel}/index.md"] == _freshly_regenerated(k, tmp_path, rel), rel
    assert "(standard/index.md)" in tree["base/index.md"] and "SDR-0001" not in tree[f"{_OLD}/index.md"]
    assert index_main([str(k), "--check"]) == 0
    assert capsys.readouterr().out == "0 index.md out of date\n"


def test_move_decisions_rewrites_a_path_key_under_a_non_ascii_alias_and_a_quoted_key(tmp_path, capsys):
    aliases = "aliases:\n  fields: { ámbito: supersedes, 'fuentes de origen': sources }\n"
    sdr = "base/decisions/standard/SDR-0001-format.md"
    files = {
        "log.md": _LOG_30, "project.md": _concept("Project", "P"),
        "base/profile.md": _LOCAL_TYPES.replace("{aliases}", aliases),
        f"{_OLD}/ADR-0001-p.md": _concept("Product ADR", "P", "adr_id: ADR-0001\n"),
        sdr: _concept(
            "Standard Decision", "Format",
            f"decision_id: SDR-0001\n\"superseded_by\": /{_OLD}/ADR-0001-p.md  # quoted\n\"decision_status\": superseded\n"
            f"ámbito: [/{_OLD}/ADR-0001-p.md]\ntags: [/{_OLD}/ADR-0001-p.md]\n"
            f"'fuentes de origen':\n- {{ id: p, resource: /{_OLD}/ADR-0001-p.md }}\n")}
    k = _bundle_30(tmp_path, files)
    assert _move(k, capsys)[0] == 0
    assert _tree(k)[sdr] == _concept(
        "Standard Decision", "Format",
        f"decision_id: SDR-0001\n\"superseded_by\": /{_NEW}/ADR-0001-p.md  # quoted\n\"decision_status\": superseded\n"
        f"ámbito: [/{_NEW}/ADR-0001-p.md]\ntags: [/{_OLD}/ADR-0001-p.md]\n"
        f"'fuentes de origen':\n- {{ id: p, resource: /{_NEW}/ADR-0001-p.md }}\n")
    keys = {"ámbito: /x": ("ámbito", 7), '"superseded_by" : /x': ("superseded_by", 17), "'it''s': x": ("it's", 8),
            "a b:\r": ("a b", 4), "url: http://x": ("url", 4), "  nested: x": None, "- item: x": None, "# c: x": None,
            "http://x": None, '"open: x': None, "": None}
    assert {line: frontmatter_key(line) for line in keys} == keys


def _resource_forms(d: str) -> str:
    """A sources block with every way of writing an entry's resource that the step rewrites, then the ones it
    leaves: another key that ends in `resource`, a resource with no path and a path that is not alone on its line."""
    p = f"/{d}/ADR-0001-x.md"
    return ("sources:\n"
            f"  - id: a\n    resource: {p}\n"
            f"  - id: b\n    \"resource\": {p}\n"
            f"  - id: c\n    'resource' : '{p}#context'  # quoted\n"
            f"  - {{ \"id\": d, \"resource\": \"{p}\" }}\n"
            f"  - {{\"id\":\"e\",\"resource\":\"{p}\"}}\n"
            f"  - id: f\n    resource: >-\n      {p}\n"
            f"  - id: g\n    resource: |-\n      {p}\n"
            f"  - id: h\n    resource:  # on the next line\n      \"{p}\"\n"
            f"  - [ {{ id: i, resource: {p} }}, {{ id: j, resource: {p} }} ]\n"
            f"  - id: k\n    resource: {p}\r\n"
            "  - id: l\n    sub_resource: /base/decisions/ADR-0001-x.md\n"
            "  - id: m\n    resource:\n    title: /base/decisions/ADR-0001-x.md\n"
            "  - id: n\n    resource: >-\n      see /base/decisions/ADR-0001-x.md\n")


def test_move_decisions_rewrites_a_sources_resource_under_a_quoted_subkey_and_on_the_next_line(tmp_path, capsys):
    def bundle(d: str) -> dict[str, str]:
        return {"log.md": _LOG_30, "project.md": _concept("Project", "P"),
                f"{d}/ADR-0001-x.md": _concept("Architecture Decision", "X", "adr_id: ADR-0001\ndecision_status: accepted\n"),
                "base/systems/pay.md": _concept("System", "Pay", _resource_forms(d))}

    k = _bundle_30(tmp_path, bundle(_OLD))
    (k / "base/systems/pay.md").write_bytes(bundle(_OLD)["base/systems/pay.md"].encode())
    assert _move(k, capsys)[0] == 0
    assert (k / "base/systems/pay.md").read_bytes().decode() == bundle(_NEW)["base/systems/pay.md"]
    resources = [s.get("resource") for s in _parse((k / "base/systems/pay.md").read_text(encoding="utf-8"))[0]["sources"][:8]]
    assert resources == [f"/{_NEW}/ADR-0001-x.md", f"/{_NEW}/ADR-0001-x.md", f"/{_NEW}/ADR-0001-x.md#context",
                         *[f"/{_NEW}/ADR-0001-x.md"] * 5]


def test_rewrite_resource_reads_each_subkey_and_says_when_the_path_is_on_the_next_line():
    def new(target: str) -> str | None:
        return "/new.md" if target == "/old.md" else None

    lines = {
        ("    resource: /old.md", False): ("    resource: /new.md", False),
        ("    \"resource\": /old.md", False): ("    \"resource\": /new.md", False),
        ("- {'resource':'/old.md', id: a}", False): ("- {'resource':'/new.md', id: a}", False),
        ("- { resource: /old.md }, { resource: /other.md }, { resource: /old.md }", False):
            ("- { resource: /new.md }, { resource: /other.md }, { resource: /new.md }", False),
        ("    resource: >-", False): ("    resource: >-", True),
        ("    resource: |2+  # kept", False): ("    resource: |2+  # kept", True),
        ("    \"resource\":\r", False): ("    \"resource\":\r", True),
        ("- { resource: /old.md }, resource:", False): ("- { resource: /new.md }, resource:", True),
        ("", True): ("", True),
        ("      /old.md", True): ("      /new.md", False),
        ("      '/old.md'  # c\r", True): ("      '/new.md'  # c\r", False),
        ("      /old.md and more", True): ("      /old.md and more", False),
        ("    title: /old.md", True): ("    title: /old.md", False),
        ("/old.md", True): ("/old.md", False),
        ("    resource: /old.md", True): ("    resource: /new.md", False),
        ("    my-resource: /old.md", False): ("    my-resource: /old.md", False),
        ("    resource:/old.md", False): ("    resource:/old.md", False),
        ("    title: /old.md", False): ("    title: /old.md", False),
    }
    assert {k: rewrite_resource(*k, new) for k in lines} == lines


_RECORD_FORMS = ("# Record\n\n"
                 "Bob: [[ADR-0001]]({abs}/ADR-0001-x.md), [a \\] b]({abs}/ADR-0001-x.md), "
                 "[`list[0]` and ``a ` ]``](../{rel}/ADR-0001-x.md#context),\n"
                 "[![i](a.png)]({abs}/ADR-0001-x.md), [![i]({abs}/ADR-0001-x.md)](https://example.com), "
                 "![i](<{abs}/ADR-0001-x.md> 'it\\'s'), [q]({abs}/ADR-0001-x.md \"a \\\" b\"),\n"
                 "[n]({abs}/ADR-0001-x.md\n  \"on the next line\"), [c]({abs}/ADR-0001-x.md\n), "
                 "[p]({abs}/ADR-0001-x.md (a \\(b\\) c)) and [two]({abs}/ADR-0001-x.md 'two\nlines').\n\n"
                 "In code, as lint reads it: `[s]({abs}/ADR-0001-x.md)`.\n\n"
                 "```\n[f]({abs}/ADR-0001-x.md)\n```\n\n"
                 "Not links: [cut](/base/decisions/ADR-0001-x.md, \\[esc](/base/decisions/ADR-0001-x.md), "
                 "[t](/base/decisions/ADR-0001-x.md (a (b) c)), [far](/base/decisions/ADR-0001-x.md\n\n) and [c][r].\n\n"
                 "[r]: /base/decisions/ADR-0001-x.md\n")


def test_move_decisions_rewrites_every_inline_link_commonmark_defines(tmp_path, capsys):
    from okf_common import extract_links

    rel = "fragments/2026-11-02-n.md"

    def bundle(d: str) -> dict[str, str]:
        return {**_b1(d == _NEW), rel: _concept("Knowledge Fragment", "N", _FRAGMENT.replace("2026-11-01", "2026-11-02"),
                                               _RECORD_FORMS.format(abs=f"/{d}", rel=d))}

    k = _bundle_30(tmp_path, bundle(_OLD))
    before = _tree(k)[rel]
    assert _move(k, capsys)[0] == 0
    after = _tree(k)[rel]
    assert after == bundle(_NEW)[rel] and after != before
    assert _outside_link_targets(before, after) == []
    assert after.count(f"{_NEW}/ADR-0001-x.md") == 13 and after.count(f"/{_OLD}/ADR-0001-x.md") == 5
    in_code = "`[s](/x.md)`\n\n```\n[f](/y.md)\n```\n"
    assert extract_links(in_code) == ["/x.md", "/y.md"] == [in_code[x.start:x.end] for x in inline_links(in_code)]


def _marked(spec: str) -> tuple[str, list]:
    """spec without its marks, and the links the marks stand for: «target» of a link, ‹target› of an image."""
    from okf_common import InlineLink

    text, links, start = "", [], 0
    for ch in spec:
        if ch in "«‹":
            start = len(text)
        elif ch in "»›":
            links.append(InlineLink(start, len(text), ch == "›"))
        else:
            text += ch
    return text, links


_INLINE_LINKS = (
    "[a](«/x.md») and [b](«y.md#h» \"T\"), then [c]( «z.md» ).",
    "[[ADR-0001]](«/x.md») [a \\] b](«/x.md») [a \\[ b](«/x.md») [a [b] [c [d]]](«/x.md»)",
    "[a `]` b](«/x.md») [``a ` ]`` b](«/x.md») `[a](«/x.md»)` [a ` b](«/x.md»)",
    "[a ` b](/x.md) and ` closes the code span that holds the bracket; [b](«/y.md»)",
    "![i](‹a.png›) [![i](‹a.png›)](«/x.md») [![i](<‹a b.png›> 'T')](<«/my x.md»>) ![a [b](«/in.md») c](‹/img.png›)",
    "[a](<«/my x.md»> 'T') [b](<«»>) [c](«») [d](«/x(1)(2(3)).md») [e](«/x\\).md») [f](<«/x\\>y.md»>) [g](«\"t\"») [h](«/x.md\"T\"»)",
    "[a](«/x.md» \"a \\\" b\") [b](«/x.md» 'it\\'s') [c](«/x.md» (a \\) \\( b)) [d](«/x.md» \"(\") [e](«/x.md» ')')",
    "[a](«/x.md»\n\"T\") [b](«/x.md»\n) [c](\n«/x.md»\n  'T'\n) [d](«/x.md» \"two\nlines\")",
    "[a](«/x.md»\r\n\"T\"\r\n) [b](«/x.md»\r\n)\r\n\r\n[c](\r«/x.md»\r)",
    "```\n[a](«/x.md»)\n```\n\n    [b](«/y.md»)\n\n<!-- [c](«/z.md») -->\n",
    "[a [b](«/in.md») c](/out.md) [a ![i](‹i.png›) [b](«/in.md»)](/out.md) \\\\[a](«/x.md»)",
    "[a](/x.md",
    "[a](/x.md \"T\"",
    "[a](</x.md) [a](<x\ny.md>) [a](<x<y.md>)",
    "[a](/x.md\n\n) [a](/x.md \"T\n\nU\")",
    "[a\n\nb](/x.md)",
    "[r]: /x.md\n[r]: </x.md> \"T\"\n[a][r] [r][] [r]\n",
    "\\[a](/x.md) [a\\](/x.md) [a] (/x.md) [a]\n(/x.md)",
    "[a](/x.md \"T\" x) [a](/x.md and more) [a](/x (y).md [a](/x.md (a (b) c)) [a](/x.md 'T'\"U\")",
    "[a](/x.md \"T\"\n\n) [a](/x(.md) [a]",
)


def test_inline_links_gives_the_exact_span_of_each_target_commonmark_defines():
    cases = dict(_marked(spec) for spec in _INLINE_LINKS)
    assert len(cases) == len(_INLINE_LINKS)
    assert {text: inline_links(text) for text in cases} == cases
    assert sum(1 for links in cases.values() if not links) == 9


_PROFILE_FORMS = ("[q]({abs}decisions/ADR-0001-x.md \"a \\\" b\"), [n]({abs}decisions/ADR-0001-x.md\n\"T\"), "
                  "[c]({rel}decisions/ADR-0001-x.md\n), [p]({abs}decisions/ADR-0001-x.md (a (b) c)), "
                  "[s]({abs}decisions/ADR-0001-x.md 'X'),\n[cut]({abs}decisions/ADR-0001-x.md, "
                  "![img]({rel}decisions/ADR-0001-x.md) and \\[esc]({abs}decisions/ADR-0001-x.md);\n"
                  "left as written: [angle](</decisions/ADR-0001-x.md>), [[ADR-0001]](/decisions/ADR-0001-x.md), "
                  "[a \\] b](/decisions/ADR-0001-x.md) and [![i](a.png)](/decisions/ADR-0001-x.md).\n")
_PROFILE_FORMS_ADR = "[up]({up}project.md\n\"T\"), [in](ADR-0001-x.md 'X') and [angle](<../project.md>).\n"


def _profile_forms(k: Path) -> dict[str, str]:
    """_bundle_20 plus a fragment and a decision holding links in every form, migrated: the two files as written."""
    frag, adr = "fragments/2026-10-31-f.md", "decisions/ADR-0003-f.md"
    keys = "occurred_at: 2026-10-31\norigin: Weekly\nparticipants: [human:alice]\ndistillation_status: pending\n"
    (k / frag).write_text(_concept("Knowledge Fragment", "F", keys, _PROFILE_FORMS.format(abs="/", rel="../")), encoding="utf-8")
    (k / adr).write_text(_concept("Architecture Decision", "F", body=_PROFILE_FORMS_ADR.format(up="../")), encoding="utf-8")
    assert main([str(k), "--profile", "knowledge/3.0"]) == 0
    return {rel: (k / rel).read_text(encoding="utf-8") for rel in (frag, "base/" + adr)}


def test_profile_step_rewrites_the_links_main_rewrote_and_no_other(tmp_path):
    """What okf_migrate.py of main 54ff9d0 writes for these links, byte for byte: the profile step keeps its own
    reading of a link (MD_LINK_RE), which is not the one --move-decisions uses."""
    assert MD_LINK_RE.pattern == r"(!?\[[^\]]*\]\()([^)\s]+)"
    keys = "occurred_at: 2026-10-31\norigin: Weekly\nparticipants: [human:alice]\ndistillation_status: pending\n"
    assert _profile_forms(_bundle_20(tmp_path)) == {
        "fragments/2026-10-31-f.md": _concept("Knowledge Fragment", "F", keys,
                                              _PROFILE_FORMS.format(abs="/base/", rel="../base/")),
        "base/decisions/ADR-0003-f.md": _concept("Architecture Decision", "F",
                                                 body=_PROFILE_FORMS_ADR.format(up="../../"))}


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
