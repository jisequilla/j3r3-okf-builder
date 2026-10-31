# Bundle history

## 2026-10-31
* **Update**: [Export and deliver projections](/runbooks/export-projections.md) and the [projections view](/architecture/single-source-projections.md): M365 Copilot reads the bundle through the GitHub connector or from a SharePoint source (ADR-0014); the claim that SharePoint indexes `.md` as is is gone.
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
