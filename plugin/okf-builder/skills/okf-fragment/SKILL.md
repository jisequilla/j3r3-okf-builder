---
name: okf-fragment
description: Captures a knowledge fragment in knowledge/fragments/, the record of a meeting, transcript, chat or slide deck kept as it happened, with its date, origin and participants, ready for okf-distill. Use when the user says "capture this meeting", "save this transcript", "record this chat", "keep this conversation", "okf fragment", or shares the notes or transcript of an event that should be kept before it is distilled.
---

# okf-fragment

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

Keeps an event (a meeting, chat, transcript or slide deck) as a `Knowledge Fragment`: what was said, as it was said. A fragment is not distilled knowledge: `okf-distill` turns it into concepts later, with the person's approval.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop) and **its version** (`okf_version` in the root `index.md`; if missing, `okf_lint.py --json` → `okf_version`). Write in that version.
2. **Gather the event** and confirm it in one line before writing:
   - the record: pasted text, a file, an exported transcript;
   - `occurred_at`: when the event happened (`YYYY-MM-DD`, or ISO 8601 with an offset), not when it is captured; ask if it is not known;
   - `origin`: where it happened (the meeting, the chat channel, the slide deck, the transcription tool);
   - `participants`: who took part, as actors (`human:<id>`, `<agent>/<version>`); ask the person to confirm how names map to ids.
3. **Clean the record, and only that.** Keep it verbatim, with speaker labels and timestamps. Remove secrets (tokens, keys, passwords, connection strings) and personal data the participants did not agree to keep (phone numbers, personal emails, addresses, health data), and put `[redacted]` where each one was. Do not summarize, rephrase or correct. Tell the person how many redactions were made and of what kind.
   - A text record that exists elsewhere (a repo file, a document URL) is copied into `# Record` and its location cited in `sources` (`id` + `resource`).
   - Slides, recordings, images and other binaries never go into `knowledge/`: they stay in their own system or in a `/sources` folder at the repository root, and are cited in `sources`. A text export of them (a transcript) is the record.
4. **Name the file** `fragments/YYYY-MM-DD-slug.md` with the date of the event; slug in ASCII kebab-case. When one event yields several fragments, the slug may carry the origin and a sequence number (`2026-10-31-conv-01-roles.md`). If the file already exists, choose another slug; never overwrite a fragment.
5. **Write** from the template `<skills>/okf-standard/templates/fragment.md`:
   - Replace every `{{...}}`. `title`: `YYYY-MM-DD · <topic>`. `description`: one self-contained sentence on what the event was about. `actor` = whoever supplies the record: `human:<id>` if the person provides it and Claude only formats it; `okf-builder/<model>` if Claude writes the record itself (for example, of its own session). `now` = UTC ISO 8601 `YYYY-MM-DDTHH:MM:SSZ`.
   - `status: draft` and `distillation_status: pending`. Do **not** add `verified`.
   - The record goes under `# Record`. Leave `# Distillation` with its empty table: `okf-distill` fills it.
   - **0.1 bundle**: after saving, run `uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file <relative-path>`; never leave 0.2 keys in a 0.1 bundle.
6. **The record is immutable from now on.** Later, only `distillation_status` and `# Distillation` change. A wrong record is deprecated (`status: deprecated`, linking the fragment that replaces it), never edited or deleted.
7. **Log**: add a `* **Creation**: ...` entry linking the fragment by its bundle path (`/fragments/<file>`) to `knowledge/log.md` under today's date (create the section if it doesn't exist, above the earlier ones). If `fragments/` has its own `log.md`, add it there too.
8. **Index and validate**:
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir fragments
   uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir .
   uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
   ```
   Fix any ERROR before finishing.
9. **Close**: show the fragment's path, `occurred_at`, the participants and the redactions, and offer `okf-distill` for it. Do not distill in the same step unless the person asks.
