#!/usr/bin/env python3
"""export_copilot.py — Genera el paquete OKF para GitHub Copilot a partir del plugin.

Copilot (VS Code agent mode, Copilot CLI y coding agent) descubre Agent Skills
(SKILL.md, estándar agentskills.io) en .github/skills/, .claude/skills/ o
.agents/skills/. Este exportador:

  1. Copia cada skill del plugin a <out>/.github/skills/<skill>/.
  2. Concreta la convención <skills> de los SKILL.md a la ruta del repo destino.
  3. Genera un custom agent .github/agents/okf.agent.md que orquesta los skills.
  4. Genera AGENTS.md (fragmento) con el inventario y la regla de consumo de knowledge/.

Uso:
    python3 tools/export_copilot.py [--out dist/copilot] [--skills-dir .github/skills] [--zip]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "okf-builder"

AGENT_MD = """---
name: okf
description: Gestor de conocimiento OKF (Open Knowledge Format) del repositorio. Úsalo para inicializar knowledge/, capturar ADRs/runbooks/sistemas, validar, regenerar índices, migrar entre OKF 0.1 y 0.2 y responder preguntas sobre el proyecto a partir de knowledge/.
tools: ["read", "edit", "search", "shell"]
---

Eres el agente OKF de este repositorio. El conocimiento del proyecto vive en `knowledge/`
como bundle OKF (markdown + frontmatter YAML). Trabaja siempre a través de los skills
`okf-*` de `{skills_dir}/`; son la fuente de verdad del estándar y contienen las
plantillas y los scripts.

Reglas:
1. Antes de responder sobre el proyecto, navega `knowledge/index.md` → índices de
   directorio → conceptos (skill okf-ask). Cita rutas y nivel de confianza.
2. Para crear o modificar conocimiento usa okf-capture: plantilla, `log.md`, índice y lint.
   Nunca añadas `verified` con `human:` sin confirmación explícita de la persona.
3. Antes de terminar cualquier cambio en `knowledge/`, ejecuta
   `python3 {skills_dir}/okf-standard/scripts/okf_lint.py knowledge` y corrige los ERROR.
4. Respeta la versión OKF del bundle (`okf_version` en `knowledge/index.md`); no mezcles
   formas 0.1 y 0.2. Para cambiar de versión usa okf-migrate con `--dry-run` primero.
5. Si no existe `knowledge/`, propone okf-init y espera confirmación.
"""

AGENTS_SNIPPET = """## Conocimiento del proyecto (OKF)

El conocimiento vive en `knowledge/` (Open Knowledge Format, markdown + frontmatter YAML).
Empieza siempre por `knowledge/index.md` y desciende por los `index.md` de cada directorio.

Skills disponibles en `{skills_dir}/` (estándar Agent Skills, también válidos para Claude Code):

| Skill | Uso |
|---|---|
| okf-standard | Estándar OKF v0.1/v0.2, perfil knowledge/1.0, plantillas y scripts |
| okf-init | Crear `knowledge/` |
| okf-capture | Añadir ADR, runbook, sistema, API, tabla, métrica, término, política |
| okf-lint | Validar conformidad (`python3 {skills_dir}/okf-standard/scripts/okf_lint.py knowledge`) |
| okf-index | Regenerar `index.md` |
| okf-ask | Responder preguntas citando conceptos y confianza |
| okf-migrate | Migrar entre OKF 0.1 y 0.2 |

Agente: `@okf` (`.github/agents/okf.agent.md`). Validación en CI: `okf_lint.py knowledge --strict`.
"""


RUTAS_RE = re.compile(r"^> \*\*Rutas\.\*\*.*$\n?", re.M)


def rewrite(text: str, skills_dir: str) -> str:
    text = RUTAS_RE.sub(f"> **Rutas.** Relativas a la raíz del repositorio; los skills `okf-*` están en `{skills_dir}/`.\n", text)
    # Los skills fuente usan la convención <skills>; aquí se concreta a la ruta del repo destino.
    return text.replace("<skills>/", f"{skills_dir}/").replace("${CLAUDE_PLUGIN_ROOT}/skills", skills_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist/copilot", help="directorio de salida (relativo al repo)")
    ap.add_argument("--skills-dir", default=".github/skills",
                    help=".github/skills (Copilot) | .agents/skills (neutro) | .claude/skills")
    ap.add_argument("--zip", action="store_true", help="además, empaquetar como okf-copilot-pack.zip")
    args = ap.parse_args(argv)

    out = (ROOT / args.out).resolve()
    skills_dir = args.skills_dir.strip("/")
    dst_skills = out / skills_dir
    if out.exists():
        shutil.rmtree(out)
    dst_skills.mkdir(parents=True)

    n = 0
    for skill in sorted((PLUGIN / "skills").iterdir()):
        if not (skill / "SKILL.md").exists():
            continue
        target = dst_skills / skill.name
        shutil.copytree(skill, target, ignore=shutil.ignore_patterns("__pycache__"))
        for md in target.rglob("*.md"):
            md.write_text(rewrite(md.read_text(encoding="utf-8"), skills_dir), encoding="utf-8")
        n += 1
    # licencia en el skill que incluye la spec de Google
    lic = dst_skills / "okf-standard" / "references" / "OKF-SPEC-LICENSE.md"
    if lic.exists():
        std = dst_skills / "okf-standard" / "SKILL.md"
        s = std.read_text(encoding="utf-8")
        if "license:" not in s.split("---")[1]:
            s = s.replace("\n---\n", "\nlicense: Apache-2.0 (specs de Google en references/); resto del skill según LICENSE del repo\n---\n", 1)
        std.write_text(s, encoding="utf-8")

    agents = out / ".github" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "okf.agent.md").write_text(AGENT_MD.format(skills_dir=skills_dir), encoding="utf-8")
    (out / "AGENTS.okf.md").write_text(AGENTS_SNIPPET.format(skills_dir=skills_dir), encoding="utf-8")
    (out / "README.md").write_text(
        f"""# OKF pack para GitHub Copilot

Copia el contenido de este directorio en la raíz de tu repositorio:

- `{skills_dir}/okf-*/` — Agent Skills (los descubre Copilot en VS Code, Copilot CLI y coding agent; también Claude Code y Gemini CLI si usas `.agents/skills`).
- `.github/agents/okf.agent.md` — custom agent `@okf` que orquesta los skills.
- `AGENTS.okf.md` — fragmento para pegar en tu `AGENTS.md` (o `.github/copilot-instructions.md`).

Los scripts (`okf_init/lint/index/migrate.py`) están en `{skills_dir}/okf-standard/scripts/` y no tienen dependencias
(Python ≥ 3.9). En Copilot, la ejecución de scripts pide confirmación salvo que añadas `allowed-tools` al SKILL.md.

Generado desde el plugin okf-builder con `tools/export_copilot.py`; no edites aquí, edita el plugin y vuelve a exportar.
""", encoding="utf-8")

    print(f"{n} skills exportados a {out} ({skills_dir})")
    if args.zip:
        zpath = out.parent / "okf-copilot-pack.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(out))
        print(f"→ {zpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
