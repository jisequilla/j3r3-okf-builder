> Architecture decision records (ADR).

# Architecture decisions

* [ADR-0001: Adopt Google's Open Knowledge Format as the basis of the standard](ADR-0001-adopt-google-okf.md) - Project knowledge is represented as an OKF bundle (markdown + YAML frontmatter) instead of a format of our own.
* [ADR-0002: One bundle per repository in knowledge/](ADR-0002-knowledge-folder-per-repo.md) - Each repo carries its knowledge in knowledge/, co-located with the code, not in a central repo.
* [ADR-0003: Profile directories and types in Spanish](ADR-0003-spanish-names.md) - Profile directories and type values are in Spanish, except references/ and Attested Computation, which the spec fixes. _(deprecated)_
* [ADR-0004: Support OKF v0.1 and v0.2, with v0.2 as the default](ADR-0004-dual-support-v01-v02.md) - The profile writes v0.2, reads and validates v0.1, and migrates in both directions without mixing forms in a bundle.
* [ADR-0005: generated required and verified only by people](ADR-0005-required-generated-human-verified.md) - The profile requires generated on every concept and forbids an agent from writing verified with a human: actor.
* [ADR-0006: Python scripts without external dependencies](ADR-0006-dependency-free-scripts.md) - The tools (init, lint, index, migrate) are Python ≥ 3.9 without pip; PyYAML is used only if present.
* [ADR-0007: Single source of skills and per-platform projections](ADR-0007-single-source-and-projections.md) - Skills live only once in plugin/okf-builder/skills; each platform receives a projection (symlink or generated package).
* [ADR-0008: The okf-builder repo documents its own knowledge with OKF](ADR-0008-dogfooding.md) - This repository applies profile knowledge/1.0 to itself; the project's decisions are ADRs in knowledge/decisions.
* [ADR-0009: Build multi-stage changes in layers and delegated tickets](ADR-0009-build-in-layers-and-tickets.md) - Changes that touch several layers of the repo are split into verifiable tickets that agents build in isolated worktrees, and the main session only judges, verifies and merges. _(draft)_
* [ADR-0010: English as the repo's canonical language and profile knowledge/2.0](ADR-0010-english-canonical-profile-2.md) - The profile vocabulary, the code, the skills and the repo's knowledge move to English, with a fixed glossary; the vocabulary change bumps the profile to knowledge/2.0. _(draft)_
