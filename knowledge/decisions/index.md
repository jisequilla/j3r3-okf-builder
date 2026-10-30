> Registro de decisiones de arquitectura (ADR).

# Architecture decisions

* [ADR-0001: Adoptar el Open Knowledge Format de Google como base del estándar](ADR-0001-adopt-google-okf.md) - El conocimiento de proyecto se representa como bundle OKF (markdown + frontmatter YAML) en lugar de un formato propio.
* [ADR-0002: Un bundle por repositorio en knowledge/](ADR-0002-knowledge-folder-per-repo.md) - Cada repo lleva su conocimiento en knowledge/ co-localizado con el código, no en un repo central.
* [ADR-0003: Directorios y tipos del perfil en español](ADR-0003-spanish-names.md) - Los directorios del perfil y los valores de type van en español, salvo references/ y Attested Computation que fija la spec. _(deprecated)_
* [ADR-0004: Soportar OKF v0.1 y v0.2 con v0.2 por defecto](ADR-0004-dual-support-v01-v02.md) - El perfil escribe v0.2, lee y valida v0.1, y migra en ambos sentidos sin mezclar formas en un bundle.
* [ADR-0005: generated obligatorio y verified solo por personas](ADR-0005-required-generated-human-verified.md) - El perfil exige generated en todo concepto y prohíbe que un agente escriba verified con actor human:.
* [ADR-0006: Scripts Python sin dependencias externas](ADR-0006-dependency-free-scripts.md) - Las herramientas (init, lint, index, migrate) son Python ≥ 3.9 sin pip; PyYAML se usa solo si está presente.
* [ADR-0007: Fuente única de skills y proyecciones por plataforma](ADR-0007-single-source-and-projections.md) - Los skills viven una sola vez en plugin/okf-builder/skills; cada plataforma recibe una proyección (symlink o paquete generado).
* [ADR-0008: El repo okf-builder documenta su propio conocimiento con OKF](ADR-0008-dogfooding.md) - Este repositorio aplica el perfil knowledge/1.0 a sí mismo; las decisiones del proyecto son ADRs en knowledge/decisions.
* [ADR-0009: Construir los cambios multi-etapa por capas y tickets delegados](ADR-0009-build-in-layers-and-tickets.md) - Los cambios que tocan varias capas del repo se dividen en tickets verificables que construyen agentes en worktrees aislados, y la sesión principal solo juzga, verifica y mergea. _(draft)_
* [ADR-0010: Inglés como idioma canónico del repo y perfil knowledge/2.0](ADR-0010-english-canonical-profile-2.md) - El vocabulario del perfil, el código, los skills y el conocimiento del repo pasan a inglés, con un glosario fijo; el cambio de vocabulario sube el perfil a knowledge/2.0. _(draft)_
