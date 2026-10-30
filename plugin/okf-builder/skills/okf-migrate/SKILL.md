---
name: okf-migrate
description: Migra un bundle OKF entre v0.1 y v0.2 en ambos sentidos (timestamp↔generated, # Citations↔sources), detecta la versión de un bundle y exporta copias degradadas para consumidores antiguos. Usar cuando el usuario diga "migra a OKF 0.2", "convierte este bundle a 0.1", "qué versión de OKF es esto", "okf migrate", "exporta para un consumidor v0.1", o cuando okf-lint reporte LEGACY_*, V02_FIELD_IN_V01 o MIXED_VERSIONS.
---

# okf-migrate

> **Rutas.** `<skills>` es el directorio que contiene los skills `okf-*` (el padre de este skill): `${CLAUDE_PLUGIN_ROOT}/skills` en el plugin de Claude, `.claude/skills`, `.agents/skills`, `.github/skills` o `.gemini/skills` en un repo. Los scripts viven en `<skills>/okf-standard/scripts/` y las plantillas en `<skills>/okf-standard/templates/`.

## Detectar versión

```bash
python3 "<skills>/okf-standard/scripts/okf_lint.py" <bundle> --no-profile --json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['okf_version'],d['version_origin'])"
```
`declared` = `okf_version` en el `index.md` raíz; `heuristic` = inferida de los campos; `mixed` = formas 0.1 y 0.2 mezcladas; `default` = sin señales (se trata como 0.2).

## Migrar

Siempre primero `--dry-run`; mostrar al usuario la lista de conceptos afectados y las notas de pérdida antes de escribir.

```bash
# 0.1 → 0.2 (sin pérdida). --actor: a quién atribuir generated.by de los conceptos antiguos
python3 "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.2 --actor <actor> --dry-run
python3 "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.2 --actor <actor>

# 0.2 → 0.1: SIEMPRE a una copia (--out); el bundle fuente se queda en 0.2
python3 "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --keep-extensions --out <dir-export>

# Un solo concepto (p. ej. tras okf-capture en un bundle 0.1 con plantilla 0.2)
python3 "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file runbooks/x.md
```

Elección del `--actor` en 0.1→0.2: si se sabe quién escribió los conceptos (p. ej. el agente de Google), `reference_agent/<modelo>`; si fueron personas, `human:<id>` solo si el usuario lo confirma; en caso de duda `process:okf-migrate` (valor por defecto, honesto: no se sabe).

## Qué se pierde al bajar a 0.1 (sin `--keep-extensions`)

`generated.by`, `verified[]`, `status`, `stale_after`, `usage_window`, señales de `sources[]` (`author`, `usage_count`, `last_modified`). Con `--keep-extensions` se conservan como claves extra: ambas specs obligan a tolerarlas, pero un consumidor 0.1 no las interpreta. `Attested Computation` pasa a tipo genérico; sus claves de computación se conservan siempre.

## Después de migrar

1. `okf-lint` con la versión destino (`--okf-version 0.2|0.1`) hasta 0 errores.
2. `okf-index` si el cambio de `status` altera los índices (sufijos `_(draft)_`).
3. El script ya añade `okf_version` en el `index.md` raíz y una entrada `**Migración**` en `log.md`; revisar el texto.
4. Si quedan `LEGACY_CITATIONS` con la nota "sources y # Citations distintas", resolver a mano: la sección contiene citas que no están en `sources[]`.

## Tabla de mapeo

Ver `<skills>/okf-standard/references/OKF-COMPATIBILITY.md` §2 y §6.
