"""Utilidades compartidas para las herramientas OKF del plugin okf-builder.

Sin dependencias externas: si PyYAML está instalado se usa; si no, un parser
YAML reducido suficiente para frontmatter OKF (mapas, listas, flow mappings
`{ a: b }`, flow lists `[a, b]`, escalares, escalares multilínea y de bloque
`|`, `|-`, `>`, `>-`). Con OKF_NO_PYYAML=1 se fuerza el parser reducido.
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
# YAML reducido
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
            raise ValueError(f"comilla sin cerrar o texto tras la comilla de cierre: {t!r}")
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
                raise ValueError(f"escape \\u sin 4 dígitos hexadecimales: {s!r}")
            code = int(hexa, 16)
            if 0xD800 <= code <= 0xDFFF:
                raise ValueError(f"escape \\u{hexa} (surrogate) no soportado: {s!r}")
            out.append(chr(code))
            i += 6
            continue
        raise ValueError(f"escape \\{esc} no soportado en comillas dobles: {s!r}")
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


def _check_line(line: str) -> None:
    # todo inicio de línea fuera del cuerpo de un escalar de bloque
    if "\t" in line[: _indent_of(line)]:
        raise ValueError(f"tab en la indentación no soportado: {line!r}")
    _check_start(line, line, inline=False)


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
    "{": "mapa en flujo { }",
    "[": "lista en flujo [ ]",
    "&": "anclas (&)",
    "*": "alias (*)",
    "!": "tags (!)",
    "?": "claves complejas (?)",
    "%": "directivas (%)",
    "@": "carácter reservado @",
    "`": "carácter reservado `",
    "|": "escalar de bloque |",
    ">": "escalar de bloque >",
}


def _check_start(t: str, line: str, inline: bool) -> None:
    # la regla del YAML reducido: un indicador solo se admite como valor en la
    # misma línea que su clave o guion, y solo { }, [ ] y |, |-, >, >-
    t = t.strip()
    c = t[:1]
    if c not in _INDICATORS:
        return
    if inline and (c in "{[" or t in _BLOCK_HEADERS):
        return
    if not inline and c in "{[|>":
        raise ValueError(
            f"{_INDICATORS[c]} solo se admite en la misma línea que su clave o guion: {line!r}"
        )
    if c in "|>":
        raise ValueError(f"{_INDICATORS[c]} no soportado (solo |, |-, >, >-): {line!r}")
    raise ValueError(f"{_INDICATORS[c]} no soportado: {line!r}")


def _mini_yaml(text: str) -> dict:
    """YAML reducido. Solo admite: mapas y listas de bloque (incluida "- clave: v"),
    escalares planos y entre comillas (de una línea o continuados en líneas más
    indentadas), escalares de bloque |, |-, >, >- y colecciones en flujo { } y [ ]
    que abren en la misma línea que su clave o guion. Todo lo demás es ValueError."""
    raw = text.splitlines()
    for r in raw:
        if r.rstrip() in ("---", "..."):
            raise ValueError(f"multidocumento no soportado: {r!r}")
    # líneas significativas (sin comentarios ni vacías) y su posición en `raw`
    lines: list[str] = []
    pos: list[int] = []
    commented: set[int] = set()
    # líneas vacías o de solo comentario con tab en la indentación: error salvo
    # que queden dentro de un escalar entre comillas o de bloque (`in_scalar`)
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
        # | |- > >- se leen de `raw` para conservar '#' y líneas vacías
        # la indentación del cuerpo se cuenta solo en espacios
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
                    raise ValueError(f"tab en una línea de solo espacios de un escalar de bloque: {r!r}")
            return "", first_line_from(end)
        # como PyYAML: una línea más larga que la indentación del cuerpo es texto
        # (aunque sean solo espacios); las demás líneas vacías son saltos
        leading, segs, last = 0, [], start
        for i in range(start, end):
            r = raw[i]
            spaces = len(r) - len(r.lstrip(" "))
            if not r.strip() and spaces < body_indent and r[spaces:]:
                raise ValueError(f"tab en la indentación de un escalar de bloque no soportado: {r!r}")
            if len(r) > body_indent:
                if not segs and not r.strip():
                    raise ValueError(
                        f"línea inicial de solo espacios más indentada que el escalar de bloque: {raw[pos[idx]]!r}"
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
        # un escalar entre comillas que sigue en otras líneas se lee de `raw`:
        # dentro de las comillas '#' es texto y no un comentario
        q, text, end, blanks = t[0], t, pos[idx] + 1, 0
        while True:
            close = _closing_quote(text, q)
            if close is not None:
                rest = text[close + 1 :]
                if rest.strip() and not (rest[:1] in " \t" and rest.strip().startswith("#")):
                    raise ValueError(f"texto tras la comilla de cierre: {raw[end - 1]!r}")
                in_scalar.update(range(pos[idx] + 1, end))
                return _scalar(text[: close + 1]), first_line_from(end)
            if end >= len(raw) or (raw[end].strip() and _indent_of(raw[end]) <= indent):
                raise ValueError(f"comilla sin cerrar: {raw[pos[idx]]!r}")
            r = raw[end]
            end += 1
            if not r.strip():
                blanks += 1
                continue
            _check_line(r)
            if q == '"' and (len(text) - len(text.rstrip("\\"))) % 2:
                raise ValueError(f"salto de línea escapado (\\ al final de línea) no soportado: {raw[pos[idx]]!r}")
            text +=("\n" * blanks if blanks else " ") + r.strip()
            blanks = 0

    def plain_scalar(idx: int, indent: int, v: str):
        # un escalar que sigue en líneas más indentadas se une con un espacio
        t = v.strip()
        if t[:1] in ('"', "'"):
            return quoted_scalar(idx, indent, t)
        closed = len(t) > 1 and t[0] in _CLOSERS and t[-1] == _CLOSERS[t[0]]
        parts, nxt = [t], idx + 1
        if not closed and t[:1] == "{" and nxt < len(lines) and _indent_of(lines[nxt]) > indent:
            raise ValueError(f"mapa en flujo {{ }} multilínea no soportado: {lines[idx]!r}")
        while not closed and nxt < len(lines) and _indent_of(lines[nxt]) > indent:
            _check_line(lines[nxt])
            c = lines[nxt].strip()
            if ": " in c or c.endswith(":"):
                raise ValueError(f"indentación inesperada: {lines[nxt]!r}")
            gap = raw[pos[nxt - 1] + 1 : pos[nxt]]
            if (nxt - 1) in commented or any(g.strip() for g in gap):
                raise ValueError(f"comentario dentro de un escalar multilínea: {lines[nxt]!r}")
            parts.append("\n" * len(gap) if gap else " ")
            parts.append(c)
            nxt += 1
        if len(parts) == 1:
            return _scalar(t), nxt
        joined = "".join(parts)
        if t[0] in _CLOSERS and not joined.endswith(_CLOSERS[t[0]]):
            raise ValueError(f"'{t[0]}' sin cerrar: {lines[idx]!r}")
        return (_scalar(joined) if t[0] in _CLOSERS else joined), nxt

    def value(idx: int, indent: int, v: str):
        _check_start(v, lines[idx], inline=True)
        if v.strip() in _BLOCK_HEADERS:
            return block_scalar(idx, indent, v.strip())
        return plain_scalar(idx, indent, v)

    def parse_block(idx: int, indent: int):
        # devuelve (valor, siguiente_idx)
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
                raise ValueError(f"indentación inesperada: {line!r}")
            if ":" not in line:
                raise ValueError(f"línea sin ':' en mapa: {line!r}")
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
            if ":" in rest and not rest.lstrip().startswith(("{", "[", '"', "'")):
                # mapa inline que empieza en la línea del guion
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
            raise ValueError(f"tab en la indentación de una línea vacía o de comentario no soportado: {raw[i]!r}")
    return val if isinstance(val, dict) else {}


def parse_yaml(text: str) -> dict:
    if _yaml is not None:
        data = _yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    return _mini_yaml(text)


# --------------------------------------------------------------------------
# Documentos
# --------------------------------------------------------------------------
@dataclass
class Doc:
    path: Path
    rel: str  # ruta relativa al bundle, con /
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
    """Devuelve la ruta en disco de un enlace interno, o None si es externo."""
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
    """(n_conceptos con señales 0.2, n_conceptos con señales 0.1)."""
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
    """Devuelve (version, origen) con origen en {declared, heuristic, default, mixed}."""
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
    """Busca knowledge/ hacia arriba desde start (o cwd)."""
    p = (start or Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "knowledge" / "index.md").exists():
            return cand / "knowledge"
        if cand.name == "knowledge" and (cand / "index.md").exists():
            return cand
    return None
