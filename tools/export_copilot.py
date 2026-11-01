#!/usr/bin/env python3
"""export_copilot.py — Build the OKF pack for GitHub Copilot from the plugin.

Copilot (VS Code agent mode, Copilot CLI and coding agent) discovers Agent Skills
(SKILL.md, agentskills.io standard) in .github/skills/, .claude/skills/ or
.agents/skills/. This exporter:

  1. Copies each plugin skill to <out>/.github/skills/<skill>/.
  2. Resolves the <skills> convention of the SKILL.md files to the target repo path.
  3. Writes a custom agent .github/agents/okf.agent.md that orchestrates the skills.
  4. Writes an AGENTS.md snippet with the inventory and the rule for reading knowledge/.

Usage:
    python3 tools/export_copilot.py [--out dist/copilot] [--skills-dir .github/skills] [--zip]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "okf-builder"

AGENT_MD = """---
name: okf
description: OKF (Open Knowledge Format) knowledge manager for this repository. Use it to initialize knowledge/, capture ADRs/runbooks/systems, capture meetings as fragments and distill them, run the double check, validate, regenerate indexes, migrate between OKF 0.1 and 0.2, and answer questions about the project from knowledge/.
tools: ["read", "edit", "search", "shell"]
---

You are the OKF agent of this repository. The project knowledge lives in `knowledge/`
as an OKF bundle (markdown + YAML frontmatter). Always work through the `okf-*` skills
in `{skills_dir}/`; they are the source of truth for the standard and hold the
templates and the scripts.

Rules:
1. Before answering about the project, navigate `knowledge/index.md` → directory
   indexes → concepts (okf-ask skill). Cite paths and the confidence level.
2. To create or change knowledge use okf-capture: template, `log.md`, index and lint.
   Never add `verified` with `human:` without the person's explicit confirmation.
   Meetings, transcripts and chats go to okf-fragment first; okf-distill proposes the
   change set and applies only what the person approves; okf-review resolves conflicts.
3. Before finishing any change in `knowledge/`, regenerate the indexes (okf-index) and validate
   with okf-lint: `uv run {skills_dir}/okf-standard/scripts/okf_lint.py knowledge`; fix every ERROR.
4. Respect the OKF version of the bundle (`okf_version` in `knowledge/index.md`); do not mix
   0.1 and 0.2 forms. To change version use okf-migrate with `--dry-run` first.
5. If `knowledge/` does not exist, propose okf-init and wait for confirmation.
"""

AGENTS_SNIPPET = """## Project knowledge (OKF)

Knowledge lives in `knowledge/` (Open Knowledge Format, markdown + YAML frontmatter).
Always start at `knowledge/index.md` and go down through the `index.md` of each directory.

Skills available in `{skills_dir}/` (Agent Skills standard, also valid for Claude Code):

| Skill | Use |
|---|---|
| okf-standard | OKF v0.1/v0.2 standard, knowledge/2.0 profile, templates and scripts |
| okf-init | Create `knowledge/` |
| okf-capture | Add an ADR, runbook, system, API, table, metric, term, policy |
| okf-fragment | Keep a meeting, transcript or chat as a fragment in `fragments/` |
| okf-distill | Distill a fragment into concepts; nothing is applied before the person approves |
| okf-review | Double check: changes, open conflicts, concepts awaiting human review |
| okf-lint | Check conformance (`uv run {skills_dir}/okf-standard/scripts/okf_lint.py knowledge`) |
| okf-index | Regenerate `index.md` |
| okf-ask | Answer questions citing concepts and confidence |
| okf-migrate | Migrate between OKF 0.1 and 0.2 |

Agent: `@okf` (`.github/agents/okf.agent.md`). CI validation: `okf_lint.py knowledge --strict`.
"""


# The paths note of the source SKILL.md files ("Rutas" until the skill prose is translated)
PATHS_NOTE_RE = re.compile(r"^> \*\*(?:Rutas|Paths)\.\*\*.*$\n?", re.M)


def rewrite(text: str, skills_dir: str) -> str:
    text = PATHS_NOTE_RE.sub(f"> **Paths.** Relative to the repository root; the `okf-*` skills are in `{skills_dir}/`."
                           " Without uv, `python3` works if PyYAML is installed.\n", text)
    # The source skills use the <skills> convention; here it becomes the target repo path.
    return text.replace("<skills>/", f"{skills_dir}/").replace("${CLAUDE_PLUGIN_ROOT}/skills", skills_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist/copilot", help="output directory (relative to the repo)")
    ap.add_argument("--skills-dir", default=".github/skills",
                    help=".github/skills (Copilot) | .agents/skills (neutral) | .claude/skills")
    ap.add_argument("--zip", action="store_true", help="also package the output as okf-copilot-pack.zip")
    args = ap.parse_args(argv)

    out = (ROOT / args.out).resolve()
    skills_dir = args.skills_dir.strip("/")
    dst_skills = out / skills_dir
    if out.exists():
        shutil.rmtree(out)
    dst_skills.mkdir(parents=True)

    n = 0
    for skill in sorted((PLUGIN / "skills").iterdir()):
        if not (skill / "SKILL.md").exists():
            continue
        target = dst_skills / skill.name
        shutil.copytree(skill, target, ignore=shutil.ignore_patterns("__pycache__"))
        for md in target.rglob("*.md"):
            md.write_text(rewrite(md.read_text(encoding="utf-8"), skills_dir), encoding="utf-8")
        n += 1
    # license in the skill that ships the Google spec
    lic = dst_skills / "okf-standard" / "references" / "OKF-SPEC-LICENSE.md"
    if lic.exists():
        std = dst_skills / "okf-standard" / "SKILL.md"
        s = std.read_text(encoding="utf-8")
        if "license:" not in s.split("---")[1]:
            s = s.replace("\n---\n", "\nlicense: Apache-2.0 (Google specs in references/); the rest of the skill under the repo LICENSE\n---\n", 1)
        std.write_text(s, encoding="utf-8")

    agents = out / ".github" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "okf.agent.md").write_text(AGENT_MD.format(skills_dir=skills_dir), encoding="utf-8")
    (out / "AGENTS.okf.md").write_text(AGENTS_SNIPPET.format(skills_dir=skills_dir), encoding="utf-8")
    (out / "README.md").write_text(
        f"""# OKF pack for GitHub Copilot

Copy the contents of this directory to the root of your repository:

- `{skills_dir}/okf-*/` — Agent Skills (discovered by Copilot in VS Code, Copilot CLI and coding agent; also by Claude Code and Gemini CLI if you use `.agents/skills`).
- `.github/agents/okf.agent.md` — custom agent `@okf` that orchestrates the skills.
- `AGENTS.okf.md` — snippet to paste into your `AGENTS.md` (or `.github/copilot-instructions.md`).

The scripts (`okf_init/lint/index/migrate.py`) are in `{skills_dir}/okf-standard/scripts/` and need Python ≥ 3.9
and PyYAML: `uv run` installs it, or plain `python3` works where it is installed. In Copilot, running scripts asks for confirmation unless you add `allowed-tools` to the SKILL.md.

Generated from the okf-builder plugin with `tools/export_copilot.py`; do not edit here: edit the plugin and export again.
""", encoding="utf-8")

    print(f"{n} skills exported to {out} ({skills_dir})")
    if args.zip:
        zpath = out.parent / "okf-copilot-pack.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(out))
        print(f"→ {zpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
