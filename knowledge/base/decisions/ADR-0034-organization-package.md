---
type: Architecture Decision
title: "ADR-0034: An organization receives okf-builder as its own package, copied in by a reviewed pull request per release, and each of its repositories pins the version that checks it"
description: A new generated platform package, the organization package, writes okf-builder's skills, its scripts as an installable package and the organization's Domain Profile into a bundle of the organization's own marketplace through a reviewed pull request per release; each repository of the organization records the version in its root index and runs lint at that version from that marketplace, never from a copy; other OKF dialects the organization runs converge on this standard as Domain Profiles and validators.
tags: [adr, distribution, packaging]
status: draft
adr_id: ADR-0034
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-07T10:09:05Z }
sources:
  - { id: adr-0007, resource: /base/decisions/ADR-0007-single-source-and-projections.md }
  - { id: adr-0011, resource: /base/decisions/ADR-0011-uv-pep723-scripts.md }
  - { id: adr-0026, resource: /base/decisions/ADR-0026-built-in-domain-profile.md }
  - { id: adr-0028, resource: /base/decisions/ADR-0028-where-things-go.md }
---

# Context

okf-builder reaches people as platform packages of this repository (ADR-0007): the Claude plugin from its marketplace, the Cowork plugin, the vendorable Copilot pack and the Microsoft 365 packages[^adr-0007]. Each one installs at the level of a person or is copied into a repository. Neither suits an organization that keeps knowledge in many repositories of its own:

- a plugin installed per person has the version each person last updated to, and no repository says which version checked it;
- a copied pack drifts: a copy is edited in one repository and not in another, and an upgrade is a large diff in each;
- an organization's repositories may sit on hosting that cannot reach this repository, run CI that runs no repository pipelines, or must not depend at run time on a repository the organization does not own.

A read-only review on 2026-11-07 of a set of repositories that adopted OKF early showed all three: four dialects of OKF with the same core (fragments, base, projections, profiles), the capability travelling as plugins nobody pins, the enforcement travelling as scripts copied into each repository whose copies had diverged, and no repository recording the version that checked it.

The owner, human:jisequilla, decided a new way to distribute okf-builder in answer to structured questions on 2026-11-07.

# Decision

1. **The organization package, a new generated platform package.** `make org-package` writes a bundle for an organization's own marketplace: okf-builder's skills, its scripts as an installable package (entry points such as `okf-lint`, ADR-0011 for the dependencies), the organization's Domain Profile, and the hooks below. The organization names the bundle; nothing in it names this repository's owner. This repository stays the generic upstream.
2. **Releases arrive by a reviewed pull request.** For each release of okf-builder, the export is proposed to the organization's marketplace repository as a pull request, under that repository's own contribution rules; once merged, the organization's release process versions the bundle, and its repositories move by a version bump. At run time, neither the organization's marketplace nor its repositories depend on this repository.
3. **Each repository pins the version that checks it.** The root `index.md` of a bundle records `okf_tooling: <bundle>@<version>`. Lint runs at that version from the organization's marketplace repository, from wherever the organization hosts it: `uvx --from "git+<marketplace repository>@<bundle>-v<version>#subdirectory=bundles/<bundle>" okf-lint knowledge --strict`. Where CI runs no repository pipeline, a pre-commit hook runs it, enabled by a session-start hook the bundle ships. No repository copies the scripts.
4. **Other dialects converge on this standard.** An organization that already runs other OKF dialects declares their conventions (types, fields, folders, local names through aliases) as Domain Profiles, and their own checks as validators a Domain Profile declares (ADR-0026), so no repository carries scripts inside `knowledge/` (ADR-0028 decision 4). `okf_migrate` learns each dialect it meets, and repositories move by pilots on branches, keeping every recorded human verification.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| The plugin per person, with auto-update | Nothing to build | No version per repository; each person at their own version | It is how the drift arose |
| A vendored pack per repository with a hash check | Works offline | A copy per repository; a large diff per upgrade | It detects drift; pinning removes it |
| The organization's bundle referencing this repository instead of a copy | Less to maintain | Every repository depends on this repository at install time | The organization must not depend on it |
| Lint from this repository's release tag | Simple | Needs this repository reachable wherever lint runs | The organization's own hosting is always reachable to it |
| A package registry for the scripts | Cleanest for CI | Not every organization has a Python registry | Git hosting is enough, and every organization has it |
| Adopt the organization's existing dialect as the standard | No migration | Each dialect leaves open what this standard checks | The other dialects' conventions fit as Domain Profiles |

# Consequences

- Positive: one copy of the code, whose version each repository names; an upgrade is a one-line pull request whose lint result shows what it changes; repositories on any hosting, with or without pipelines, get the same checks.
- Negative / accepted debt: a release ends in a second pull request, in the organization's repository and under its review; the scripts must become an installable package; a Domain Profile cannot yet be extended across repositories, which an organization's shared profile needs; migrating a dialect is work in repositories other people use.
- Follow-up actions: the installable package and `okf_tooling` in the standard; `make org-package`; an ADR for extending a Domain Profile across repositories, pinned to a version; `okf_migrate` for each dialect met; other dialects' checks as validators; the export runbook gains the organization package.

# Related

* [ADR-0007: Single source of skills and platform packages](/base/decisions/ADR-0007-single-source-and-projections.md)
* [ADR-0026: The built-in Domain Profile](/base/decisions/ADR-0026-built-in-domain-profile.md)
* [ADR-0028: Where things go](/base/decisions/ADR-0028-where-things-go.md)
* [Export and deliver platform packages](/base/runbooks/export-projections.md)

[^adr-0007]: ADR-0007, Decision.
