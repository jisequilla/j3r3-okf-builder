---
name: okf-fragment
description: Captures a knowledge fragment in knowledge/fragments/, the record of a meeting, transcript, chat or slide deck kept as it happened, with its date, origin and participants, in the bundle's own type and key names, ready for okf-distill. Use when the user says "capture this meeting", "save this transcript", "record this chat", "keep this conversation", "okf fragment", or shares the notes or transcript of an event that should be kept before it is distilled. Also backfills a missing occurred_at, origin or participants in existing fragments ("backfill fragment fields", "fragments missing participants").
---

# okf-fragment

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

Keeps an event (a meeting, chat, transcript or slide deck) as a `Knowledge Fragment`: what was said, as it was said. A fragment is not distilled knowledge: `okf-distill` turns it into concepts later, with the person's approval.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop), **its version** (`okf_version` in the root `index.md`; if missing, `okf_lint.py --json` → `okf_version`) and **its OKF profile** (`okf_profile` in the root `index.md`; if missing, knowledge/2.0, the older OKF profile). Write in that version and in that OKF profile's layout.
   - `fragments/` is at the bundle root in both OKF profiles. **knowledge/2.0 bundle**: links to concepts drop the `base/` prefix (`/decisions/x.md`); never mix the two layouts, and offer the migration (`uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --profile knowledge/3.0 --dry-run`, applied only after the person confirms).
   - **The Domain Profile in force** (knowledge/3.0; a knowledge/2.0 bundle has none): run `uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle> --profiles /fragments/ --json` and read from it, not from `base/profile.md` by hand, the fragment types allowed (`Knowledge Fragment` and the local types that extend it, such as a `Client Meeting`, each with its fields and requirements), the rules and the aliases. When a local fragment type fits the event, offer it and ask for its required fields.
2. **Gather the event** and confirm it in one line before writing:
   - the record: pasted text, a file, an exported transcript;
   - `occurred_at`: when the event happened (`YYYY-MM-DD`, or ISO 8601 with an offset), not when it is captured; ask if it is not known;
   - `origin`: where it happened (the meeting, the chat channel, the slide deck, the transcription tool);
   - `participants`: who took part, as actors (`human:<id>`, `<agent>/<version>`); ask the person to confirm how names map to ids.
3. **Clean the record, and only that.** Keep it verbatim, with speaker labels and timestamps. Remove secrets (tokens, keys, passwords, connection strings) and personal data the participants did not agree to keep (phone numbers, personal emails, addresses, health data), and put `[redacted]` where each one was. Do not summarize, rephrase or correct. Tell the person how many redactions were made and of what kind.
   - **Meeting discipline** (a meeting or a transcript): mark each gap and unclear passage where it is (`[inaudible 10:42]`, `[unclear: "...?"]`) and keep every line attributed to who said it, `[unknown speaker]` when nobody knows; never fill a gap from memory. Leave out non-professional content (small talk, private matters) before freezing, and say so in the record (`[non-professional content left out]`). The raw transcript is never altered after capture: a correction is a new fragment.
   - A text record that exists elsewhere (a repo file, a document URL) is copied into `# Record` and its location cited in `sources` (`id` + `resource`).
   - Slides, recordings, images and other binaries never go into `knowledge/`: they stay in their own system or in a `/sources` folder at the repository root, and are cited in `sources`. A text export of them (a transcript) is the record.
   - **Material** (SDR-0021): when the person hands files the record is taken from, list each in `material` as `{ path, sha256 }`. A file kept in the bundle is text and already redacted (save the redacted copy, never the raw one), beside the fragment with the same name and a `.txt` (or its own text) extension, never `.md`; `sha256` is the digest of the file as kept (`shasum -a 256 <file>`, or `python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <file>`). `path` is relative to the bundle root (`fragments/2026-10-31-call.txt`) or a bundle path (`/fragments/...`), never relative to the fragment's directory. A binary at the repository root is named with `../` (`../sources/deck.pdf`): lint gives it a notice, outside the bundle, and does not check it. Quote `sha256` (`sha256: "ab12..."`): an unquoted all-digit value is read as a number (`BAD_MATERIAL`). Lint reports a material file in the bundle that no longer matches as `FRAGMENT_MATERIAL_CHANGED`, an error.
   - **A repository at a commit**: when the record is a reading of a repository, write `repository: { url: <url>, commit: "<full commit>" }` with the commit read from git (`git -C <repo> rev-parse HEAD`, 40 hex digits, quoted), never typed from memory or shortened. Never put a token in the `url`.
4. **Name the file** `fragments/YYYY-MM-DD-slug.md` with the date of the event; slug in ASCII kebab-case. When one event yields several fragments, the slug may carry the origin and a sequence number (`2026-10-31-conv-01-roles.md`). If the file already exists, choose another slug; never overwrite a fragment.
5. **Write** from the template `<skills>/okf-standard/templates/fragment.md`:
   - Replace every `{{...}}`. `title`: `YYYY-MM-DD · <topic>`. `description`: one self-contained sentence on what the event was about. `actor` = whoever supplies the record: `human:<id>` if the person provides it and Claude only formats it; `okf-builder/<model>` if Claude writes the record itself (for example, of its own session). `now` = UTC ISO 8601 `YYYY-MM-DDTHH:MM:SSZ`.
   - The commented `# material:` and `# repository:` lines: delete each one unless material or a repository applies (step 3); only then fill its `{{...}}` and uncomment it.
   - `status: draft` and `distillation_status: pending`. Do **not** add `verified`.
   - **The bundle's own names** (the `aliases` in force): write a local name for a type or a field only when the existing concepts of that type already use it more than the declared name, and the declared name on a tie or when no concept uses a local one, since writing a local name no concept uses would rename the bundle's vocabulary. A type alias names exactly its target (a local name of `Client Meeting` is never a `Knowledge Fragment`). A value alias is written in reverse (`ingerido: false` for `distillation_status: pending`) only when the type is written with a local name and exactly one alias maps to that field and value. Lint reads every local name as the declared one.
   - A link to a concept uses its bundle path under `base/` (`/base/decisions/architecture/ADR-0001-x.md`), and a link to another fragment `/fragments/<file>`.
   - The record goes under `# Record`. Leave `# Distillation` with its empty table: `okf-distill` fills it.
   - **0.1 bundle**: after saving, run `uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file <relative-path>`; never leave 0.2 keys in a 0.1 bundle.
6. **The record is immutable from now on.** Later, only `distillation_status` (or the local key a value alias reads as it) and `# Distillation` change, plus a one-time backfill of a missing capture field (see Backfill). `material` and `repository` are written at capture only, and a material file is never edited after it. A wrong record is deprecated (`status: deprecated`, linking the fragment that replaces it), never edited or deleted.
7. **Log**: add a `* **Creation**: ...` entry linking the fragment by its bundle path (`/fragments/<file>`) to `knowledge/log.md` under today's date (create the section if it doesn't exist, above the earlier ones). If `fragments/` has its own `log.md`, add it there too.
8. **Index and validate**:
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir fragments
   uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
   ```
   The run regenerates `fragments/index.md` and the root `index.md` above it. Fix any ERROR before finishing.
9. **Close**: show the fragment's path, `occurred_at`, the participants, the redactions, the gaps marked and what was left out, and the `material` and `repository` written. Ask the person to confirm the record with someone who was there before it is distilled, and offer `okf-distill` once it is confirmed. Do not distill in the same step unless the person asks.

## Backfill

For fragments captured before a capture field existed (`okf_lint` warns `FRAGMENT_NO_FIELD`). Only `occurred_at`, `origin` and `participants`, and only where the field is absent.

1. **Find them**: `uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle> --json`, the `FRAGMENT_NO_FIELD` items for those three fields.
2. **Read each value from the evidence**: the fragment's own `# Record` (a date line, attendee lines, speaker labels) or an original its `sources` already cite. Never infer it, take it from memory or from another fragment. `participants` lists the actors the record shows taking part. If the record does not show the value, leave the field absent: the warning stays, and that is correct.
3. **Propose a change set**: one row per fragment with the field, the value, and the line of the record or the source it comes from; for `participants`, how each name maps to an actor id (`human:<id>`). Apply nothing until the person approves it, mappings included.
4. **Apply**: add only the absent keys. Never change a value already written (a wrong one means the fragment is deprecated and replaced), and leave `# Record`, `generated` and every other key as they are. Do not add `verified`.
5. **Log**: one `* **Update**: ...` entry in `knowledge/log.md` under today's date naming the fragments, the fields filled and who approved them.
6. **Validate**: `uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle>`; the backfilled fields no longer warn.
