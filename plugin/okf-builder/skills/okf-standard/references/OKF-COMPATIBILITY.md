# OKF v0.1 ↔ v0.2 compatibility

**Sources:** `SPEC.md` v0.1 (commit `ee67a5c`, Jun 2026) and v0.2 (commit `780fe9d`, Jul 2026, + `62432a0`, Aug 2026, which requires an explicit offset on every timestamp) from the `GoogleCloudPlatform/knowledge-catalog` repo. Verbatim copies in `plugin/okf-builder/skills/okf-standard/references/`.

Google declares v0.2 a *minor bump* except for **two breaking changes** (§13.1). In practice a v0.2 consumer reads v0.1 with two fallbacks, and a v0.1 consumer reads v0.2 because it must tolerate unknown keys. The `knowledge/3.0` profile is **v0.2 by default** and supports v0.1 for reading, validation and migration in both directions. The OKF version and the profile version are independent; §5 covers both.

---

## 1. What does NOT change (common core)

| Element | v0.1 | v0.2 |
|---|---|---|
| Bundle = markdown tree | ✓ | ✓ |
| Reserved files `index.md`, `log.md` | ✓ | ✓ |
| `index.md` without frontmatter except the root one with `okf_version` | ✓ | ✓ |
| `log.md`: `## YYYY-MM-DD`, most recent first | ✓ | ✓ |
| `type` the only required field | ✓ | ✓ |
| `title`, `description`, `resource`, `tags` recommended | ✓ | ✓ |
| Bundle-absolute links `/dir/x.md` or relative ones | ✓ | ✓ |
| Broken links tolerated | ✓ | ✓ |
| Headings `# Schema`, `# Examples` | ✓ | ✓ |
| Types not registered; unknown keys preserved | ✓ | ✓ |
| Conformance: parseable frontmatter + `type` + well-formed reserved files | ✓ (§9) | ✓ (§11) |
| `references/` subdirectory convention (`base/references/` in profile 3.0) | ✓ (in §8 Citations) | ✓ (§6.3) |

Any tool that only uses the common core works with both versions unchanged.

---

## 2. Breaking changes (§13.1)

| # | v0.1 | v0.2 | 0.1→0.2 mapping | 0.2→0.1 mapping |
|---|---|---|---|---|
| B1 | `timestamp: <ISO>` (frontmatter) — last modification | `generated: { by: <actor>, at: <ISO> }` | `generated.at = timestamp`; `generated.by` **doesn't exist in 0.1** → a default actor is assigned (`process:okf-migrate`) or the one the user gives | `timestamp = generated.at`; `generated.by` is lost (optionally keep `generated` as an extension) |
| B2 | Body section `# Citations` with a list `[n] [title](url)` (spec) or `- url` / `- [title](url)` (real bundles) | Frontmatter `sources: [{ id, resource, title, author, usage_count, last_modified }]` + `[^id]` footnotes | Each citation → `sources[]` with `resource=url`, `title` if there is one, `id=cit-n`; `[n]` references in the body → `[^cit-n]`; remove the `# Citations` section | Each `sources[]` → a `[n] [title](resource)` line under `# Citations`; `[^id]` → `[n]`; remove the footnote definitions; signals (`author`, `usage_count`, `last_modified`) are lost unless kept as an extension |

Fallbacks the v0.2 spec allows the consumer: read `timestamp` if `generated` is missing (MAY) and parse `# Citations` (MAY). `okf-lint` in 0.2 mode reports them as `LEGACY_TIMESTAMP` / `LEGACY_CITATIONS` (warning, not error).

---

## 3. v0.2 additions (optional only; their absence ⇒ a plain v0.1 concept)

| Family | Keys | Semantics | In a v0.1 bundle |
|---|---|---|---|
| Provenance | `sources[]`, `usage_window` | What the concept derives from; credibility signals per source | Unknown → preserved, not interpreted |
| Trust | `generated`, `verified[]` | Who wrote / who confirmed. Levels: unverified / machine-confirmed / human-reviewed | Same |
| Lifecycle | `status` (`draft\|stable\|deprecated`), `stale_after` | State and absolute staleness | Same |
| Actors | `human:<id>`, `process:<id>`, `<agent>/<version>` | Convention for `generated.by`, `verified[].by`, `sources[].author` | Doesn't exist |
| Attested computation | `type: Attested Computation`, `runtime`, `parameters`, `computation`, `executor`, `attester`, heading `# Computation` | Sanctioned, verifiable computation | Unknown type → generic concept |
| Timestamps | Every datetime with an **explicit offset** (`Z` or `±hh:mm`) since `62432a0` | — | v0.1 only asked for ISO 8601 |

Minor wording differences: v0.1 says consumers *SHOULD NOT* reject unknown keys; v0.2 raises it to *MUST NOT*. v0.1 had a "Relationship to other formats" section (removed in v0.2). v0.2 adds "Non-goal: packaging executor/attester code".

---

## 4. Version detection

Order of precedence applied by `okf_common.detect_version()`:

1. `okf_version` in the frontmatter of the root `index.md` → authoritative.
2. Heuristic over the concepts:
   - Any concept with `generated`, `verified`, `sources`, `status`, `stale_after` or `type: Attested Computation` ⇒ **0.2**.
   - Otherwise, any concept with `timestamp` or a `# Citations` section ⇒ **0.1**.
   - If there are no signals (common core only) ⇒ **0.2** (indistinguishable; treated as the current version).
3. A mix of 0.1 and 0.2 signals without `okf_version` ⇒ **0.2 with a `MIXED_VERSIONS` warning** (a half-migrated bundle).

---

## 5. Profile policy (`knowledge/3.0` and `knowledge/2.0`)

### 5.1 Profile versions

| | `knowledge/2.0` (older) | `knowledge/3.0` (default) |
|---|---|---|
| Root `index.md` | `okf_profile: "knowledge/2.0"` | `okf_profile: "knowledge/3.0"` |
| Layout | Typed directories (`decisions/`, `systems/`, `references/`…) and `fragments/` at the root | Root holds `index.md`, `log.md`, `project.md`, `conflict-log.md` and the layers `fragments/`, `base/` (the typed directories, `references/` included) and `projections/` (not OKF, skipped by OKF tools) |
| Where concepts live | Anywhere in the bundle | Only in `base/` (any depth) and `fragments/`, besides `project.md` and `conflict-log.md` at the root |
| Bundle paths | `/decisions/ADR-0001-x.md` | `/base/decisions/ADR-0001-x.md` |
| `okf-init` | Not written any more | Always |
| `okf-lint` | Validated by the 2.0 layout, with a notice "profile knowledge/2.0 is outdated: run okf_migrate.py --profile knowledge/3.0" that is neither a warning nor an error (`--strict` does not fail; `"profile_outdated": true` in `--json`) | Validated by the 3.0 layout; a concept outside `base/` and `fragments/` is an error |
| Migration | `okf_migrate.py --profile knowledge/3.0`: moves the typed directories under `base/`, rewrites the bundle-path links and `sources` that point into them, sets `okf_profile` and logs a **Migration** entry | — |

`--profile` is separate from `--to`: one migrates the profile, the other the OKF version, and at least one of them is required. Migrating the profile leaves `okf_version` as it is.

### 5.2 OKF version policy

| Situation | Behaviour |
|---|---|
| New bundle (`okf-init`) | v0.2. `--okf-version 0.1` generates the 0.1 form (`timestamp`, no `generated`) for projects that must interoperate with older consumers. |
| Validate (`okf-lint`) | `--okf-version auto\|0.1\|0.2`. In 0.1: `timestamp` and `# Citations` are correct; v0.2 keys are reported as `V02_FIELD_IN_V01` (informational warning). In 0.2: `timestamp`/`# Citations` ⇒ `LEGACY_*`. The knowledge profile (which requires `generated`) only applies in 0.2; in 0.1 the required equivalent is `timestamp`. |
| Query (`okf-ask`) | Transparent: age is read from `generated.at` or, failing that, `timestamp`; sources from `sources[]` or, failing that, `# Citations`. No `verified` (always the case in 0.1) ⇒ "unverified". |
| Capture (`okf-capture`) | Writes in the bundle's detected version. Never mixes: if the bundle is 0.1, it uses `timestamp` and `# Citations`. |
| Migrate (`okf-migrate`) | `--to 0.2` (recommended, lossless) or `--to 0.1` (lossy: `generated.by`, `verified`, `status`, `stale_after`, source signals; with `--keep-extensions` they are kept as extra keys, legal in both specs). `--dry-run` is always available; updates `okf_version` and adds an entry to `log.md`. |
| Exchange with third parties | Publish in 0.2. If the consumer is strict 0.1, export with `okf-migrate --to 0.1 --keep-extensions` to a separate directory; don't downgrade the source bundle. |

---

## 6. Field matrix (quick reference)

| Key | 0.1 | 0.2 | Note |
|---|---|---|---|
| `type` | REQ | REQ | — |
| `title` `description` `resource` `tags` | REC | REC | — |
| `timestamp` | REC | ✗ (legacy) | → `generated.at` |
| `generated.by` | ✗ | REQ inside `generated` | no 0.1 equivalent |
| `generated.at` | ✗ | REC | ← `timestamp` |
| `verified[]` | ✗ | OPT | lost when going down |
| `status` | ✗ | OPT (default `stable`) | lost when going down |
| `stale_after` | ✗ | OPT | lost when going down |
| `sources[]` | ✗ | OPT | ↔ `# Citations` |
| `usage_window` | ✗ | OPT | lost when going down |
| `runtime` `parameters` `computation` `executor` `attester` | ✗ | REQ/OPT in Attested Computation | type becomes generic in 0.1 |
| `okf_version` (root index) | `"0.1"` | `"0.2"` | — |
| `# Citations` (body) | REC | ✗ (legacy) | ↔ `sources[]` |
| `# Computation` (body) | ✗ | CONV | — |
| `[^id]` footnotes | ✗ | CONV | ↔ `[n]` |
