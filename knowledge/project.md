---
type: Project
title: OKF Builder
description: Estándar OKF (perfil knowledge/2.0) y plugin okf-builder para gestionar conocimiento de proyectos con Claude, Copilot, M365 y Gemini
resource: https://github.com/jisequilla/j3r3-okf-builder
tags: [okf, conocimiento, plugin]
status: draft
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Propósito

Definir una estructura estándar de conocimiento por repositorio (`knowledge/`) basada en el Open Knowledge Format de Google, y entregar herramientas (skills + scripts) para crearla, mantenerla, validarla y consultarla desde cualquier agente de IA que el equipo use.

# Alcance

- Incluye: estándar (perfil), plantillas, scripts sin dependencias, skills Agent Skills, proyecciones para Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI y Microsoft 365 Copilot, soporte OKF v0.1 y v0.2.
- Excluye: servir o indexar bundles (eso lo hacen los consumidores: Knowledge Catalog, SharePoint, buscadores); ejecutar computaciones atestadas.

# Equipo y propiedad

| Rol | Persona / equipo | Contacto |
|---|---|---|
| Owner | human:jisequilla | jisequilla@gmail.com |

# Enlaces clave

| Recurso | URL |
|---|---|
| Repositorio | https://github.com/jisequilla/j3r3-okf-builder |
| Spec upstream | https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf |

# Mapa del conocimiento

* [Arquitectura](/architecture/index.md) — fuente única y proyecciones
* [Decisiones](/decisions/index.md) — ADRs del estándar y del plugin
* [Dominio](/domain/index.md) — glosario OKF
* [Sistemas](/systems/index.md) — plugin, scripts, exportadores
* [Runbooks](/runbooks/index.md) — release, exportación, actualización de la spec
* [Políticas](/policies/index.md) — reglas que todo agente debe cumplir en este repo
