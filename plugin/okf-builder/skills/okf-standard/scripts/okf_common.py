"""Shared utilities for the OKF tools of the okf-builder plugin.

No external dependencies: PyYAML is used when installed; otherwise a reduced
YAML parser that is enough for OKF frontmatter (maps, lists, flow mappings
`{ a: b }`, flow lists `[a, b]`, scalars, multi-line scalars and block scalars
`|`, `|-`, `>`, `>-`). OKF_NO_PYYAML=1 forces the reduced parser.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESERVED = {"index.md", "log.md"}
ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$"
)
ACTOR_RE = re.compile(r"^(human:[^\s/]+|process:[^\s/]+|[^\s/:]+/[^\s/]+)$")
KEBAB_RE = re.compile(r"^(ADR-\d{4}-)?[a-z0-9]+(-[a-z0-9]+)*\.md$")
LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
VALID_STATUS = {"draft", "stable", "deprecated"}

try:  # pragma: no cover
    import yaml as _yaml  # type: ignore
except Exception:  # pragma: no cover
    _yaml = None
if os.environ.get("OKF_NO_PYYAML") == "1":
    _yaml = None


# --------------------------------------------------------------------------
# Reduced YAML
# --------------------------------------------------------------------------
def _scalar(tok: str) -> Any:
    t = tok.strip()
    if t == "" or t in ("~", "null", "Null", "NULL"):
        return None
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if t[:1] in ('"', "'"):
        if _closing_quote(t, t[0]) != len(t) - 1:
            raise ValueError(f"unclosed quote or text after the closing quote: {t!r}")
        return _unescape_double(t[1:-1]) if t[0] == '"' else t[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    if t.startswith("{") and t.endswith("}"):
        return _flow_map(t[1:-1])
    if t.startswith("[") and t.endswith("]"):
        return _flow_list(t[1:-1])
    return t


_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t", "r": "\r", "0": "\0"}


def _unescape_double(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        esc = s[i + 1 : i + 2]
        if esc and esc in _ESCAPES:
            out.append(_ESCAPES[esc])
            i += 2
            continue
        if esc == "u":
            hexa = s[i + 2 : i + 6]
            if not re.fullmatch(r"[0-9A-Fa-f]{4}", hexa):
                raise ValueError(f"\\u escape without 4 hex digits: {s!r}")
            code = int(hexa, 16)
            if 0xD800 <= code <= 0xDFFF:
                raise ValueError(f"\\u{hexa} escape (surrogate) not supported: {s!r}")
            out.append(chr(code))
            i += 6
            continue
        raise ValueError(f"\\{esc} escape not supported in double quotes: {s!r}")
    return "".join(out)


def _split_top(s: str, sep: str = ",") -> list[str]:
    out, depth, cur, quote, escaped = [], 0, "", None, False
    for ch in s:
        if quote:
            cur += ch
            if escaped:
                escaped = False
            elif quote == '"' and ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            cur += ch
        elif ch in "[{":
            depth += 1
            cur += ch
        elif ch in "]}":
            depth -= 1
            cur += ch
        elif ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _flow_map(s: str) -> dict:
    d: dict = {}
    for item in _split_top(s):
        if ":" not in item:
            continue
        k, v = item.split(":", 1)
        d[k.strip()] = _scalar(v)
    return d


def _flow_list(s: str) -> list:
    return [_scalar(x) for x in _split_top(s) if x.strip()]


def _strip_comment(line: str) -> str:
    out, quote, escaped = "", None, False
    for i, ch in enumerate(line):
        if quote:
            out += ch
            if escaped:
                escaped = False
            elif quote == '"' and ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out += ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        else:
            out += ch
    return out.rstrip()


_BLOCK_HEADERS = {"|", "|-", ">", ">-"}
_CLOSERS = {'"': '"', "'": "'", "{": "}", "[": "]"}


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _check_tab(line: str) -> None:
    if "\t" in line[: _indent_of(line)]:
        raise ValueError(f"tab in indentation not supported: {line!r}")


def _check_line(line: str) -> None:
    # a line that opens a map entry or a list item; continuation lines of a
    # scalar are only checked with _check_tab
    _check_tab(line)
    _check_start(line, line, inline=False)


def _check_dash_value(t: str, line: str) -> None:
    t = t.strip()
    if t == "-" or t.startswith("- "):
        raise ValueError(f"dash as a value (compact sequence - -) not supported: {line!r}")


def _closing_quote(text: str, q: str) -> int | None:
    i = 1
    while i < len(text):
        ch = text[i]
        if q == '"' and ch == "\\":
            i += 2
            continue
        if ch == q:
            if q == "'" and text[i + 1 : i + 2] == "'":
                i += 2
                continue
            return i
        i += 1
    return None


_INDICATORS = {
    "{": "flow map { }",
    "[": "flow list [ ]",
    "&": "anchors (&)",
    "*": "aliases (*)",
    "!": "tags (!)",
    "?": "complex keys (?)",
    "%": "directives (%)",
    "@": "reserved character @",
    "`": "reserved character `",
    "|": "block scalar |",
    ">": "block scalar >",
}


def _check_start(t: str, line: str, inline: bool) -> None:
    # the reduced-YAML rule: an indicator is only accepted as a value on the
    # same line as its key or dash, and only { }, [ ] and |, |-, >, >-
    t = t.strip()
    c = t[:1]
    if c not in _INDICATORS:
        return
    if inline and (c in "{[" or t in _BLOCK_HEADERS):
        return
    if not inline and c in "{[|>":
        raise ValueError(
            f"{_INDICATORS[c]} is only accepted on the same line as its key or dash: {line!r}"
        )
    if c in "|>":
        raise ValueError(f"{_INDICATORS[c]} not supported (only |, |-, >, >-): {line!r}")
    raise ValueError(f"{_INDICATORS[c]} not supported: {line!r}")


def _mini_yaml(text: str) -> dict:
    """Reduced YAML. It only accepts: block maps and lists (including "- key: v"),
    plain and quoted scalars (on one line or continued on more indented lines),
    block scalars |, |-, >, >- and flow collections { } and [ ] that open on the
    same line as their key or dash. Everything else is a ValueError."""
    raw = text.splitlines()
    for r in raw:
        if r.rstrip() in ("---", "..."):
            raise ValueError(f"multi-document YAML not supported: {r!r}")
    # significant lines (no comments, not blank) and their position in `raw`
    lines: list[str] = []
    pos: list[int] = []
    commented: set[int] = set()
    # blank or comment-only lines with a tab in the indentation: an error unless
    # they fall inside a quoted or block scalar (`in_scalar`)
    tab_blank: list[int] = []
    in_scalar: set[int] = set()
    for i, r in enumerate(raw):
        l = _strip_comment(r)
        if l.strip():
            if l != r.rstrip():
                commented.add(len(lines))
            lines.append(l)
            pos.append(i)
        elif "\t" in r[: _indent_of(r)]:
            tab_blank.append(i)

    def first_line_from(raw_idx: int) -> int:
        j = 0
        while j < len(pos) and pos[j] < raw_idx:
            j += 1
        return j

    def block_scalar(idx: int, indent: int, header: str):
        # | |- > >- are read from `raw` to keep '#' and blank lines;
        # the body indentation counts spaces only
        start = end = pos[idx] + 1
        body_indent = None
        while end < len(raw):
            r = raw[end]
            if r.strip():
                ind = len(r) - len(r.lstrip(" "))
                if (body_indent is None and ind <= indent) or (body_indent is not None and ind < body_indent):
                    break
                if body_indent is None:
                    body_indent = ind
            end += 1
        in_scalar.update(range(start, end))
        if body_indent is None:
            for r in raw[start:end]:
                if "\t" in r:
                    raise ValueError(f"tab in a whitespace-only line of a block scalar: {r!r}")
            return "", first_line_from(end)
        # as in PyYAML: a line longer than the body indentation is text
        # (even if it is only spaces); the other blank lines are line breaks
        leading, segs, last = 0, [], start
        for i in range(start, end):
            r = raw[i]
            spaces = len(r) - len(r.lstrip(" "))
            if not r.strip() and spaces < body_indent and r[spaces:]:
                raise ValueError(f"tab in the indentation of a block scalar not supported: {r!r}")
            if len(r) > body_indent:
                if not segs and not r.strip():
                    raise ValueError(
                        f"leading whitespace-only line indented deeper than the block scalar: {raw[pos[idx]]!r}"
                    )
                segs.append([r[body_indent:], 0])
                last = i
            elif segs:
                segs[-1][1] += 1
            else:
                leading += 1
        out = "\n" * leading
        for n, (c, breaks) in enumerate(segs):
            out += c
            if n + 1 < len(segs):
                nxt = segs[n + 1][0]
                if header[0] == ">" and c[:1] not in " \t" and nxt[:1] not in " \t":
                    out += "" if breaks else " "
                else:
                    out += "\n"
                out += "\n" * breaks
        if not header.endswith("-") and (last + 1 < len(raw) or text.endswith(("\n", "\r"))):
            out += "\n"
        return out, first_line_from(end)

    def quoted_scalar(idx: int, indent: int, t: str):
        # a quoted scalar that continues on other lines is read from `raw`:
        # inside the quotes '#' is text, not a comment
        q, text, end, blanks = t[0], t, pos[idx] + 1, 0
        while True:
            close = _closing_quote(text, q)
            if close is not None:
                rest = text[close + 1 :]
                if rest.strip() and not (rest[:1] in " \t" and rest.strip().startswith("#")):
                    raise ValueError(f"text after the closing quote: {raw[end - 1]!r}")
                in_scalar.update(range(pos[idx] + 1, end))
                return _scalar(text[: close + 1]), first_line_from(end)
            if end >= len(raw) or (raw[end].strip() and _indent_of(raw[end]) <= indent):
                raise ValueError(f"unclosed quote: {raw[pos[idx]]!r}")
            r = raw[end]
            end += 1
            if not r.strip():
                blanks += 1
                continue
            _check_tab(r)
            if q == '"' and (len(text) - len(text.rstrip("\\"))) % 2:
                raise ValueError(f"escaped line break (\\ at end of line) not supported: {raw[pos[idx]]!r}")
            text +=("\n" * blanks if blanks else " ") + r.strip()
            blanks = 0

    def plain_scalar(idx: int, indent: int, v: str):
        # a scalar that continues on more indented lines is joined with a space
        t = v.strip()
        if t[:1] in ('"', "'"):
            return quoted_scalar(idx, indent, t)
        closed = len(t) > 1 and t[0] in _CLOSERS and t[-1] == _CLOSERS[t[0]]
        parts, nxt = [t], idx + 1
        if not closed and t[:1] == "{" and nxt < len(lines) and _indent_of(lines[nxt]) > indent:
            raise ValueError(f"multi-line flow map {{ }} not supported: {lines[idx]!r}")
        while not closed and nxt < len(lines) and _indent_of(lines[nxt]) > indent:
            _check_tab(lines[nxt])
            c = lines[nxt].strip()
            if t[:1] not in "{[" and (": " in c or c.endswith(":")):
                raise ValueError(f"unexpected indentation: {lines[nxt]!r}")
            gap = raw[pos[nxt - 1] + 1 : pos[nxt]]
            if (nxt - 1) in commented or any(g.strip() for g in gap):
                raise ValueError(f"comment inside a multi-line scalar: {lines[nxt]!r}")
            parts.append("\n" * len(gap) if gap else " ")
            parts.append(c)
            nxt += 1
        joined = "".join(parts)
        if t[0] in "{[" and not joined.endswith(_CLOSERS[t[0]]):
            raise ValueError(f"'{t[0]}' unclosed or with text after the closer: {lines[idx]!r}")
        if len(parts) == 1:
            return _scalar(t), nxt
        return (_scalar(joined) if t[0] in _CLOSERS else joined), nxt

    def value(idx: int, indent: int, v: str):
        _check_start(v, lines[idx], inline=True)
        _check_dash_value(v, lines[idx])
        if v.strip() in _BLOCK_HEADERS:
            return block_scalar(idx, indent, v.strip())
        return plain_scalar(idx, indent, v)

    def parse_block(idx: int, indent: int):
        # returns (value, next_idx)
        if idx >= len(lines):
            return None, idx
        first = lines[idx]
        if first.strip().startswith("- "):
            return parse_list(idx, indent)
        return parse_map(idx, indent)

    def parse_map(idx: int, indent: int):
        d: dict = {}
        while idx < len(lines):
            line = lines[idx]
            _check_line(line)
            ind = len(line) - len(line.lstrip())
            if ind < indent or line.strip().startswith("- "):
                break
            if ind > indent:
                raise ValueError(f"unexpected indentation: {line!r}")
            if ":" not in line:
                raise ValueError(f"line without ':' in a map: {line!r}")
            k, v = line.strip().split(":", 1)
            k = k.strip()
            if v.strip() == "":
                nxt = idx + 1
                if nxt < len(lines):
                    nind = len(lines[nxt]) - len(lines[nxt].lstrip())
                    if nind > indent or (nind == indent and lines[nxt].strip().startswith("- ")):
                        val, idx = parse_block(nxt, nind)
                        d[k] = val
                        continue
                d[k] = None
                idx += 1
            else:
                d[k], idx = value(idx, indent, v)
        return d, idx

    def parse_list(idx: int, indent: int):
        lst: list = []
        while idx < len(lines):
            line = lines[idx]
            _check_line(line)
            ind = len(line) - len(line.lstrip())
            if ind != indent or not line.strip().startswith("- "):
                break
            rest = line.strip()[2:]
            _check_dash_value(rest, line)
            if ":" in rest and not rest.lstrip().startswith(("{", "[", '"', "'")):
                # inline map that starts on the dash line
                k, v = rest.split(":", 1)
                sub_indent = ind + 2
                lines[idx] = " " * sub_indent + rest
                val, idx = parse_map(idx, sub_indent)
                lst.append(val)
            else:
                val, idx = value(idx, indent, rest)
                lst.append(val)
        return lst, idx

    val, _ = parse_block(0, 0)
    for i in tab_blank:
        if i not in in_scalar:
            raise ValueError(f"tab in the indentation of a blank or comment line not supported: {raw[i]!r}")
    return val if isinstance(val, dict) else {}


def parse_yaml(text: str) -> dict:
    if _yaml is not None:
        data = _yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    return _mini_yaml(text)


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
