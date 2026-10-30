> Registro de decisiones de arquitectura (ADR).

# Decisiones de arquitectura

* [ADR-0001: Adoptar el Open Knowledge Format de Google como base del estándar](ADR-0001-adoptar-okf-de-google.md) - El conocimiento de proyecto se representa como bundle OKF (markdown + frontmatter YAML) en lugar de un formato propio.
* [ADR-0002: Un bundle por repositorio en knowledge/](ADR-0002-carpeta-knowledge-por-repo.md) - Cada repo lleva su conocimiento en knowledge/ co-localizado con el código, no en un repo central.
* [ADR-0003: Directorios y tipos del perfil en español](ADR-0003-nombres-en-espanol.md) - Los directorios del perfil y los valores de type van en español, salvo references/ y Attested Computation que fija la spec.
* [ADR-0004: Soportar OKF v0.1 y v0.2 con v0.2 por defecto](ADR-0004-soporte-dual-v01-v02.md) - El perfil escribe v0.2, lee y valida v0.1, y migra en ambos sentidos sin mezclar formas en un bundle.
* [ADR-0005: generated obligatorio y verified solo por personas](ADR-0005-generated-obligatorio-verified-humano.md) - El perfil exige generated en todo concepto y prohíbe que un agente escriba verified con actor human:.
* [ADR-0006: Scripts Python sin dependencias externas](ADR-0006-scripts-sin-dependencias.md) - Las herramientas (init, lint, index, migrate) son Python ≥ 3.9 sin pip; PyYAML se usa solo si está presente.
* [ADR-0007: Fuente única de skills y proyecciones por plataforma](ADR-0007-fuente-unica-y-proyecciones.md) - Los skills viven una sola vez en plugin/okf-builder/skills; cada plataforma recibe una proyección (symlink o paquete generado).
* [ADR-0008: El repo okf-builder documenta su propio conocimiento con OKF](ADR-0008-dogfooding.md) - Este repositorio aplica el perfil knowledge/1.0 a sí mismo; las decisiones del proyecto son ADRs en knowledge/decisiones.
