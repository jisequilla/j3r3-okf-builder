#!/usr/bin/env python3
"""okf_init.py — Crea la estructura knowledge/ del perfil knowledge/2.0 (OKF v0.2).

Uso:
    python3 okf_init.py --root /ruta/al/repo --title "Mi proyecto" \
        --description "Una frase" --actor human:jisequilla [--repo-url URL] \
        [--dirs architecture,decisions,...] [--force]

No sobreescribe ficheros existentes salvo --force. Idempotente.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import now_iso  # noqa: E402

_HERE = Path(__file__).resolve().parent
TEMPLATES = _HERE.parent / "templates"   # okf-standard/scripts/ → okf-standard/templates/
DEFAULT_DIRS = ["architecture", "decisions", "domain", "systems", "apis", "data",
                "metrics", "computations", "runbooks", "playbooks", "policies", "references"]
DIR_DESC = {
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
}


def render(name: str, **vars) -> str:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def write(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"omitido (existe) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"creado {path}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="raíz del repositorio")
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", required=True)
    ap.add_argument("--actor", required=True, help="human:<id> | process:<id> | <agente>/<version>")
    ap.add_argument("--repo-url", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--dirs", default=",".join(DEFAULT_DIRS))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--okf-version", default="0.2", choices=("0.1", "0.2"),
                    help="versión OKF del bundle (0.1 solo para interoperar con consumidores antiguos)")
    args = ap.parse_args(argv)

    k = Path(args.root).resolve() / "knowledge"
    dirs = [d.strip() for d in args.dirs.split(",") if d.strip()]
    now = now_iso()
    log = []

    log.append(write(k / "project.md", render(
        "project.md", title=args.title, one_sentence_description=args.description,
        repo_url=args.repo_url, tags=args.tags, actor=args.actor, now=now), args.force))

    root_idx = ['---', f'okf_version: "{args.okf_version}"', 'okf_profile: "knowledge/2.0"', '---', '',
                '# Project', '', f'* [{args.title}](project.md) - {args.description}', '',
                '# Subdirectorios', '']
    for d in dirs:
        root_idx.append(f"* [{d}]({d}/index.md) - {DIR_DESC.get(d, f'Conceptos de {d}.')}")
    log.append(write(k / "index.md", "\n".join(root_idx) + "\n", args.force))

    log.append(write(k / "log.md", render("log.md", date=date.today().isoformat()), args.force))

    for d in dirs:
        desc = DIR_DESC.get(d, f"Conceptos de {d}.")
        log.append(write(k / d / "index.md", f"# {d}\n\n> {desc}\n\n_(vacío)_\n", args.force))
        if d == "references":
            for sub in ("skills", "attesters"):
                log.append(write(k / d / sub / "index.md",
                                 f"# {sub}\n\n> {DIR_DESC.get(sub, '')}\n\n_(vacío)_\n", args.force))
    print("\n".join(log))
    # Normalizar índices con el mismo generador que okf-index
    from okf_index import main as index_main  # noqa: E402
    if args.okf_version == "0.1":
        from okf_migrate import main as migrate_main  # noqa: E402
        migrate_main([str(k), "--to", "0.1", "--force"])
    index_main([str(k)])
    print(f"\nBundle inicializado en {k} (OKF v{args.okf_version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
