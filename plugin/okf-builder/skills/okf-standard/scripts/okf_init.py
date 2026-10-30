#!/usr/bin/env python3
"""okf_init.py — Crea la estructura knowledge/ del perfil knowledge/1.0 (OKF v0.2).

Uso:
    python3 okf_init.py --root /ruta/al/repo --title "Mi proyecto" \
        --description "Una frase" --actor human:jisequilla [--repo-url URL] \
        [--dirs arquitectura,decisiones,...] [--force]

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
DEFAULT_DIRS = ["arquitectura", "decisiones", "dominio", "sistemas", "apis", "datos",
                "metricas", "computaciones", "runbooks", "playbooks", "politicas", "references"]
DIR_DESC = {
    "arquitectura": "Vistas y principios de arquitectura.",
    "decisiones": "Registro de decisiones de arquitectura (ADR).",
    "dominio": "Glosario y conceptos de negocio.",
    "sistemas": "Servicios, módulos y componentes desplegables.",
    "apis": "Contratos de API y su semántica.",
    "datos": "Datasets, tablas y esquemas.",
    "metricas": "Definiciones de métricas y KPIs.",
    "computaciones": "Computaciones sancionadas (Attested Computation).",
    "runbooks": "Procedimientos operativos y de incidentes.",
    "playbooks": "Procedimientos de equipo y negocio.",
    "politicas": "Normas, estándares y compliance.",
    "references": "Material externo espejado, skills de ejecución y attesters.",
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

    log.append(write(k / "proyecto.md", render(
        "proyecto.md", titulo=args.title, descripcion_una_frase=args.description,
        url_repo=args.repo_url, tags=args.tags, actor=args.actor, ahora=now), args.force))

    root_idx = ['---', f'okf_version: "{args.okf_version}"', 'okf_profile: "knowledge/1.0"', '---', '',
                '# Proyecto', '', f'* [{args.title}](proyecto.md) - {args.description}', '',
                '# Subdirectorios', '']
    for d in dirs:
        root_idx.append(f"* [{d}]({d}/index.md) - {DIR_DESC.get(d, f'Conceptos de {d}.')}")
    log.append(write(k / "index.md", "\n".join(root_idx) + "\n", args.force))

    log.append(write(k / "log.md", render("log.md", fecha=date.today().isoformat()), args.force))

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
