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
ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ACTOR_RE = re.compile(r"^(human:[^\s/]+|process:[^\s/]+|[^\s/:]+/[^\s/]+)$")
KEBAB_RE = re.compile(r"^(ADR-\d{4}-)?[a-z0-9]+(-[a-z0-9]+)*\.md$")
LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
VALID_STATUS = {"draft", "stable", "deprecated"}
VALID_DISTILLATION = ("pending", "distilled", "conflict")


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
    docs = []
    for root, dirs, files in os.walk(bundle):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for f in sorted(files):
            if f.endswith(".md"):
                docs.append(load_doc(bundle, Path(root) / f))
    return docs


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
    if isinstance(ts, datetime):
        return ts.tzinfo is not None
    return isinstance(ts, str) and bool(ISO_RE.match(ts))


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
    return isinstance(v, str) and bool(ISO_RE.match(v))


def to_dt(ts: Any) -> datetime | None:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, str) and ISO_RE.match(ts):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return None


def as_list(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


V02_KEYS = {"generated", "verified", "sources", "status", "stale_after", "usage_window",
            "runtime", "parameters", "computation", "executor", "attester"}
V01_SIGNALS = {"timestamp"}
CITATIONS_RE = re.compile(r"^#\s+Citations\s*$", re.M)
SUPPORTED_VERSIONS = ("0.1", "0.2")


def declared_version(bundle: Path) -> str | None:
    idx = bundle / "index.md"
    if not idx.exists():
        return None
    raw, _ = split_frontmatter(idx.read_text(encoding="utf-8"))
    if raw is None:
        return None
    try:
        v = parse_yaml(raw).get("okf_version")
    except Exception:  # noqa: BLE001
        return None
    return str(v) if v is not None else None


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
