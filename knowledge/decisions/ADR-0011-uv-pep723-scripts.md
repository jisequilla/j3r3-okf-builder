---
type: Architecture Decision
title: "ADR-0011: Scripts run with uv and declare PyYAML inline (PEP 723)"
description: The okf-standard scripts declare PyYAML in PEP 723 inline metadata and run with uv run, the reduced YAML parser is removed, and each script carries its own tests.
tags: [adr, tooling]
status: draft
adr_id: ADR-0011
decision_status: accepted
supersedes: /decisions/ADR-0006-dependency-free-scripts.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T03:15:21Z }
sources:
  - { id: m365-note, resource: tools/export_m365.py }
  - { id: common, resource: plugin/okf-builder/skills/okf-standard/scripts/okf_common.py }
---

# Context

[ADR-0006](/decisions/ADR-0006-dependency-free-scripts.md) made the scripts dependency-free so they would run in any agent's sandbox, and paid for it with `_mini_yaml`, a reduced YAML parser used when PyYAML is missing[^common]. Keeping that parser equivalent to PyYAML has become the main cost of the scripts: three review rounds of one ticket each found a new input where the two disagreed, and the repo carries a differential checker and a no-PyYAML pass of every test to hold the line.

The premise that only `python3` is available no longer holds where it was tested. A probe in the Claude Cowork sandbox found Python 3.13, uv 0.11, PyYAML 6.0.3 already installed, and PyPI reachable. GitHub Copilot's coding agent and CI in other repos run on runners whose setup each repo controls, so they can install uv. Microsoft 365 Copilot is told to run the scripts with `python3` and, if it cannot, to apply the rules by hand from `references/`[^m365-note]; its runtime has not been probed.

# Decision

1. **Each entry script (`okf_init`, `okf_lint`, `okf_index`, `okf_migrate`) starts with PEP 723 inline metadata** declaring `dependencies = ["pyyaml"]` and `requires-python = ">=3.9"`. The skills invoke them as `uv run "<skills>/okf-standard/scripts/<script>.py"`.
2. **PyYAML is required.** `_mini_yaml`, `OKF_NO_PYYAML`, `tools/check_mini_yaml.py` and the no-PyYAML test pass are removed. `okf_common` imports `yaml` directly.
3. **Plain `python3` stays a fallback**, because the metadata block is a comment to Python: `python3 <script>.py` works wherever PyYAML is installed. With neither uv nor PyYAML, the script exits with one message naming both ways to fix it.
4. **Each script carries its own tests**, run with `uv run --with pytest <script>.py --test`. pytest is a test-time dependency only and never appears in the runtime metadata. Checks of one script's behavior live in that script; `make test` runs every script's `--test` and then the cross-script runs (init → index → lint, Google fixtures, the 0.1 ↔ 0.2 migration round trip), which belong to no single script.

| Environment | How the scripts run |
|---|---|
| Claude Cowork | `uv run` (probed); `python3` also works, PyYAML is preinstalled |
| Claude Code, Gemini CLI | The developer's machine: install uv, or PyYAML for `python3` |
| GitHub Copilot coding agent, CI in other repos | The repo installs uv in its setup steps (`setup-uv` or the agent's setup workflow) |
| Microsoft 365 Copilot | Unprobed: `python3` if PyYAML is present, otherwise the existing apply-by-hand fallback |

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep ADR-0006 and the reduced parser | Runs with bare `python3` | Every parser gap is a silent divergence from PyYAML; the differential test only covers inputs someone thought of | The cost is ongoing and grows with each review |
| Vendor PyYAML's pure-Python package in `scripts/` | Bare `python3`, offline, no parser of our own | About 5,900 lines of third-party code in every projection, plus a license notice and manual updates | The probe showed uv and PyYAML where it was assumed missing |
| PEP 723 metadata but keep the reduced parser as fallback | No host loses anything | Keeps the parser and its maintenance | It keeps the problem this ADR removes |
| Separate test files next to the scripts | Shorter scripts | A copied script loses its tests | Self-contained scripts are the point of the change |

# Consequences

- Positive: one YAML parser everywhere; about 450 lines of parser code and its checker disappear; a script copied into another repo brings its dependencies and its tests.
- Negative / accepted debt: a host with neither uv nor PyYAML can no longer run the scripts; Microsoft 365 Copilot may fall to applying the rules by hand where it ran them before; running the tests needs network access the first time uv fetches pytest and PyYAML.
- Follow-up actions: one build ticket following [Build a change in layers](/runbooks/build-in-layers.md) covering the metadata blocks, removing the parser, the inline tests, `make test`, the skills' invocations, the exporters' instructions (`export_copilot.py`, `export_m365.py`), the `okf-standard` skill's requirements line and the [project page](/project.md); probe Microsoft 365 Copilot with the same commands used in Cowork.

# Related

* [ADR-0006: Python scripts without external dependencies](/decisions/ADR-0006-dependency-free-scripts.md) (superseded)
* [ADR-0007: Single source and projections](/decisions/ADR-0007-single-source-and-projections.md)
* [Exporters](/systems/exporters.md)

[^m365-note]: The environment note `export_m365.py` adds to every skill in the Microsoft 365 package.
[^common]: `parse_yaml` in `okf_common.py` falls back to `_mini_yaml` when `import yaml` fails.
