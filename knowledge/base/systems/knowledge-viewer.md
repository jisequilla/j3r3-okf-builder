---
type: System
title: Knowledge Viewer
description: A page private to its owner, built by okf_viewer.py from a bundle and published as a Claude artifact, on which the owner reads the concepts, follows their links, and confirms or does not confirm each one at the version shown; okf_viewer.py --answers checks the stored answers against the bundle, and only the agent writes verified.
resource: /plugin/okf-builder/skills/okf-standard/viewer
tags: [system, viewer, review, verification]
status: stable
owner: human:jisequilla
runtime: claude-artifact
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-15T21:48:55Z }
verified: [{ by: human:jisequilla, at: 2026-11-17T20:53:27Z }]
sources:
  - { id: adr-0042, resource: /base/decisions/architecture/ADR-0042-knowledge-viewer.md }
  - { id: template, resource: plugin/okf-builder/skills/okf-standard/viewer/index.html, title: "The page template" }
  - { id: script, resource: plugin/okf-builder/skills/okf-standard/scripts/okf_viewer.py, title: "okf_viewer.py" }
---

# Responsibility

The Knowledge Viewer is the review page of [SDR-0022](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md)'s second channel, a viewer setup in the sense of [ADR-0032](/base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md) and [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md). [okf_viewer.py](/base/systems/scripts-okf.md) builds it from any bundle into a directory outside the bundle: `index.html`, the template the plugin ships in `okf-standard/viewer/`, copied byte for byte, and `concepts.json`, the bundle's data. The agent publishes the two files as a Claude artifact shared with nobody. This repository's page is `https://claude.ai/artifact/Tuhiidxvb6RtxXEuUUzszE`, built with `just viewer`.

**What the page shows.** A header names the commit, whether the tree was dirty, the number of concepts and when the page was built. A notice says what confirming means. The left pane has five views, a tally of the round and a filter by title or path:

| View (tab) | What it lists |
|---|---|
| This round | The concepts of `round.paths`, grouped as Policies (`/base/policies/`) and Decisions (every other path); the tally counts confirmed, not confirmed, still to review and changed since answered |
| Concepts | Every concept outside `fragments/` that is not deprecated, grouped by type for `base/` and as Bundle root for the root |
| Fragments | The fragments, newest first, split into awaiting distillation and distilled; they are read, never verified |
| Deprecated | The concepts in status deprecated, by path |
| Questions & conflicts | The Open Questions with the number still open, then the Conflict Log |

Each item carries a dot for its state: confirmed, not confirmed, changed since answered, already verified, or not answered.

**How a concept is shown.** Its bundle path and title, its description, chips for type, status, `decision_status`, `question_status`, `distillation_status` and owner, links to what it supersedes or is superseded by, then the verdict box and the body. The verdict box names the bundle path, the commit, `generated.at` and who wrote it, and shows the raw frontmatter as part of what is verified. The body is rendered Markdown with its footnotes: a link to a concept of the page opens it, a link to an `index.md` or `log.md` is shown as text, a link to a path not in the bundle is struck through, and an external link opens in a new tab.

**What a reader can do.** On a `base/` concept or the Project that is not deprecated: Confirm this version, Not confirmed, and Clear my answer; after Not confirmed, a comment saying why or what should change, saved with the answer. Only the artifact's owner can answer; anyone else the page is shared with reads only. Fragments, the Conflict Log and deprecated concepts are never verified.

**The data file, `concepts.json`.** A snapshot of the bundle at one commit:

| Key | From |
|---|---|
| `commit` | The repository's `HEAD`; `null` outside git |
| `dirty` | Whether git reports a change under the bundle |
| `built_at` | The time of the build |
| `round` | `name`, `title`, `paths`: the round given with `--round` and `--paths`, or by default every `base/` concept in status draft that no person verified at its current `generated.at` (`unverified`) |
| `concepts` | One entry per Markdown file with a frontmatter that lint reads, but each `index.md`, `log.md` and the Conflict Log |

Each concept: `path` (bundle path), `type`, `title`, `description`, `status`, `decision_status`, `question_status`, `distillation_status`, `owner`, `stale_after`, `supersedes` and `superseded_by` (read from the frontmatter with the aliases of the Domain Profile in force resolved); `generated_by` and `generated_at` (from `generated`); `verified_by` and `verified_at` (from `verified`, its last entry when it is a list); `layer` (`base`, `fragments` or `root`); `frontmatter` (the raw text between the `---` lines); `body` (as written); `links` (the bundle paths of the concepts its body links to).

**The answers.** The page stores one answer per concept in the artifact's database collection `answers`, which only the owner reads and writes; the document id is the bundle path without its leading `/`, with `~` for `/`. An answer holds `path`, `commit`, `generated_at` (the version shown), `choice` (`confirmed` or `not_confirmed`), `answered_at`, `by` (the platform's user id, not an OKF actor), `page_built_at`, `round` (`null` outside it) and, after a comment, `comment` and `commented_at`. Publishing the page copies the text of every concept to claude.ai.

**Checking the answers.** `okf_viewer.py <bundle> --answers <export>` reads the exported answers and writes nothing. It gives one row per answer, newest first: `APPLY` (confirmed at the current `generated.at`), `STALE` (the concept changed since), `NOT_CONFIRMED` (with the comment verbatim), `ALREADY` (a person's `verified` entry is already at that answer), `UNKNOWN` (no such concept), `NOT_VERIFIABLE` (a fragment, the Conflict Log or a deprecated concept). Only the agent writes `verified`, from the `APPLY` rows, under SDR-0022.

# Applicable rules

- The page is a viewer setup: it is built outside the bundle, never inside `knowledge/`, and nothing in the bundle reads it (ADR-0042 decisions 1 and 2).
- `okf_viewer.py` refuses to build a bundle in which lint finds a credential, since publishing copies the data to the platform (ADR-0042 decision 3).
- No script publishes the page and none writes `verified` (ADR-0042 decisions 4 and 5; SDR-0022 decision 3).
- The Claude plugin ships the script and the template; the Microsoft 365 package and the Copilot pack leave both out and carry, in place of the review page part of `okf-review`, a note pointing to the structured question (ADR-0042 decision 6).

What the page does not do yet:

- The Conflict Log never appears under Questions & conflicts: `concepts.json` leaves it out, while the view looks for it there. The header always says `knowledge/`, a bundle outside git (`commit` null) stops the page from loading, the notice cites ADR-0033 for SDR-0022, and This round labels every concept that is not a policy as a decision. Tracker item okf-1lj.8.
- No graph of the concepts and their links: tracker item okf-1lj.5.
- One owner only: several knowledge owners answering on one shared page needs a decision superseding SDR-0022, tracker item okf-1lj.6.

# Operation

* [Run a verification round](/base/runbooks/run-a-verification-round.md)
* [OKF scripts](/base/systems/scripts-okf.md), `okf_viewer.py`
* Decisions: [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md), [ADR-0032](/base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md), [SDR-0022](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md)
