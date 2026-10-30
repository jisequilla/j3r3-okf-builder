#!/usr/bin/env python3
"""export_m365.py — Empaqueta los skills OKF para Microsoft 365 Copilot.

Genera dos salidas a partir de plugin/okf-builder/:

  dist/m365/okf-builder-m365.zip          Plugin de M365 Copilot Cowork (manifest.json v1.28
                                          + skills/ + iconos). Se sube en M365 admin center >
                                          Manage apps > Upload custom app, o con
                                          `atk install --file-path ... --scope Personal`.
  dist/m365/skills/okf-<skill>.zip        Un zip por skill (SKILL.md en la raíz) para
                                          "Upload a skill" en Copilot Studio / Agent Builder.

Diferencias respecto al plugin de Claude que resuelve este exportador:
  - ${CLAUDE_PLUGIN_ROOT} no existe: cada skill debe ser autocontenido. Se copian en cada
    skill los scripts y plantillas que usa y se reescriben las rutas a relativas al skill.
  - Límite M365: ≤20 ficheros companion por skill, ≤5 MB/fichero, sin ficheros ocultos.
  - name del SKILL.md == nombre de carpeta (regla ASKILL-P006).

Uso:
    python3 tools/export_m365.py [--out dist/m365] [--developer "Nombre"] [--website URL]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "okf-builder"
SCRIPTS = PLUGIN / "skills" / "okf-standard" / "scripts"
PLUGIN_JSON = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

# Qué scripts/plantillas necesita cada skill (para ser autocontenido)
NEEDS = {
    "okf-standard": {"scripts": [], "templates": True},
    "okf-init":     {"scripts": ["okf_init.py", "okf_common.py", "okf_index.py", "okf_migrate.py"], "templates": True},
    "okf-capture":  {"scripts": ["okf_index.py", "okf_lint.py", "okf_migrate.py", "okf_common.py"], "templates": True},
    "okf-lint":     {"scripts": ["okf_lint.py", "okf_common.py"], "templates": False},
    "okf-index":    {"scripts": ["okf_index.py", "okf_common.py"], "templates": False},
    "okf-migrate":  {"scripts": ["okf_migrate.py", "okf_common.py", "okf_lint.py"], "templates": False},
    "okf-ask":      {"scripts": ["okf_lint.py", "okf_common.py"], "templates": False},
}
MAX_COMPANIONS = 20


RUTAS_RE = re.compile(r"^> \*\*Rutas\.\*\*.*$\n?", re.M)


def rewrite(text: str, skill: str) -> str:
    text = RUTAS_RE.sub("> **Rutas.** Este skill es autocontenido: scripts en `scripts/` y plantillas en `templates/` de su propio directorio base.\n"
                        if NEEDS[skill]["templates"] or NEEDS[skill]["scripts"] else "", text)
    # Cada skill M365 es autocontenido: <skills>/okf-standard/scripts → scripts/ del propio skill
    text = text.replace("<skills>/okf-standard/scripts/", "scripts/")
    if NEEDS[skill]["templates"]:
        text = text.replace("<skills>/okf-standard/templates/", "templates/")
    else:
        text = text.replace("<skills>/okf-standard/templates/", "(plantillas: skill okf-standard) templates/")
    text = text.replace("<skills>/okf-standard/references/", "(skill okf-standard) references/")
    text = text.replace("<skills>/", "(skill) ")
    text = text.replace("${CLAUDE_PLUGIN_ROOT}/skills", "(skills)")
    return text


M365_NOTE = """

## Nota de entorno (Microsoft 365 Copilot)

Este skill se ejecuta en Microsoft 365 Copilot, no en un terminal sobre el repositorio. El bundle
`knowledge/` llega como carpeta de OneDrive/SharePoint sincronizada desde el repo (o como archivos
adjuntos). Pide la ruta o la carpeta al usuario si no es evidente. Los scripts `scripts/*.py` se
ejecutan desde el directorio base de este skill con `python3` y reciben la ruta del bundle como
argumento; si el entorno no permite ejecutar scripts, aplica las mismas reglas manualmente
leyendo `references/` y las plantillas, y dilo explícitamente.
"""


def ensure_frontmatter(text: str, skill: str, author: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit(f"{skill}: SKILL.md sin frontmatter")
    fm = m.group(1)
    if not re.search(rf"^name:\s*{re.escape(skill)}\s*$", fm, re.M):
        fm = re.sub(r"^name:.*$", f"name: {skill}", fm, flags=re.M)
    if "license:" not in fm:
        fm += "\nlicense: Apache-2.0"
    if "metadata:" not in fm:
        fm += f'\nmetadata:\n  author: {author}\n  version: "{PLUGIN_JSON["version"]}"'
    return f"---\n{fm}\n---\n" + text[m.end():]


def build_skill(skill_src: Path, dst: Path, author: str) -> int:
    skill = skill_src.name
    shutil.copytree(skill_src, dst, ignore=shutil.ignore_patterns("__pycache__", ".*"))
    if skill == "okf-standard" and (dst / "scripts").exists():
        shutil.rmtree(dst / "scripts")  # límite de 20 companions; los scripts van en los skills que los usan
    need = NEEDS[skill]
    if need["scripts"]:
        (dst / "scripts").mkdir(exist_ok=True)
        for s in need["scripts"]:
            shutil.copy2(SCRIPTS / s, dst / "scripts" / s)
    if need["templates"] and skill != "okf-standard":
        shutil.copytree(PLUGIN / "skills" / "okf-standard" / "templates", dst / "templates")
    for md in dst.rglob("*.md"):
        md.write_text(rewrite(md.read_text(encoding="utf-8"), skill), encoding="utf-8")
    sk = dst / "SKILL.md"
    sk.write_text(ensure_frontmatter(sk.read_text(encoding="utf-8"), skill, author).rstrip() + M365_NOTE, encoding="utf-8")
    companions = [p for p in dst.rglob("*") if p.is_file() and p.name != "SKILL.md"]
    if len(companions) > MAX_COMPANIONS:
        raise SystemExit(f"{skill}: {len(companions)} ficheros companion > {MAX_COMPANIONS}")
    for p in companions:
        if p.stat().st_size > 5 * 1024 * 1024 or p.name.startswith("."):
            raise SystemExit(f"{skill}: fichero no válido para M365: {p}")
    return len(companions)


def make_icons(out: Path) -> None:
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:  # noqa: BLE001
        src = PLUGIN / ".claude-plugin" / "icon.png"
        shutil.copy2(src, out / "color.png")
        shutil.copy2(src, out / "outline.png")
        print("aviso: PIL no disponible; iconos sin redimensionar (192x192 / 32x32 requeridos)")
        return
    img = Image.open(PLUGIN / ".claude-plugin" / "icon.png").convert("RGBA")
    img.resize((192, 192)).save(out / "color.png")
    o = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    for i in range(3):
        d.rounded_rectangle([5 + i * 3, 5 + i * 3, 22 + i * 3, 22 + i * 3], radius=3, outline=(255, 255, 255, 255), width=2)
    o.save(out / "outline.png")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist/m365")
    ap.add_argument("--developer", default=PLUGIN_JSON.get("author", {}).get("name", "okf-builder"))
    ap.add_argument("--website", default="https://github.com/jisequilla/j3r3-okf-builder")
    args = ap.parse_args(argv)

    out = (ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    pkg = out / "package"
    (pkg / "skills").mkdir(parents=True)
    (out / "skills").mkdir()

    skills = []
    for skill_src in sorted((PLUGIN / "skills").iterdir()):
        if not (skill_src / "SKILL.md").exists():
            continue
        n = build_skill(skill_src, pkg / "skills" / skill_src.name, args.developer)
        skills.append(skill_src.name)
        print(f"skill {skill_src.name}: {n} companions")
        # zip individual para Copilot Studio / Agent Builder (SKILL.md en la raíz del zip)
        zp = out / "skills" / f"{skill_src.name}.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted((pkg / "skills" / skill_src.name).rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(pkg / "skills" / skill_src.name))

    make_icons(pkg)
    manifest = {
        "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.28/MicrosoftTeams.schema.json",
        "manifestVersion": "1.28",
        "version": PLUGIN_JSON["version"],
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, args.website + "#okf-builder")),
        "developer": {
            "name": args.developer,
            "websiteUrl": args.website,
            "privacyUrl": args.website + "#privacy",
            "termsOfUseUrl": args.website + "#terms",
        },
        "name": {"short": "OKF Builder", "full": "OKF Builder — conocimiento de proyecto en Open Knowledge Format"},
        "description": {
            "short": "Gestiona knowledge/ en formato OKF: scaffold, captura, validación, consulta",
            "full": PLUGIN_JSON["description"],
        },
        "icons": {"color": "color.png", "outline": "outline.png"},
        "accentColor": "#1F2A44",
        "agentSkills": [{"folder": f"./skills/{s}"} for s in skills],
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    zp = out / "okf-builder-m365.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pkg.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(pkg))
    (out / "README.md").write_text(f"""# OKF para Microsoft 365 Copilot

## A) Plugin de M365 Copilot Cowork — `okf-builder-m365.zip`
Paquete M365 (manifest v1.28 + {len(skills)} Agent Skills). Requiere Microsoft 365 Copilot y, hoy, el programa Frontier para Cowork.
- Tenant (admin): M365 admin center → Manage apps → Upload custom app → Add agent → subir el zip. Aparece en Cowork → Sources & Skills → Plugins.
- Personal (sin admin): `npm i -g @microsoft/m365agentstoolkit-cli && atk auth login && atk install --file-path okf-builder-m365.zip --scope Personal`.
- Validación opcional: `wiqd plugin validate` (CLI preview de Microsoft).

## B) Skills sueltos — `skills/okf-*.zip`
Para Copilot Studio (nueva experiencia de agentes) o Agent Builder: Build → Skills → Upload a skill → arrastrar cada zip. Subir al menos `okf-standard`, `okf-ask` y `okf-capture`.

## Conocimiento
M365 Copilot no lee el repositorio git. Sincroniza la carpeta `knowledge/` a SharePoint/OneDrive (OneDrive sync del clon,
o un job de CI que publique `knowledge/` en una biblioteca de documentos) y añádela como fuente de conocimiento del agente.
OKF es markdown plano: se indexa tal cual. El repo sigue siendo la fuente de verdad; en M365 se lee y se proponen cambios
que vuelven al repo por PR (o se editan en la carpeta sincronizada si se acepta ese flujo).

Generado con `tools/export_m365.py`; no editar aquí.
""", encoding="utf-8")
    print(f"→ {zp}\n→ {out / 'skills'}/*.zip\n{len(skills)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
