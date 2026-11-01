# Bundle history

## 2026-11-01
* **Creation**: [ADR-0018](/decisions/ADR-0018-three-layers-fragments-base-projections.md): a bundle has three layers, `fragments/`, `base/` and `projections/`, in profile knowledge/3.0; distilled from the [real-bundles fragment](/fragments/2026-11-01-real-bundles-review.md), approved by human:jisequilla.
* **Creation**: [ADR-0019](/decisions/ADR-0019-knowledge-projections.md): knowledge projections with a `projection.yaml`, a dependency rule and drift by content hash; the skills' per-platform outputs become platform packages; approved by human:jisequilla.
* **Update**: [Projection](/domain/projection.md) now means a knowledge projection; the old meaning moves to the new term [Platform package](/domain/platform-package.md).
* **Creation**: fragment [What eleven real knowledge bundles teach](/fragments/2026-11-01-real-bundles-review.md): three layers, projections and a taxonomy per domain declared in each `index.md`, pending distillation.
* **Update**: okf-builder 0.5.0 released: the Claude knowledge-architect agent preloads all 10 skills, and the M365 agent's skills and conversation starters come from `tools/m365-agent.json` (ADR-0017).
* **Creation**: [ADR-0017](/decisions/ADR-0017-agent-skills-per-platform.md): the Claude knowledge-architect agent preloads all 10 skills, and `tools/m365-agent.json` picks the at most 8 the M365 agent carries; [Exporters](/systems/exporters.md), the [okf-builder plugin](/systems/plugin-okf-builder.md) and the [Knowledge architect](/roles/knowledge-architect.md) profile say so.
* **Deprecation**: [ADR-0013](/decisions/ADR-0013-agent-projections.md), superseded by ADR-0017.
* **Update**: okf-builder 0.4.1 released: okf-distill confirmations footnote an existing sentence and update `generated`, and distillation uses only the standard log labels.
* **Update**: [Publish a plugin version](/runbooks/release-version.md): the M365 agent package is attached to each release; okf-builder 0.4.0 released.
* **Update**: [Exporters](/systems/exporters.md): each M365 skill's Paths note, environment note and the okf-standard inventory name only what that skill ships, and the build checks it.
* **Update**: [okf-builder plugin](/systems/plugin-okf-builder.md), [Exporters](/systems/exporters.md) and the [Knowledge architect](/roles/knowledge-architect.md) profile: the plugin ships the knowledge-architect agent, and `make m365` generates it as a separate M365 declarative agent package.
* **Update**: [okf-builder plugin](/systems/plugin-okf-builder.md), [OKF scripts](/systems/scripts-okf.md) and [Exporters](/systems/exporters.md), plus the READMEs: the plugin has 10 skills with `okf-fragment`, `okf-distill` and `okf-review`, and the M365 exporter gives each skill only the templates it uses.
* **Update**: [Exporters](/systems/exporters.md) and [Export and deliver projections](/runbooks/export-projections.md): the M365 okf-standard keeps only its references, its templates ship in okf-capture, and `make test` runs the M365 exporter.
* **Creation**: [ADR-0016](/decisions/ADR-0016-refutation-as-a-distillation-kind.md): distillation adds refutation, which deprecates an outdated concept and links its replacement without opening a conflict; the standard's distillation and conflict rows say so.
* **Deprecation**: [ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md), superseded by ADR-0016.
* **Creation**: [Knowledge architect](/roles/knowledge-architect.md) role profile in the new `roles/` directory: it links the human-verified KDD role and fixes the agent's 8 skills, what it hands to a person and the fragment contract with the functional architect.

## 2026-10-31
* **Update**: [Export and deliver projections](/runbooks/export-projections.md) and the [projections view](/architecture/single-source-projections.md): M365 Copilot reads the bundle through the GitHub connector or from a SharePoint source (ADR-0014); the claim that SharePoint indexes `.md` as is is gone.
* **Creation**: fragment [Review of the KDD profiles bundle](/fragments/2026-10-31-kdd-bundle-review.md), distilled into ADR-0015 and the conflict log.
* **Creation**: [ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md): fragments follow the KDD bundle format plus `participants`, one conflict register per bundle, and `okf-fragment`, `okf-distill` and `okf-review` as separate skills.
* **Deprecation**: [ADR-0012](/decisions/ADR-0012-knowledge-fragments-and-distillation.md), superseded by ADR-0015.
* **Conflict**: C-001 to C-003 in the [conflict log](/conflict-log.md), opened and resolved by human:jisequilla.
* **Creation**: [ADR-0012](/decisions/ADR-0012-knowledge-fragments-and-distillation.md): knowledge fragments are captured as they happened and distilled into the bundle, with conflicts resolved by a person.
* **Creation**: [ADR-0013](/decisions/ADR-0013-agent-projections.md): one knowledge-architect agent for Claude and Microsoft 365 Copilot.
* **Creation**: [ADR-0014](/decisions/ADR-0014-knowledge-repository-storage.md): a knowledge repository has one source, Git or SharePoint; other tools read it.
* **Update**: [Publish a plugin version](/runbooks/release-version.md): a GitHub Release with the built files is part of each release; okf-builder 0.3.0 released.
* **Update**: [OKF scripts](/systems/scripts-okf.md) and the [project page](/project.md): the scripts run with uv (PEP 723), the reduced YAML parser is gone and each script carries its own tests (ADR-0011).
* **Creation**: [ADR-0011](/decisions/ADR-0011-uv-pep723-scripts.md): scripts run with uv and declare PyYAML inline (PEP 723); the reduced YAML parser is removed.
* **Deprecation**: [ADR-0006](/decisions/ADR-0006-dependency-free-scripts.md), superseded by ADR-0011.
* **Update**: [Build a change in layers](/runbooks/build-in-layers.md): blocking bar in each ticket, `make test` concurrency and the GNU Make 3.81 shell-flags trap.
* **Update**: Bundle prose translated to English (ADR-0010).
* **Update**: ADR-0010 glossary extended with the Migration and Verification log labels.

## 2026-10-30
* **Update**: Profile vocabulary moved to knowledge/2.0 (ADR-0010): directories, types and slugs renamed.
* **Creation**: [ADR-0010](/decisions/ADR-0010-english-canonical-profile-2.md): English as the canonical language and profile knowledge/2.0, with a migration glossary.
* **Deprecation**: [ADR-0003](/decisions/ADR-0003-spanish-names.md), superseded by ADR-0010.
* **Creation**: [ADR-0009](/decisions/ADR-0009-build-in-layers-and-tickets.md) and the runbook [Build a change in layers](/runbooks/build-in-layers.md): doctrine for building multi-stage changes in layers and delegated tickets.
* **Creation**: Project page, 8 ADRs (ADR-0001 to ADR-0008), architecture view, 3 systems, 3 runbooks, 2 policies, 6 terms and 3 references, capturing the decisions made while designing the standard and the plugin.
* **Initialization**: `knowledge/` structure created with profile knowledge/1.0 (OKF v0.2).
