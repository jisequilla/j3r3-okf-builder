#!/usr/bin/env python3
"""okf_lint.py — Valida un bundle OKF v0.2 y el perfil knowledge/1.0.

Uso:
    python3 okf_lint.py [ruta/al/bundle] [--json] [--strict] [--no-profile]

Salida: lista de hallazgos con nivel ERROR / WARN y código. Exit 1 si hay
errores (o avisos con --strict).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    ACTOR_RE,
    CITATIONS_RE,
    SUPPORTED_VERSIONS,
    V02_KEYS,
    detect_version,
    KEBAB_RE,
    VALID_STATUS,
    Doc,
    as_list,
    extract_links,
    find_bundle,
    is_iso,
    resolve_link,
    to_dt,
    walk_bundle,
)


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, code: str, path: str, msg: str) -> None:
        self.items.append({"level": level, "code": code, "path": path, "message": msg})

    def error(self, code, path, msg):
        self.add("ERROR", code, path, msg)

    def warn(self, code, path, msg):
        self.add("WARN", code, path, msg)

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "ERROR"]

    @property
    def warns(self):
        return [i for i in self.items if i["level"] == "WARN"]


def check_index(doc: Doc, bundle: Path, rep: Report, docs_by_path: dict, profile: bool = True) -> None:
    is_root = doc.path.parent.resolve() == bundle.resolve()
    if doc.has_fm_block and not is_root:
        rep.error("INDEX_FM", doc.rel, "index.md fuera de la raíz no debe llevar frontmatter (§8)")
    if is_root:
        fm = doc.frontmatter or {}
        if profile and "okf_version" not in fm:
            rep.error("PROFILE_OKF_VERSION", doc.rel, "index.md raíz debe declarar okf_version (perfil §7.4)")
    body = doc.body
    if not re.search(r"^#\s+\S", body, re.M):
        rep.error("INDEX_STRUCT", doc.rel, "index.md debe tener al menos una sección '# Título' (§8)")
    entries = re.findall(r"^\*\s+\[[^\]]+\]\(([^)]+)\)", body, re.M)
    if not entries and "_(vacío)_" not in body:
        rep.warn("INDEX_EMPTY", doc.rel, "index.md sin entradas '* [Título](ruta) - descripción'")
    for e in entries:
        if "#" in e or re.match(r"^[a-z]+:", e):
            continue
        target = resolve_link(bundle, doc, e)
        if target is None:
            continue
        if target.is_dir():
            continue
        if not target.exists():
            rep.warn("INDEX_BROKEN", doc.rel, f"entrada de índice apunta a inexistente: {e}")
    # Conceptos del directorio no listados
    listed = set()
    for e in entries:
        t = resolve_link(bundle, doc, e)
        if t is not None:
            listed.add(t.resolve())
            if t.is_dir():
                listed.add((t / "index.md").resolve())
    for p in sorted(doc.path.parent.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_file() and p.suffix == ".md" and p.name not in ("index.md", "log.md"):
            if p.resolve() not in listed:
                rep.warn("INDEX_STALE", doc.rel, f"concepto no listado en el índice: {p.name}")
        if p.is_dir() and (p / "index.md").exists():
            if (p / "index.md").resolve() not in listed and p.resolve() not in listed:
                rep.warn("INDEX_STALE", doc.rel, f"subdirectorio no listado en el índice: {p.name}/")


def check_log(doc: Doc, rep: Report) -> None:
    body = doc.body
    dates = re.findall(r"^##\s+(\S+)", body, re.M)
    if not dates:
        rep.error("LOG_STRUCT", doc.rel, "log.md debe agrupar entradas bajo '## YYYY-MM-DD' (§9)")
        return
    parsed = []
    for d in dates:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            rep.error("LOG_DATE", doc.rel, f"fecha de log no ISO 8601 YYYY-MM-DD: {d}")
        else:
            parsed.append(d)
    if parsed != sorted(parsed, reverse=True):
        rep.warn("LOG_ORDER", doc.rel, "las fechas del log deben ir de más reciente a más antigua")


def check_concept(doc: Doc, bundle: Path, rep: Report, profile: bool, now: datetime, version: str = "0.2") -> None:
    if not doc.has_fm_block:
        rep.error("NO_FRONTMATTER", doc.rel, "concepto sin bloque frontmatter YAML (§11.1)")
        return
    if doc.fm_error:
        rep.error("BAD_YAML", doc.rel, f"frontmatter YAML no parseable: {doc.fm_error}")
        return
    fm = doc.frontmatter or {}
    t = fm.get("type")
    if not t or not str(t).strip():
        rep.error("NO_TYPE", doc.rel, "frontmatter sin 'type' no vacío (§11.2)")
    if "description" not in fm or not fm.get("description"):
        rep.warn("NO_DESCRIPTION", doc.rel, "sin 'description' (recomendado; alimenta los index.md)")
    if "title" not in fm:
        rep.warn("NO_TITLE", doc.rel, "sin 'title' (recomendado)")

    status = fm.get("status")
    if status is not None and status not in VALID_STATUS:
        rep.error("BAD_STATUS", doc.rel, f"status '{status}' no es draft|stable|deprecated (§5.4)")

    has_citations = bool(CITATIONS_RE.search(doc.body))
    if version == "0.2":
        if "timestamp" in fm and "generated" not in fm:
            rep.warn("LEGACY_TIMESTAMP", doc.rel, "'timestamp' es v0.1; migrar a generated.at (§13.1)")
        if has_citations:
            rep.warn("LEGACY_CITATIONS", doc.rel, "'# Citations' es v0.1; migrar a 'sources' (§13.1)")
    else:  # 0.1
        v02 = sorted(V02_KEYS & set(fm))
        if v02:
            rep.warn("V02_FIELD_IN_V01", doc.rel, f"claves v0.2 en bundle 0.1 (se preservan, no se interpretan): {', '.join(v02)}")
        if str(t) == "Attested Computation":
            rep.warn("V02_FIELD_IN_V01", doc.rel, "type 'Attested Computation' es v0.2; en 0.1 es un tipo genérico")
        ts = fm.get("timestamp")
        if ts is None:
            if profile:
                rep.error("PROFILE_NO_TIMESTAMP", doc.rel, "perfil knowledge/1.0 en modo 0.1 exige 'timestamp'")
        elif not is_iso(ts):
            rep.warn("BAD_ISO", doc.rel, f"timestamp '{ts}' no es ISO 8601 con offset")
        if has_citations:
            m = re.search(r"^#\s+Citations\s*$(.*?)(?=^#\s|\Z)", doc.body, re.M | re.S)
            items = re.findall(r"^\s*(?:\[\d+\]|[-*])\s+\S", m.group(1), re.M) if m else []
            if not items:
                rep.warn("CITATIONS_EMPTY", doc.rel, "'# Citations' sin entradas '[n] ...' o '- ...' (v0.1 §8)")

    gen = fm.get("generated")
    if gen is not None:
        if not isinstance(gen, dict) or not gen.get("by"):
            rep.error("BAD_GENERATED", doc.rel, "'generated' requiere { by, at } con 'by' (§5.2)")
        else:
            if not ACTOR_RE.match(str(gen["by"])):
                rep.warn("BAD_ACTOR", doc.rel, f"generated.by '{gen['by']}' no sigue la convención de actores (§7)")
            if "at" in gen and not is_iso(gen["at"]):
                rep.warn("BAD_ISO", doc.rel, f"generated.at '{gen['at']}' no es ISO 8601 con offset")
    elif profile and version == "0.2":
        rep.error("PROFILE_NO_GENERATED", doc.rel, "perfil knowledge/1.0 exige 'generated: { by, at }'")

    for v in as_list(fm.get("verified")):
        if not isinstance(v, dict) or not v.get("by"):
            rep.error("BAD_VERIFIED", doc.rel, "cada entrada de 'verified' requiere { by, at } (§5.2)")
            continue
        if not ACTOR_RE.match(str(v["by"])):
            rep.warn("BAD_ACTOR", doc.rel, f"verified.by '{v['by']}' no sigue la convención de actores (§7)")
        if "at" in v and not is_iso(v["at"]):
            rep.warn("BAD_ISO", doc.rel, f"verified.at '{v['at']}' no es ISO 8601 con offset")

    sa = fm.get("stale_after")
    if sa is not None:
        dt = to_dt(sa)
        if dt is None:
            rep.warn("BAD_ISO", doc.rel, f"stale_after '{sa}' no es ISO 8601 con offset")
        elif now >= dt and status != "deprecated":
            rep.warn("STALE", doc.rel, f"contenido obsoleto desde {dt.isoformat()} (§5.5): revisar y renovar o deprecar")

    sources = fm.get("sources")
    ids = set()
    if sources is not None:
        if not isinstance(sources, list):
            rep.error("BAD_SOURCES", doc.rel, "'sources' debe ser una lista (§5.1)")
        else:
            for s in sources:
                if not isinstance(s, dict) or not s.get("resource"):
                    rep.error("BAD_SOURCES", doc.rel, "cada entrada de 'sources' requiere 'resource' (§5.1)")
                    continue
                if s.get("id"):
                    ids.add(str(s["id"]))
                if "last_modified" in s and not is_iso(s["last_modified"]):
                    rep.warn("BAD_ISO", doc.rel, f"sources[].last_modified '{s['last_modified']}' no es ISO 8601")
    for fn in set(re.findall(r"\[\^([^\]]+)\]", doc.body)):
        if fn not in ids:
            rep.warn("FOOTNOTE_NO_SOURCE", doc.rel, f"nota al pie [^{fn}] sin sources[].id correspondiente (§5.1)")

    if str(t) == "Attested Computation":
        if not fm.get("runtime"):
            rep.error("AC_NO_RUNTIME", doc.rel, "Attested Computation requiere 'runtime' (§10.2)")
        if not fm.get("computation"):
            m = re.search(r"^#\s+Computation\s*$(.*?)(?=^#\s|\Z)", doc.body, re.M | re.S)
            fences = len(re.findall(r"^```", m.group(1), re.M)) // 2 if m else 0
            indented = bool(m and re.search(r"^(    |\t)\S", m.group(1), re.M))
            if not m or (fences != 1 and not indented):
                rep.error("AC_NO_COMPUTATION", doc.rel,
                          "Attested Computation sin 'computation' ni un único bloque bajo '# Computation' (§10.3)")
        for p in as_list(fm.get("parameters")):
            if not isinstance(p, dict) or not p.get("name") or not p.get("type"):
                rep.error("AC_BAD_PARAM", doc.rel, "parameters[] requiere { name, type, required } (§10.2)")

    if profile and not KEBAB_RE.match(doc.path.name):
        rep.warn("NAME_KEBAB", doc.rel, "nombre de fichero no es kebab-case ASCII (perfil §2)")

    for link in extract_links(doc.body):
        target = resolve_link(bundle, doc, link)
        if target is None:
            continue
        try:
            target.relative_to(bundle.resolve())
        except ValueError:
            rep.warn("LINK_OUTSIDE", doc.rel, f"enlace sale del bundle: {link}")
            continue
        if not target.exists():
            rep.warn("BROKEN_LINK", doc.rel, f"enlace roto (tolerado por §6.1): {link}")


def lint(bundle: Path, profile: bool = True, version: str = "auto") -> tuple[Report, str, str]:
    rep = Report()
    now = datetime.now(timezone.utc)
    docs = walk_bundle(bundle)
    by_path = {d.path.resolve(): d for d in docs}

    detected, origin = detect_version(bundle, docs)
    if version == "auto":
        version = detected
    if origin == "mixed":
        rep.warn("MIXED_VERSIONS", "index.md", "conceptos con formas 0.1 y 0.2 mezcladas y sin okf_version: bundle a medio migrar (okf-migrate)")
    if origin == "declared" and detected != version:
        rep.warn("VERSION_MISMATCH", "index.md", f"index.md declara okf_version {detected} pero se valida como {version}")
    if origin != "declared" and profile:
        rep.warn("NO_OKF_VERSION", "index.md", f"index.md raíz sin okf_version; versión inferida: {version} ({origin})")

    if profile:
        if not (bundle / "index.md").exists():
            rep.error("PROFILE_NO_INDEX", "index.md", "falta knowledge/index.md (perfil §7.4)")
        if not (bundle / "log.md").exists():
            rep.error("PROFILE_NO_LOG", "log.md", "falta knowledge/log.md (perfil §7.4)")
        proj = bundle / "proyecto.md"
        if not proj.exists():
            rep.error("PROFILE_NO_PROJECT", "proyecto.md", "falta knowledge/proyecto.md con type: Proyecto (perfil §7.4)")
        else:
            d = by_path.get(proj.resolve())
            if d and d.frontmatter and d.frontmatter.get("type") != "Proyecto":
                rep.error("PROFILE_PROJECT_TYPE", "proyecto.md", "proyecto.md debe tener type: Proyecto")
        types = [d.frontmatter.get("type") for d in docs if d.frontmatter and not d.is_reserved]
        if types.count("Proyecto") > 1:
            rep.error("PROFILE_MANY_PROJECTS", "proyecto.md", "más de un concepto con type: Proyecto")

    for d in docs:
        if d.path.name == "index.md":
            check_index(d, bundle, rep, by_path, profile)
        elif d.path.name == "log.md":
            if d.has_fm_block and d.frontmatter and d.frontmatter.get("type") not in (None, "Log"):
                rep.warn("LOG_TYPE", d.rel, "log.md con frontmatter debería ser type: Log o no llevarlo")
            check_log(d, rep)
        else:
            check_concept(d, bundle, rep, profile, now, version)
    return rep, version, origin


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="ruta al bundle (por defecto busca knowledge/ hacia arriba)")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--strict", action="store_true", help="los avisos también provocan exit 1")
    ap.add_argument("--no-profile", action="store_true", help="validar solo la spec OKF, no el perfil knowledge/1.0")
    ap.add_argument("--okf-version", default="auto", choices=("auto", *SUPPORTED_VERSIONS),
                    help="versión de la spec contra la que validar (auto: okf_version del index raíz o heurística)")
    args = ap.parse_args(argv)

    bundle = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if bundle is None or not bundle.is_dir():
        print("ERROR: no se encontró el bundle (knowledge/index.md). Indica la ruta.", file=sys.stderr)
        return 2

    rep, version, origin = lint(bundle, profile=not args.no_profile, version=args.okf_version)
    n_docs = len([d for d in walk_bundle(bundle) if not d.is_reserved])
    if args.json:
        print(json.dumps({"bundle": str(bundle), "okf_version": version, "version_origin": origin, "concepts": n_docs, "errors": len(rep.errors),
                          "warnings": len(rep.warns), "findings": rep.items}, ensure_ascii=False, indent=2))
    else:
        for i in rep.items:
            print(f"{i['level']:5} {i['code']:22} {i['path']}: {i['message']}")
        verdict = "CONFORMANTE" if not rep.errors else "NO CONFORMANTE"
        print(f"\n{bundle}: OKF {version} ({origin}) · {n_docs} conceptos · {len(rep.errors)} errores · {len(rep.warns)} avisos → {verdict}")
    if rep.errors or (args.strict and rep.warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
