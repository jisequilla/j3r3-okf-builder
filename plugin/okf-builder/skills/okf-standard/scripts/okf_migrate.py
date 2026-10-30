#!/usr/bin/env python3
"""okf_migrate.py — Migra un bundle OKF entre v0.1 y v0.2 (ambos sentidos).

Uso:
    python3 okf_migrate.py [bundle] --to 0.2 [--actor process:okf-migrate] [--dry-run] [--out DIR]
    python3 okf_migrate.py [bundle] --to 0.1 [--keep-extensions] [--dry-run] [--out DIR]

0.1 → 0.2 (sin pérdida):
  - timestamp            → generated: { by: <actor>, at: <timestamp> }
  - # Citations (cuerpo) → sources[] (id cit-n, resource, title) + notas al pie [^cit-n]
  - okf_version "0.2" en index.md raíz; entrada en log.md

0.2 → 0.1 (con pérdida salvo --keep-extensions):
  - generated.at         → timestamp
  - sources[]            → # Citations con [n] [title](resource); [^id] → [n]
  - verified, status, stale_after, usage_window, generated, sources se eliminan
    (con --keep-extensions se conservan como claves extra, legal en ambas specs)
  - okf_version "0.1" en index.md raíz; entrada en log.md

--out DIR escribe una copia migrada y deja intacto el bundle fuente (recomendado para 0.2→0.1).
Edita el texto del frontmatter por bloques de clave para preservar orden, comentarios y
claves desconocidas; nunca re-serializa YAML completo.
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
# Frontmatter como bloques de clave de primer nivel (preserva texto original)
# --------------------------------------------------------------------------
def fm_blocks(raw: str) -> list[tuple[str | None, list[str]]]:
    """[(clave|None para comentarios sueltos, líneas)] en orden."""
    blocks: list[tuple[str | None, list[str]]] = []
    for line in raw.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:", line)
        if m and not line.startswith((" ", "\t")):
            blocks.append((m.group(1), [line]))
        elif blocks and blocks[-1][0] is not None and (line.startswith((" ", "\t", "-")) or not line.strip()):
            blocks[-1][1].append(line)
        else:
            blocks.append((None, [line]))
    # recortar líneas en blanco finales de cada bloque
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
    """ISO 8601 con offset explícito; si es naive se asume UTC (y se avisa)."""
    s = ts.isoformat() if hasattr(ts, "isoformat") else str(ts).strip().strip("'\"")
    if re.search(r"(Z|[+-]\d{2}:\d{2})$", s):
        return s.replace("+00:00", "Z")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s + "T00:00:00Z"
    return s + "Z"


# --------------------------------------------------------------------------
# Citas v0.1 <-> sources v0.2
# --------------------------------------------------------------------------
CIT_ITEM_RE = re.compile(r"^\s*(?:\[(\d+)\]|[-*])\s+(.*\S)\s*$")
MDLINK_RE = re.compile(r"^\[([^\]]*)\]\(([^)\s]+)\)\s*(.*)$")


def parse_citations(body: str):
    """Devuelve (body_sin_seccion, [(n, title, url)])."""
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
            # "url - descripción" o texto libre
            parts = text.split(None, 1)
            url, title = (parts[0], parts[1].lstrip("-– ").strip()) if re.match(r"^[a-z]+:|^/|^\.", parts[0]) else ("", text)
            if not url:
                url, title = text, ""
        items.append((n, title, url))
    body = body[: m.start()] + body[m.end():]
    return body.rstrip() + "\n", items


def upgrade_citation_refs(body: str, ids: dict[int, str]) -> str:
    # [n] suelto (no seguido de '(' ni ':' y no precedido por '^') → [^cit-n]
    def rep(m):
        n = int(m.group(1))
        return f"[^{ids[n]}]" if n in ids else m.group(0)
    return re.sub(r"(?<![\^\[])\[(\d+)\](?![\(:])", rep, body)


def downgrade_footnotes(body: str, id_to_n: dict[str, int]) -> str:
    # eliminar definiciones [^id]: ...
    body = re.sub(r"^\[\^([^\]]+)\]:[^\n]*\n?", lambda m: "" if m.group(1) in id_to_n else m.group(0), body, flags=re.M)
    body = re.sub(r"\[\^([^\]]+)\]", lambda m: f"[{id_to_n[m.group(1)]}]" if m.group(1) in id_to_n else m.group(0), body)
    return body


# --------------------------------------------------------------------------
# Migración de un concepto
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
                notes.append(f"{rel}: timestamp sin offset; asumido UTC")
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
                # Citations generadas por un downgrade previo: restaurar notas al pie y quitar la sección
                ids = {n: str(by_res[url.lstrip("/")].get("id") or f"cit-{n}") for n, _, url in cits}
                body2 = upgrade_citation_refs(body2, ids)
                used = set(re.findall(r"\[\^([^\]]+)\]", body2))
                defs = [f"[^{ids[n]}]: {title or url}" for n, title, url in cits
                        if ids[n] in used and not re.search(rf"^\[\^{re.escape(ids[n])}\]:", body2, re.M)]
                if defs:
                    body2 = body2.rstrip() + "\n\n" + "\n".join(defs) + "\n"
                body = body2
            else:
                notes.append(f"{rel}: tiene sources y # Citations distintas; sección Citations conservada sin convertir")
    else:  # to 0.1
        gen = fm.get("generated")
        if isinstance(gen, dict) and gen.get("at") is not None and "timestamp" not in fm:
            i = get_block(blocks, "generated")
            ts_line = f"timestamp: {norm_ts(gen['at'])}"
            if keep_ext:
                blocks.insert(i, ("timestamp", [ts_line]))
            else:
                blocks[i] = ("timestamp", [ts_line])
                notes.append(f"{rel}: generated.by '{gen.get('by')}' descartado")
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
                    notes.append(f"{rel}: señales de credibilidad de sources descartadas")
        if not keep_ext:
            for k in DROP_ON_DOWNGRADE:
                i = get_block(blocks, k)
                if i >= 0:
                    del blocks[i]
                    notes.append(f"{rel}: '{k}' descartado")
        if fm.get("type") == "Attested Computation":
            notes.append(f"{rel}: type 'Attested Computation' pasa a tipo genérico en 0.1 (claves de computación conservadas)")

    return "---\n" + blocks_to_raw(blocks) + "\n---\n\n" + body.lstrip("\n")


def set_root_version(index_path: Path, to: str) -> None:
    text = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Índice\n"
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
    entry = f"* **Migración**: Bundle migrado a OKF v{to} ({n} conceptos) con okf-migrate."
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8")
        if f"## {today}" in text:
            text = text.replace(f"## {today}\n", f"## {today}\n{entry}\n", 1)
        else:
            m = re.search(r"^## ", text, re.M)
            text = (text[: m.start()] + f"## {today}\n{entry}\n\n" + text[m.start():]) if m else text.rstrip() + f"\n\n## {today}\n{entry}\n"
    else:
        text = f"# Historial del bundle\n\n## {today}\n{entry}\n"
    log_path.write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?")
    ap.add_argument("--to", required=True, choices=SUPPORTED_VERSIONS)
    ap.add_argument("--actor", default="process:okf-migrate", help="generated.by para conceptos sin autor (0.1→0.2)")
    ap.add_argument("--keep-extensions", action="store_true", help="0.2→0.1: conservar claves v0.2 como extensiones")
    ap.add_argument("--out", help="escribir copia migrada en este directorio (el origen no se toca)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="migrar aunque la versión detectada ya sea la destino")
    ap.add_argument("--file", action="append", default=[],
                    help="migrar solo este concepto (ruta relativa al bundle); repetible. No toca index/log")
    args = ap.parse_args(argv)

    src = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if src is None or not src.is_dir():
        print("ERROR: bundle no encontrado.", file=sys.stderr)
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
            print(f"{'(dry) ' if args.dry_run else ''}migrado {rel} → {args.to}")
        for n in notes:
            print("  nota:", n)
        return 0
    print(f"Origen: {src} · versión detectada {detected} ({origin}) → destino {args.to}")
    if detected == args.to and origin == "declared" and not args.force:
        print("Ya está en la versión destino; nada que hacer (usa --force para reescribir).")
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
            print(f"{'(dry) ' if args.dry_run else ''}migrado {doc.rel}")
            if not args.dry_run:
                (dst / doc.rel).write_text(new, encoding="utf-8")
    if not args.dry_run:
        set_root_version(dst / "index.md", args.to)
        append_log(dst / "log.md", args.to, changed)
    for n in notes:
        print("  nota:", n)
    print(f"\n{changed} conceptos migrados a OKF v{args.to}{' (dry-run)' if args.dry_run else ''} → {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
