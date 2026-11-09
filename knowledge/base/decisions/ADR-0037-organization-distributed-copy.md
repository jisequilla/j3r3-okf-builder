---
type: Architecture Decision
title: "ADR-0037: An organization receives a copy of okf-builder that it owns and versions, pulls later releases when it chooses, and runs lint from the installed plugin"
description: The organization package, generated from a tagged release of okf-builder, delivers the skills with their scripts as plain files, the organization's Domain Profile and a pre-commit hook; once delivered the copy is the organization's, which may take it in its own direction and versions it by its own release process while recording the okf-builder version it was taken from; a later okf-builder release reaches it only when the organization pulls it, by a pull request in its own repository; its repositories run lint from the plugin each person installs, with no pinned version; the installable scripts package is deferred; other OKF dialects still converge as Domain Profiles and validators. Supersedes ADR-0034.
tags: [adr, distribution, packaging]
status: draft
adr_id: ADR-0037
decision_status: accepted
supersedes: /base/decisions/ADR-0034-organization-package.md
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-09T05:26:38Z }
sources:
  - { id: fragment, resource: /fragments/2026-11-09-organization-distributed-copy.md }
  - { id: adr-0034, resource: /base/decisions/ADR-0034-organization-package.md }
  - { id: adr-0036, resource: /base/decisions/ADR-0036-release-please.md }
  - { id: adr-0026, resource: /base/decisions/ADR-0026-built-in-domain-profile.md }
  - { id: adr-0028, resource: /base/decisions/ADR-0028-where-things-go.md }
---

# Context

ADR-0034 delivered okf-builder to an organization as a package proposed to the organization's marketplace by a reviewed pull request for every release, and had each of the organization's repositories pin the version that checks it by running lint from an installable scripts package[^adr-0034]. It assumed that the organization keeps following okf-builder and that its repositories run lint where no plugin is installed.

Designing that scripts package (ticket okf-lyg.2) showed that it works without changing the scripts, and that it serves only a repository whose CI runs lint without Claude or the plugin. On 2026-11-09 the owner, human:jisequilla, said no repository has that need, nor will for now, and that the organization needs the plugin distributed to it so that it installs it and keeps its own version, living with the risk of drift, since it may take the skills and the plugin in its own direction. The owner then shaped the decision in answer to structured questions[^fragment].

# Decision

1. **The organization package delivers a copy.** `just org-package` writes, from a tagged release of okf-builder, a bundle for an organization's own marketplace: okf-builder's skills with their scripts as plain files, the organization's Domain Profile and the hook of decision 5. The organization names the bundle; nothing in it names this repository's owner. The export carries okf-builder's version (ADR-0036 decision 1)[^adr-0036]. This repository stays the generic upstream.
2. **Once delivered, the copy is the organization's.** The organization may change its skills, scripts, templates and copy of the standard, and take them in its own direction. okf-builder never pushes to it, and neither depends on the other at run time. The drift this allows is accepted.
3. **The copy keeps its own version and records its base.** The organization versions the copy by its own release process, starting from the version it chooses. The package's README names the okf-builder version it was taken from, and each later pull updates that name.
4. **A later okf-builder release arrives only when the organization pulls it.** The organization asks for a new export at a later okf-builder tag and proposes it as a pull request in its own repository, under that repository's contribution rules; the pull request shows the new release against the organization's own changes, and resolving them is the organization's work.
5. **The organization's repositories run lint from the installed plugin.** Lint is the `okf_lint.py` of the plugin each person installs: the skills call it in a Claude session, and a pre-commit hook runs it at `--strict`, set up by a session-start hook the package ships, where CI runs no repository pipeline. No repository records the version that checks it, and the root `index.md` gains no key for it; two people on different versions of the plugin may get different results.
6. **The installable scripts package is deferred.** No package with entry points such as `okf-lint` is built. It returns, by its own ADR, when a repository needs lint where no plugin is installed.
7. **Other dialects converge on this standard.** An organization that already runs other OKF dialects declares their conventions (types, fields, folders, local names through aliases) as Domain Profiles, and their own checks as validators a Domain Profile declares (ADR-0026)[^adr-0026], so no repository carries scripts inside `knowledge/` (ADR-0028 decision 4)[^adr-0028]. `okf_migrate` learns each dialect it meets, and repositories move by pilots on branches, keeping every recorded human verification.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| ADR-0034 as it stood: a reviewed pull request per release, lint pinned per repository | One copy of the code; every repository names its version | Assumes the organization keeps following okf-builder; needs an installable package no repository needs | The organization will take the copy in its own direction |
| A one-time fork with no record of its base | Nothing to maintain | A later pull cannot tell what it changes | Recording the base costs one line |
| okf-builder keeps delivering every release | The organization stays close to upstream | Pushes changes the organization may not want, onto a copy that diverges | The organization chooses when it moves |
| Build the installable scripts package now | Ready for CI without Claude | Code and a release asset nobody uses | No repository runs lint outside Claude |

# Consequences

- Positive: the organization adapts the plugin to its own practice without waiting for okf-builder; okf-builder's releases stay its own; no package or pin is built for a need nobody has.
- Negative / accepted debt: the organization's copy and okf-builder drift, and an improvement on either side does not reach the other unless someone carries it; a later pull can be a large merge; lint results depend on the plugin version each person installed; the organization's copy may come to check something other than what the standard says.
- Follow-up actions: `just org-package`; the export runbook gains the organization package; the epic's tickets for the organization's bundle and its pilots follow this decision; ticket okf-lyg.2 stays deferred with its design.

# Related

* [ADR-0034: The organization package](/base/decisions/ADR-0034-organization-package.md)
* [ADR-0036: Releases with release-please](/base/decisions/ADR-0036-release-please.md)
* [ADR-0026: The built-in Domain Profile](/base/decisions/ADR-0026-built-in-domain-profile.md)
* [Export and deliver platform packages](/base/runbooks/export-projections.md)

[^fragment]: 2026-11-09 · An organization receives a copy of the plugin with its own version, Record.
[^adr-0034]: ADR-0034, decisions 2 and 3.
[^adr-0036]: ADR-0036, decision 1.
[^adr-0026]: ADR-0026, Decision.
[^adr-0028]: ADR-0028, decision 4.
