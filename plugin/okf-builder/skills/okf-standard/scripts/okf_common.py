"""Shared utilities for the OKF tools of the okf-builder plugin.

Requires PyYAML. The entry scripts declare it in PEP 723 metadata, so
`uv run <script>.py` installs it; plain `python3` works where it is installed.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "okf: PyYAML is missing; run the script with `uv run <script>.py` "
        "or install it with `pip install pyyaml`\n"
    )
    raise SystemExit(2)

RESERVED = {"index.md", "log.md"}
PROFILE_20 = "knowledge/2.0"
PROFILE_30 = "knowledge/3.0"
FRAGMENTS_DIR, BASE_DIR, PROJECTIONS_DIR = "fragments", "base", "projections"
LAYER_DIRS = (FRAGMENTS_DIR, BASE_DIR, PROJECTIONS_DIR)
ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ACTOR_RE = re.compile(r"^(human:[^\s/]+|process:[^\s/]+|[^\s/:]+/[^\s/]+)$")
KEBAB_RE = re.compile(r"^(ADR-\d{4}-)?[a-z0-9]+(-[a-z0-9]+)*\.md$")
LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
VALID_STATUS = {"draft", "stable", "deprecated"}


def run_tests(script: str, argv: list[str]) -> int:
    """Run the pytest functions in `script`; `argv` holds extra pytest arguments."""
    try:
        import pytest
    except ImportError:
        sys.stderr.write("okf: pytest is missing; run the tests with `uv run --with pytest <script>.py --test`\n")
        return 2
    return pytest.main([script, "-q", "-p", "no:cacheprovider", *argv])


def parse_yaml(text: str) -> dict:
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------
@dataclass
class Doc:
    path: Path
    rel: str  # path relative to the bundle, with /
    frontmatter: dict | None
    body: str
    fm_error: str | None = None
    has_fm_block: bool = False

    @property
    def is_reserved(self) -> bool:
        return self.path.name in RESERVED

    @property
    def concept_id(self) -> str:
        return self.rel[:-3] if self.rel.endswith(".md") else self.rel


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    return None, text


def load_doc(bundle: Path, path: Path) -> Doc:
    text = path.read_text(encoding="utf-8")
    raw, body = split_frontmatter(text)
    rel = path.relative_to(bundle).as_posix()
    if raw is None:
        return Doc(path, rel, None, body, None, False)
    try:
        fm = parse_yaml(raw)
        return Doc(path, rel, fm, body, None, True)
    except Exception as e:  # noqa: BLE001
        return Doc(path, rel, None, body, str(e), True)


def walk_bundle(bundle: Path) -> list[Doc]:
    """Every .md of the bundle; hidden dirs and the root projections/ (not OKF, ADR-0019) are skipped."""
    docs = []
    for root, dirs, files in os.walk(bundle):
        at_root = Path(root) == bundle
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (at_root and d == PROJECTIONS_DIR))
        for f in sorted(files):
            if f.endswith(".md"):
                docs.append(load_doc(bundle, Path(root) / f))
    return docs


OKFIGNORE = ".okfignore"


def _glob_re(pat: str) -> str:
    """A gitignore glob as a regex over a whole path: '**' crosses '/', '*' and '?' do not, [...] is a class."""
    out, i = "", 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pat.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pat[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pat[i] == "?":
            out, i = out + "[^/]", i + 1
        elif pat[i] == "[" and "]" in pat[i + 2:]:
            j = pat.index("]", i + 2)
            body = pat[i + 1:j]
            out, i = out + "[" + ("^" + body[1:] if body[:1] == "!" else body).replace("\\", "\\\\") + "]", j + 1
        else:
            out, i = out + re.escape(pat[i]), i + 1
    return out


@dataclass
class OkfIgnore:
    """The .okfignore of a bundle root: gitignore-style globs, one per line, matched against paths from the root.

    A blank line or one that starts with '#' is skipped; '\\#' and '\\!' stand for a literal first character.
    '!' re-includes what an earlier line excluded; a trailing '/' matches directories only; a pattern with a '/'
    other than a trailing one is anchored at the root (a leading '/' only anchors), one without matches a name at
    any depth; '**' crosses directories. The last matching line wins. As in git, a file under an excluded
    directory cannot be re-included: the directory is never entered."""
    rules: list[tuple[re.Pattern, bool, bool]] = field(default_factory=list)  # (regex, negated, directories only)

    @classmethod
    def parse(cls, text: str) -> "OkfIgnore":
        rules = []
        for line in text.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            neg = line.startswith("!")
            if neg or line.startswith("\\"):
                line = line[1:]
            dir_only = line.endswith("/")
            line = line.rstrip("/")
            if not line:
                continue
            anchored = "/" in line
            rx = _glob_re(line.lstrip("/"))
            rules.append((re.compile(("" if anchored else "(?:.*/)?") + rx + r"\Z"), neg, dir_only))
        return cls(rules)

    @classmethod
    def load(cls, bundle: Path) -> "OkfIgnore":
        f = bundle / OKFIGNORE
        return cls.parse(f.read_text(encoding="utf-8")) if f.is_file() else cls()

    def match(self, rel: str, is_dir: bool) -> bool:
        hit = False
        for rx, neg, dir_only in self.rules:
            if (is_dir or not dir_only) and rx.match(rel):
                hit = not neg
        return hit


def okf_shaped(doc: Doc) -> bool:
    """A Markdown file that reads as an OKF document: frontmatter with a key of the spec (SPEC_KEYS: type, title,
    description, generated, verified, sources, status, tags, stale_after, resource, timestamp...), or one that
    cannot be parsed. A concept that lost its type and its title keeps NO_TYPE, a broken one its BAD_YAML."""
    if not doc.has_fm_block:
        return False
    return doc.frontmatter is None or bool(SPEC_KEYS & set(doc.frontmatter))


@dataclass
class Scan:
    """What a linter reads of a bundle (scan_bundle): its documents, and what it leaves out and why."""
    docs: list[Doc]
    ignored: list[str] = field(default_factory=list)  # paths .okfignore excludes; a directory ends with '/'
    nested: list[str] = field(default_factory=list)  # directories whose index.md declares okf_version, with '/'
    reserved: list[str] = field(default_factory=list)  # paths .okfignore matches but cannot exclude (reserved_path)
    not_okf: list[tuple[str, int]] = field(default_factory=list)  # (directory with '/', its Markdown files)

    def excluded(self, bundle: Path) -> set[Path]:
        """The resolved paths left out: the ignored files and directories, the nested bundles, the non-OKF directories."""
        rels = [*self.ignored, *self.nested, *(d for d, _ in self.not_okf)]
        return {(bundle / r.rstrip("/")).resolve() for r in rels}


PROFILE_REL = f"{BASE_DIR}/profile.md"
# The reserved files of the root (ADR-0018 decision 3) and the bundle's Domain Profile: .okfignore never excludes them
RESERVED_PATHS = ("index.md", "log.md", "project.md", "conflict-log.md", PROFILE_REL)


def reserved_path(rel: str) -> bool:
    """A file .okfignore cannot exclude: one of RESERVED_PATHS, or the index.md of any directory."""
    return rel in RESERVED_PATHS or rel.endswith("/index.md")


def scan_bundle(bundle: Path) -> Scan:
    """The documents walk_bundle reads, less three things a linter does not judge as part of the bundle:
    the paths .okfignore matches, a nested bundle (a subdirectory other than a root layer whose index.md declares
    its own okf_version, skipped as a whole), and a non-OKF directory (one that is not the root nor a root layer,
    has no index.md, and whose Markdown files all lack OKF frontmatter: okf_shaped). A directory that mixes OKF
    documents and plain files keeps every file. A match of .okfignore on a reserved_path, or on base/ while it
    holds base/profile.md, is not excluded: it is read as usual and listed under reserved."""
    ign = OkfIgnore.load(bundle)
    sc = Scan([])
    for root, dirs, files in os.walk(bundle):
        here = Path(root)
        at_root = here == bundle
        prefix = "" if at_root else here.relative_to(bundle).as_posix() + "/"
        keep = []
        for d in sorted(dirs):
            if d.startswith(".") or (at_root and d == PROJECTIONS_DIR):
                continue
            layer_dir = at_root and d in LAYER_DIRS
            if ign.match(prefix + d, True):
                if not (prefix + d + "/" + "profile.md" == PROFILE_REL and (here / PROFILE_REL).is_file()):
                    sc.ignored.append(prefix + d + "/")
                    continue
                sc.reserved.append(prefix + d + "/")
            if not layer_dir and declared_version(here / d) is not None:
                sc.nested.append(prefix + d + "/")
            else:
                keep.append(d)
        dirs[:] = keep
        found = []
        for f in sorted(files):
            if ign.match(prefix + f, False):
                if not reserved_path(prefix + f):
                    sc.ignored.append(prefix + f)
                    continue
                sc.reserved.append(prefix + f)
            if f.endswith(".md"):
                found.append(load_doc(bundle, here / f))
        candidate = not at_root and not (here.parent == bundle and here.name in LAYER_DIRS) and "index.md" not in files
        if candidate and found and not any(okf_shaped(d) for d in found):
            sc.not_okf.append((prefix, len(found)))
            continue
        sc.docs += found
    return sc


def extract_links(body: str) -> list[str]:
    return [m.group(2) for m in LINK_RE.finditer(body)]


def resolve_link(bundle: Path, doc: Doc, target: str) -> Path | None:
    """Return the on-disk path of an internal link, or None if it is external."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    if target.startswith("/"):
        return (bundle / target.lstrip("/")).resolve()
    return (doc.path.parent / target).resolve()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_iso(ts: Any) -> bool:
    """An ISO 8601 datetime with an explicit offset that names a real moment."""
    if isinstance(ts, datetime):
        return ts.tzinfo is not None
    return to_dt(ts) is not None


def is_iso_date_or_datetime(v: Any) -> bool:
    """A calendar date (YYYY-MM-DD) or an ISO 8601 datetime with an explicit offset."""
    if isinstance(v, datetime):
        return v.tzinfo is not None
    if isinstance(v, date):
        return True
    if isinstance(v, str) and DATE_RE.match(v):
        try:
            date.fromisoformat(v)
        except ValueError:
            return False
        return True
    return is_iso(v)


def to_dt(ts: Any) -> datetime | None:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, str) and ISO_RE.match(ts):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def as_list(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


V02_KEYS = {"generated", "verified", "sources", "status", "stale_after", "usage_window",
            "runtime", "parameters", "computation", "executor", "attester"}
V01_SIGNALS = {"timestamp"}
# the keys every concept may carry: the spec's (OKF v0.1 and v0.2) and those of the standard's §3.1
SPEC_KEYS = frozenset({"type", "title", "description", "resource", "tags", "timestamp"}) | V02_KEYS
CITATIONS_RE = re.compile(r"^#\s+Citations\s*$", re.M)
SUPPORTED_VERSIONS = ("0.1", "0.2")


def _root_key(bundle: Path, key: str) -> str | None:
    idx = bundle / "index.md"
    if not idx.exists():
        return None
    raw, _ = split_frontmatter(idx.read_text(encoding="utf-8"))
    if raw is None:
        return None
    try:
        v = parse_yaml(raw).get(key)
    except Exception:  # noqa: BLE001
        return None
    return str(v) if v is not None else None


def declared_version(bundle: Path) -> str | None:
    return _root_key(bundle, "okf_version")


def declared_profile(bundle: Path) -> str | None:
    """okf_profile of the root index.md, or None."""
    return _root_key(bundle, "okf_profile")


def knowledge_root(bundle: Path) -> Path:
    """Directory that holds the typed directories: base/ in knowledge/3.0, the bundle root otherwise."""
    return bundle / BASE_DIR if declared_profile(bundle) == PROFILE_30 else bundle


def knowledge_dirs(bundle: Path) -> list[Path]:
    """The typed directories of the bundle (under base/ in knowledge/3.0, at the root in knowledge/2.0)."""
    root = knowledge_root(bundle)
    if not root.is_dir():
        return []
    return [p for p in sorted(root.iterdir()) if p.is_dir() and not p.name.startswith(".")
            and not (root == bundle and p.name in LAYER_DIRS)]


def version_signals(docs: list[Doc]) -> tuple[int, int]:
    """(n concepts with 0.2 signals, n concepts with 0.1 signals)."""
    s02 = s01 = 0
    for d in docs:
        if d.is_reserved or not d.frontmatter:
            continue
        fm = d.frontmatter
        has02 = bool(V02_KEYS & set(fm)) or fm.get("type") == "Attested Computation"
        has01 = bool(V01_SIGNALS & set(fm)) or bool(CITATIONS_RE.search(d.body))
        s02 += has02
        s01 += has01
    return s02, s01


def detect_version(bundle: Path, docs: list[Doc] | None = None) -> tuple[str, str]:
    """Return (version, origin) with origin in {declared, heuristic, default, mixed}."""
    dv = declared_version(bundle)
    if dv in SUPPORTED_VERSIONS:
        return dv, "declared"
    docs = docs if docs is not None else walk_bundle(bundle)
    s02, s01 = version_signals(docs)
    if s02 and s01:
        return "0.2", "mixed"
    if s02:
        return "0.2", "heuristic"
    if s01:
        return "0.1", "heuristic"
    return "0.2", "default"


def find_bundle(start: Path | None = None) -> Path | None:
    """Search upwards from start (or cwd) for knowledge/."""
    p = (start or Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "knowledge" / "index.md").exists():
            return cand / "knowledge"
        if cand.name == "knowledge" and (cand / "index.md").exists():
            return cand
    return None
