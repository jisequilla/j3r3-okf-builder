---
type: Architecture Decision
title: "ADR-0042: The Knowledge Viewer is a viewer setup: okf_viewer.py builds a page and its data from any knowledge/ directory, published as a Claude artifact"
description: okf_viewer.py, in okf-standard/scripts/, reads a bundle as okf-lint does and writes, outside the bundle, the Knowledge Viewer's page and a concepts.json snapshot naming the commit, a dirty tree and each concept's generated.at; it refuses a bundle with SECRET_IN_BUNDLE, publishes nothing, checks stored answers and writes no verified; the page is a Claude artifact for now; the Claude plugin ships it and the generated non-Claude packages do not; the graph and several owners are follow-ups.
tags: [adr, viewer, review, verification]
status: stable
adr_id: ADR-0042
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-15T15:46:31Z }
verified: [{ by: human:jisequilla, at: 2026-11-15T17:42:41Z }]
sources:
  - { id: fragment, resource: /fragments/2026-11-15-knowledge-viewer.md, title: "Fragment: the Knowledge Viewer" }
  - { id: adr-0032, resource: /base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md }
  - { id: sdr-0022, resource: /base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md }
  - { id: sdr-0024, resource: /base/decisions/standard/SDR-0024-closing-operational-bundles.md }
  - { id: okf-1lj, resource: "bead okf-1lj", title: "Knowledge Viewer (epic)" }
---

# Context

Since okf-12m, the verification rounds of this repository have run on a private Claude artifact, the OKF Review Desk: a page and a published `concepts.json`, with views of the round, every concept, the fragments, the deprecated concepts and the open items, links between concepts resolved, and a confirm or do-not-confirm answer per concept stored in the artifact[^okf-1lj]. It answers [SDR-0022](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md)'s second channel, a review page private to the person. Two parts of it are not in the repository: the generator of `concepts.json`, a recipe rebuilt by hand each round for this bundle only, and the applying of the answers, done by the agent from memory.

[ADR-0032](/base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md) made a tool that configures how a bundle is read a viewer setup, and named the web viewer of okf-1lj as the reader for those without Obsidian. On 2026-11-15 the owner, human:jisequilla, asked for that viewer to point at any `knowledge/` directory, as the Obsidian setup does, to let knowledge owners read and navigate the concepts, by links and by a graph, and confirm them. In structured questions the same day the owner named it, chose its platform, the order of the build and which packages ship it[^fragment].

**Worked example.**

- Before: each round, the agent rebuilds `concepts.json` by hand from a recipe, for this repository only, and publishes it beside the page.
- After: `uv run <skills>/okf-standard/scripts/okf_viewer.py path/to/knowledge --out /tmp/viewer` writes `/tmp/viewer/index.html` and `/tmp/viewer/concepts.json` (commit `4727d0d`, 66 concepts), and the agent publishes the two files as the page.

# Decision

1. **A viewer setup.** The Knowledge Viewer is a viewer setup in ADR-0032 decision 1's sense: neither a knowledge projection nor a platform package. It is the web viewer ADR-0032's consequences name for readers without Obsidian.
2. **A script builds it.** `okf_viewer.py`, in `okf-standard/scripts/` with the other scripts, takes a bundle root and writes into an output directory outside the bundle, never inside `knowledge/`, the page (`index.html`, copied from the template the plugin ships) and its data file `concepts.json`. The data is a snapshot: it names the repository commit, whether the tree was dirty, and each concept's `generated.at`, so an answer names a version (SDR-0022 decision 4).
3. **It reads the bundle as `okf-lint` does**: `scan_bundle`, so `.okfignore` and nested bundles, with the aliases of the Domain Profile in force. It refuses to build when lint reports `SECRET_IN_BUNDLE`, since the data is copied to the platform that hosts the page.
4. **The page is a Claude artifact for now.** Other platforms are decided when one is needed. The agent publishes the two files with its platform's tool; no script publishes.
5. **The script writes no `verified`.** It checks stored answers against the bundle and reports; the agent applies them under SDR-0022 (decision 3: no script adds `verified`).
6. **The Claude plugin ships it; the generated non-Claude packages do not.** `okf_viewer.py` and its template live in the skills' source, which the Claude plugin (`.plugin`) ships and both link packages point to, so `.agents/skills` sees them as a link to that source. The Microsoft 365 package (`just m365`) and the vendorable Copilot pack (`just copilot`) leave them out, as the Microsoft 365 package leaves out `okf_close.py` ([SDR-0024](/base/decisions/standard/SDR-0024-closing-operational-bundles.md) decision 12).
7. **Follow-ups, not decided here:** the graph view; several knowledge owners on one shared page, each answering as themselves for any concept, which needs a decision superseding SDR-0022 before it is built.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep rebuilding `concepts.json` by hand each round | Nothing to build | Works for this repository only; each round repeats the recipe and may drift from it | The owner wants the viewer to point at any `knowledge/` directory |
| One self-contained HTML file that reads anywhere and takes answers only as a Claude artifact | Opens without a platform | Two modes to build and test before the first is needed | The owner chose to start with a Claude artifact only |
| A knowledge projection `projections/viewer/` | Uses the projection tools | The page derives from the whole bundle, not from base concepts, and is not knowledge | ADR-0032 already places such a tool as a viewer setup |
| The script publishes the page | One command | Ties a script to one platform's credentials and puts the bundle on a platform without the agent in the loop | The agent publishes with its platform's tool |
| The data written inside the bundle | Next to what it shows | A generated file in `knowledge/` that lint reads and git tracks | Written outside the bundle |
| Leave it out of Microsoft 365 only | The router's first proposal; one exclusion | The vendorable Copilot pack carries a script for a page it cannot publish | The owner chose to leave it out of every generated non-Claude package |
| Restructure the links so `.agents/skills` leaves it out | Claude-only everywhere | Build work and a second layout of the skills' source | Not worth it while the link points to the same source |

# Consequences

- Positive: any bundle gets a review page with one command and a published page; the generator and the check of answers live in the repository, tested, instead of in a recipe and in memory; the page shows exactly one commit's concepts, each with its version.
- Negative / accepted debt: one more script and a page template in the Claude plugin; `.agents/skills` sees a script its platforms cannot publish a page with; until the several-owners decision, only the person whose account owns the page answers on it (SDR-0022 decision 4).
- Follow-up actions (tracker epic okf-1lj): `okf_viewer.py` and the page template at parity with the current page, on any `knowledge/` directory (layer 1); the check of stored answers, `okf-review` running a round with it and this repository's page published from it (layer 2); the graph (layer 3); several owners under a decision superseding SDR-0022 (layer 4); the exporters leave the script and the template out.

# Related

* [ADR-0032: A bundle opens as an Obsidian vault through a viewer setup](/base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md)
* [SDR-0022: Verification recorded by question or review page](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md)
* [SDR-0024: Closing operational bundles](/base/decisions/standard/SDR-0024-closing-operational-bundles.md)

[^fragment]: 2026-11-15 · The Knowledge Viewer, Record.
[^okf-1lj]: Bead okf-1lj, description and comments of 2026-11-07.
