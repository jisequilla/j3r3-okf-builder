#!/usr/bin/env python3
"""okf_index.py — Regenera los index.md de un bundle OKF a partir del frontmatter.

Uso:
    python3 okf_index.py [ruta/al/bundle] [--check] [--dir SUBDIR]

- Agrupa conceptos por `type` dentro de cada directorio.
- Lista subdirectorios con la primera frase de su propio index.md o su nombre.
- Preserva en la raíz el frontmatter (okf_version, okf_profile) y cualquier
  sección cuyo encabezado empiece por "# Notas".
- --check: no escribe; exit 1 si algún index.md cambiaría.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import RESERVED, find_bundle, load_doc, split_frontmatter  # noqa: E402

DIR_DESCRIPTIONS = {
    "architecture": "Architecture views and principles.",
    "decisions": "Architecture decision records (ADR).",
    "domain": "Glossary and business concepts.",
    "systems": "Services, modules and deployable components.",
    "apis": "API contracts and their semantics.",
    "data": "Datasets, tables and schemas.",
    "metrics": "Metric and KPI definitions.",
    "computations": "Sanctioned computations (Attested Computation).",
    "runbooks": "Operational and incident procedures.",
    "playbooks": "Team and business procedures.",
    "policies": "Rules, standards and compliance.",
    "references": "Mirrored external material, execution skills and attesters.",
    "skills": "Execution instructions (executors) for computations.",
    "attesters": "Deterministic receipt verification code.",
}

# Orden de secciones (tipos) en el índice; el resto alfabético después.
TYPE_ORDER = [
    "Project", "Architecture View", "Architecture Decision", "Term", "Glossary",
    "System", "API", "Dataset", "Table", "Metric", "Attested Computation",
    "Runbook", "Playbook", "Policy", "Reference",
]


def plural_heading(t: str) -> str:
    table = {
        "Project": "Project",
        "Architecture View": "Architecture views",
        "Architecture Decision": "Architecture decisions",
        "Term": "Terms",
        "Glossary": "Glossary",
        "System": "Systems",
        "API": "APIs",
        "Dataset": "Datasets",
        "Table": "Tables",
        "Metric": "Metrics",
        "Attested Computation": "Attested computations",
        "Runbook": "Runbooks",
        "Playbook": "Playbooks",
        "Policy": "Policies",
        "Reference": "References",
    }
    return table.get(t, t)


def dir_description(d: Path) -> str:
    idx = d / "index.md"
    if idx.exists():
        _, body = split_frontmatter(idx.read_text(encoding="utf-8"))
        m = re.search(r"^>\s*(.+)$", body, re.M)  # blockquote descriptivo opcional
        if m:
            return m.group(1).strip()
    return DIR_DESCRIPTIONS.get(d.name, f"Conceptos de {d.name}.")


def existing_root_fm_and_notes(idx: Path) -> tuple[str, str]:
    if not idx.exists():
        return "", ""
    text = idx.read_text(encoding="utf-8")
    raw, body = split_frontmatter(text)
    fm = f"---\n{raw}\n---\n\n" if raw is not None else ""
    notes = ""
    m = re.search(r"^(#\s+Notas.*)", body, re.M | re.S)
    if m:
        notes = m.group(1).rstrip() + "\n"
    return fm, notes


def build_index(bundle: Path, d: Path) -> str:
    is_root = d.resolve() == bundle.resolve()
    concepts = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix == ".md" and p.name not in RESERVED:
            doc = load_doc(bundle, p)
            fm = doc.frontmatter or {}
            concepts.append((str(fm.get("type") or "Otros"), fm.get("title") or p.stem,
                             fm.get("description") or "", p.name, fm.get("status")))
    subdirs = [p for p in sorted(d.iterdir()) if p.is_dir() and not p.name.startswith(".")
               and any(q.suffix == ".md" for q in p.rglob("*.md"))]

    groups: dict[str, list] = {}
    for c in concepts:
        groups.setdefault(c[0], []).append(c)
    ordered = sorted(groups, key=lambda t: (TYPE_ORDER.index(t) if t in TYPE_ORDER else 99, t))

    out = []
    fm_prefix, notes = ("", "")
    if is_root:
        fm_prefix, notes = existing_root_fm_and_notes(d / "index.md")
        if not fm_prefix:
            fm_prefix = '---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\n---\n\n'
    else:
        _, notes = existing_root_fm_and_notes(d / "index.md")
        out.append(f"> {dir_description(d)}\n")

    for t in ordered:
        out.append(f"# {plural_heading(t)}\n")
        for _, title, desc, fname, status in groups[t]:
            tag = " _(deprecated)_" if status == "deprecated" else (" _(draft)_" if status == "draft" else "")
            line = f"* [{title}]({fname})"
            if desc:
                line += f" - {desc}"
            out.append(line + tag)
        out.append("")
    if subdirs:
        out.append("# Subdirectorios\n")
        for s in subdirs:
            out.append(f"* [{s.name}]({s.name}/index.md) - {dir_description(s)}")
        out.append("")
    if not ordered and not subdirs:
        out.append(f"# {d.name}\n")
        out.append("_(vacío)_\n")
    body = "\n".join(out).rstrip() + "\n"
    if notes:
        body += "\n" + notes
    return fm_prefix + body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dir", help="regenerar solo este subdirectorio (relativo al bundle)")
    args = ap.parse_args(argv)

    bundle = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if bundle is None:
        print("ERROR: no se encontró el bundle.", file=sys.stderr)
        return 2

    targets = [bundle / args.dir] if args.dir else [bundle, *[p for p in bundle.rglob("*") if p.is_dir() and not any(
        part.startswith(".") for part in p.relative_to(bundle).parts)]]
    changed = 0
    for d in targets:
        if not any(q.suffix == ".md" for q in d.rglob("*.md")) and d != bundle:
            continue
        new = build_index(bundle, d)
        idx = d / "index.md"
        old = idx.read_text(encoding="utf-8") if idx.exists() else None
        if old != new:
            changed += 1
            rel = idx.relative_to(bundle).as_posix()
            if args.check:
                print(f"DESACTUALIZADO {rel}")
            else:
                idx.write_text(new, encoding="utf-8")
                print(f"ESCRITO {rel}")
    if args.check:
        print(f"{changed} index.md desactualizados")
        return 1 if changed else 0
    print(f"{changed} index.md regenerados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
