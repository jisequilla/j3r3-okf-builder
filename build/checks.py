#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""checks.py — Every check of `just test`, one named step each.

Usage:
    uv run build/checks.py [STEP ...]    every step in order, or only the steps named
    uv run build/checks.py --list        the steps, in order, with what each checks

Each step runs the scripts as a person would, through `uv run`, and fails on the first exit code or assertion
that differs from what it expects. Steps write only to one temporary directory per run, removed at the end,
and to dist/, which the exporters own. The m365 step builds dist/m365/, which builtin-profile and m365-agent read.
Prints one line per result and exits 1 on the first failing step.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = Path("plugin/okf-builder")
REF = PLUGIN / "skills" / "okf-standard"
S = REF / "scripts"
EX = Path("examples/knowledge")
FIXTURES = Path("examples/fixtures")
M365 = Path("dist/m365/package/skills")
SCRIPTS = ("okf_init", "okf_index", "okf_lint", "okf_profile", "okf_migrate", "okf_audit", "okf_projection",
           "okf_obsidian", "okf_close", "okf_viewer")
CLOSING = FIXTURES / "closing-instance" / "knowledge"
# The note that replaces okf-distill's Closing mode in the M365 package, exactly
M365_NO_CLOSING = ("## Closing mode\n\nClosing an operational instance is not available in Microsoft 365 Copilot: it needs "
                   "okf_close.py, which this package does not ship. Close the instance from Claude Code or from the GitHub "
                   "Copilot pack.\n")
INIT = ("--title", "T", "--description", "D", "--actor", "human:test")


class Fail(Exception):
    pass


def expect(cond: object, message: str) -> None:
    if not cond:
        raise Fail(message)


def run(*args: object, ok: tuple[int, ...] = (0,)) -> str:
    cmd = [str(a) for a in args]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode not in ok:
        output = (proc.stdout + proc.stderr).strip()
        raise Fail(f"{' '.join(cmd)} exited {proc.returncode}\n{output[-3000:]}")
    return proc.stdout


def uv(script: Path, *args: object, ok: tuple[int, ...] = (0,)) -> str:
    return run("uv", "run", "-q", script, *args, ok=ok)


def last_line(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def lint(bundle: Path, *flags: str, script: Path = S / "okf_lint.py", zero_errors: bool = False) -> None:
    """Lint must exit 0; with zero_errors, its summary must also say 0 errors."""
    summary = last_line(uv(script, bundle, *flags))
    if zero_errors:
        expect(" 0 errors" in summary, f"{bundle}: {summary}")
    print(summary)


def text(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Steps, in the order they run
# --------------------------------------------------------------------------
def unit(tmp: Path) -> None:
    """each script's inline tests (uv run --with pytest <script> --test)"""
    for name in SCRIPTS:
        out = run("uv", "run", "-q", "--with", "pytest", S / f"{name}.py", "--test")
        print(f"{name}.py: {last_line(out).strip('= ')}")


def init_02(tmp: Path) -> None:
    """init 0.2 (profile knowledge/3.0), then index --check and lint --strict"""
    k = tmp / "init-0.2" / "knowledge"
    uv(S / "okf_init.py", "--root", k.parent, *INIT)
    uv(S / "okf_index.py", k, "--check")
    lint(k, "--strict")
    for d in ("base/decisions", "base/policies", "base/questions", "fragments"):
        expect((k / d).is_dir(), f"init did not create {d}/")
    expect((k / "project.md").is_file(), "init did not create project.md")
    expect((k / "projections" / ".gitkeep").is_file(), "init did not create projections/.gitkeep")
    expect("knowledge/3.0" in (k / "index.md").read_text(encoding="utf-8"), "index.md does not declare knowledge/3.0")
    expect(not (k / "decisions").exists(), "init created decisions/ outside base/")


GUIDE = "OKF-WRITING-GUIDE.md"
# The line between a concept template's frontmatter and its first heading that points to the guide, exactly
GUIDE_POINTER = ("{{How to write this concept: OKF-WRITING-GUIDE.md, in the okf-standard skill's references. "
                 "Delete this line.}}")
# The note of each section of a decision (SDR-0028 decision 4), exactly, in the order of the sections
DECISION_NOTES = {
    "Context": ("The forces that make a decision needed now, in one paragraph. Then a worked example, before and after. "
                "Not how the decision was reached: that is in the source fragment."),
    "Decision": "What is decided, as numbered points, each one sentence a reader can act on.",
    "Alternatives considered": "One row per option really weighed, with the reason it lost in a phrase.",
    "Consequences": "What changes for the reader. One line each: positive, accepted debt, follow-up.",
    "Related": "Links only, one per line.",
}
# Each concept template with its notes, section by section
TEMPLATE_NOTES = {"decision.md": DECISION_NOTES, "adr.md": DECISION_NOTES}
# The skills that write or verify a concept, each of which names the guide
GUIDE_SKILLS = ("okf-capture", "okf-distill", "okf-review", "okf-standard")
# A note: one {{...}} on a line of its own, with no "|" and no "}}" inside it
NOTE_RE = re.compile(r"^\{\{((?:(?!\}\})[^|])*)\}\}$")


def template_notes(path: Path, notes: dict[str, str]) -> None:
    """The template has the guide's pointer once, as its first body line, and each # section exactly one note, the
    line after its heading and a blank line, equal to its note in notes."""
    body = text(path).split("---\n", 2)[2]
    expect(text(path).count(GUIDE_POINTER) == 1 and body.startswith(f"\n{GUIDE_POINTER}\n\n# "),
           f"{path}: the pointer to the guide is not the one line between the frontmatter and the first heading")
    lines = body.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("# ")]
    headings = [lines[i][2:] for i in starts]
    expect(headings == list(notes), f"{path}: sections {headings}, expected {list(notes)}")
    for i, end in zip(starts, starts[1:] + [len(lines)]):
        heading, section = lines[i][2:], lines[i + 1:end]
        found = [line for line in section if NOTE_RE.match(line)]
        expect(len(found) == 1 and section[:2] == ["", found[0]],
               f"{path}: section # {heading} does not have exactly one note, after its heading and a blank line: {found}")
        got = NOTE_RE.match(found[0]).group(1)
        expect(got == notes[heading], f"{path}: section # {heading} has the note {got!r}, not {notes[heading]!r}")


def writing_guide(tmp: Path) -> None:
    """each concept template, in the plugin and in the root copy, has the pointer to OKF-WRITING-GUIDE.md and one note
    per section equal to its expected text; okf-capture, okf-distill, okf-review and okf-standard name the guide"""
    for name, notes in TEMPLATE_NOTES.items():
        for path in (REF / "templates" / name, Path("templates") / name):
            template_notes(path, notes)
    print(f"{', '.join(TEMPLATE_NOTES)}: the pointer to the guide, and one note per section as expected")
    missing = [s for s in GUIDE_SKILLS if GUIDE not in text(PLUGIN / "skills" / s / "SKILL.md")]
    expect(not missing, f"SKILL.md does not name {GUIDE}: {', '.join(missing)}")
    print(f"{', '.join(GUIDE_SKILLS)} name {GUIDE}")


def guide_beside_standard(root: Path) -> int:
    """Each OKF-STANDARD.md under root, or in a zip under it or root itself a zip, has OKF-WRITING-GUIDE.md beside it, byte for byte the
    source; returns how many places carry it."""
    import zipfile

    source = (ROOT / REF / "references" / GUIDE).read_bytes()
    places = 0
    for p in sorted(root.rglob("*")) if root.is_dir() else [root]:
        if p.name == "OKF-STANDARD.md":
            guide = p.with_name(GUIDE)
            expect(guide.is_file() and guide.read_bytes() == source,
                   f"{guide.relative_to(ROOT)}: missing or not byte for byte the source")
            places += 1
        elif p.suffix == ".zip":
            with zipfile.ZipFile(p) as zf:
                names = set(zf.namelist())
                for n in sorted(names):
                    if n.rsplit("/", 1)[-1] == "OKF-STANDARD.md":
                        g = n[:-len("OKF-STANDARD.md")] + GUIDE
                        expect(g in names and zf.read(g) == source,
                               f"{p.relative_to(ROOT)}:{g}: missing or not byte for byte the source")
                        places += 1
    expect(places, f"{root.relative_to(ROOT)} carries no OKF-STANDARD.md")
    return places


def decision_template(tmp: Path) -> None:
    """templates/decision.md filled in as DEC-0001 of a fresh bundle: no placeholder, note or pointer left, its
    frontmatter whole, lint --strict with no finding, and listed under # Decisions of base/decisions/index.md"""
    k = tmp / "decision-template" / "knowledge"
    uv(S / "okf_init.py", "--root", k.parent, *INIT)
    fill = {"nnnn": "0001", "title": "How we work", "one_sentence_description": "The team works in pairs.",
            "tags": "team", "actor": "human:test", "now": "2026-11-14T00:00:00Z"}
    filled = re.sub(r"\{\{(.*?)\}\}", lambda m: fill.get(m.group(1), "Text."), text(REF / "templates" / "decision.md"))
    expect("{{" not in filled, f"decision.md filled in still holds a placeholder:\n{filled}")
    left = [n for n in [*DECISION_NOTES.values(), GUIDE_POINTER.strip("{}")] if n in filled]
    expect(not left, f"decision.md filled in still holds the text of {left}")
    rel = "base/decisions/DEC-0001-how-we-work.md"
    (k / rel).write_text(filled.replace(": ...", ": none."), encoding="utf-8")
    fm = yaml.safe_load(filled.split("---\n")[1])
    fm["generated"]["at"] = str(fm["generated"]["at"])
    want = {"type": "Decision", "title": "DEC-0001: How we work", "description": "The team works in pairs.",
            "tags": ["decision", "team"], "status": "draft", "decision_id": "DEC-0001", "decision_status": "proposed",
            "supersedes": None, "superseded_by": None,
            "generated": {"by": "human:test", "at": "2026-11-14 00:00:00+00:00"}, "sources": []}
    expect(fm == want, f"decision.md filled in gives the frontmatter {fm}")
    uv(S / "okf_index.py", k)
    report = json.loads(uv(S / "okf_lint.py", k, "--strict", "--json", ok=(0, 1)))
    expect(report["findings"] == [], json.dumps(report["findings"], indent=2))
    index = (k / "base" / "decisions" / "index.md").read_text(encoding="utf-8")
    listed = ("# Decisions\n\n* [DEC-0001: How we work](DEC-0001-how-we-work.md) - The team works in pairs. "
              "_(draft)_\n")
    expect(listed in index, f"base/decisions/index.md does not list the decision under # Decisions:\n{index}")
    print("decision.md filled in: decision_id DEC-0001, lint --strict finds nothing, listed under # Decisions")


def init_01(tmp: Path) -> None:
    """init 0.1, then lint --strict"""
    root = tmp / "init-0.1"
    uv(S / "okf_init.py", "--root", root, *INIT, "--okf-version", "0.1")
    lint(root / "knowledge", "--strict")


def google_fixtures(tmp: Path) -> None:
    """Google's fixtures v0.1 and v0.2 pass spec-only lint --strict"""
    for fixture in ("google-crypto-bitcoin-v0.1", "google-acme-retail-v0.2"):
        lint(FIXTURES / fixture, "--no-profile", "--strict")


def migration(tmp: Path) -> None:
    """migration 0.1→0.2, and round trip 0.2→0.1→0.2"""
    m1, m2, m3 = tmp / "m1", tmp / "m2", tmp / "m3"
    uv(S / "okf_migrate.py", FIXTURES / "google-crypto-bitcoin-v0.1", "--to", "0.2", "--out", m1)
    lint(m1, "--no-profile", "--strict")
    expect("**Migration**" in (m1 / "log.md").read_text(encoding="utf-8"), "0.1→0.2 wrote no Migration log entry")
    uv(S / "okf_migrate.py", FIXTURES / "google-acme-retail-v0.2", "--to", "0.1", "--keep-extensions", "--out", m2)
    lint(m2, "--no-profile")
    uv(S / "okf_migrate.py", m2, "--to", "0.2", "--out", m3, "--force")
    lint(m3, "--no-profile", "--strict")


def profile_migration(tmp: Path) -> None:
    """profile migration knowledge/2.0→3.0 of the frozen fixture: 0 errors, and its 5 known warnings
    (BROKEN_LINK and VERIFIED_STALE on ADR-0001, STALE, SECTION_EMPTY x2 on project.md)"""
    p3 = tmp / "p3"
    uv(S / "okf_migrate.py", FIXTURES / "knowledge-2.0", "--profile", "knowledge/3.0", "--out", p3)
    lint(p3, zero_errors=True)
    expect((p3 / "base" / "decisions").is_dir() and not (p3 / "decisions").exists(), "decisions/ not moved under base/")
    expect("knowledge/3.0" in (p3 / "index.md").read_text(encoding="utf-8"), "index.md does not declare knowledge/3.0")
    expect("**Migration**" in (p3 / "log.md").read_text(encoding="utf-8"), "2.0→3.0 wrote no Migration log entry")


def m365(tmp: Path) -> None:
    """M365 export: within the companion limit, okf-capture carrying decision.md and okf-distill pointing to that
    copy, each exported skill self-contained, its okf_migrate.py migrating
    the knowledge/2.0 fixture, its okf_projection.py checking the example bundle's projection, its okf-init
    shipping a running okf_obsidian.py and its okf-lint reporting the fragment and question codes; its okf-review
    carrying the note in place of the review page item, okf_viewer named nowhere in the package, and the export
    stopping on okf_viewer planted"""
    run("python3", "build/export_m365.py")
    init, migrate, lint_skill = M365 / "okf-init" / "scripts", M365 / "okf-migrate" / "scripts", M365 / "okf-lint"
    root = tmp / "m365"
    uv(init / "okf_init.py", "--root", root, *INIT)
    lint(root / "knowledge", "--strict", script=init / "okf_lint.py")
    p3 = tmp / "m365-p3"
    uv(migrate / "okf_migrate.py", FIXTURES / "knowledge-2.0", "--profile", "knowledge/3.0", "--out", p3)
    lint(p3, script=migrate / "okf_lint.py", zero_errors=True)

    sibling = {p.stem for p in (ROOT / S).glob("*.py")}
    for d in sorted((ROOT / M365).glob("*/scripts")):
        for py in sorted(d.glob("*.py")):
            nodes = list(ast.walk(ast.parse(py.read_text(encoding="utf-8"))))
            mods = {n.module for n in nodes if isinstance(n, ast.ImportFrom) and n.module} | {
                a.name for n in nodes if isinstance(n, ast.Import) for a in n.names}
            missing = sorted(m + ".py" for m in mods & sibling if not (d / f"{m}.py").is_file())
            expect(not missing, f"{py.relative_to(ROOT)} imports {', '.join(missing)}, which its skill does not ship")
    uv(M365 / "okf-index" / "scripts" / "okf_index.py", root / "knowledge", "--check")
    print("each exported script ships the scripts it imports; exported okf_index.py checks a fresh bundle")
    for skill in ("okf-capture", "okf-fragment", "okf-distill"):
        expect("scripts/okf_migrate.py" in text(M365 / skill / "SKILL.md")
               and (ROOT / M365 / skill / "scripts" / "okf_migrate.py").is_file(),
               f"{skill}: names okf_migrate.py but does not ship it")
    expect("(okf-projection skill) scripts/okf_projection.py" in text(M365 / "okf-distill" / "SKILL.md")
           and not (ROOT / M365 / "okf-distill" / "scripts" / "okf_projection.py").exists(),
           "okf-distill: does not point to okf-projection's okf_projection.py")
    companions = {skill: len([f for f in (ROOT / M365 / skill).rglob("*") if f.is_file() and f.name != "SKILL.md"])
                  for skill in ("okf-capture", "okf-distill")}
    expect(companions == {"okf-capture": 20, "okf-distill": 20},
           f"companion files {companions}: okf-capture and okf-distill each ship 20")
    expect("`templates/decision.md`" in text(M365 / "okf-capture" / "SKILL.md")
           and (ROOT / M365 / "okf-capture" / "templates" / "decision.md").is_file(),
           "okf-capture: names decision.md but does not ship it")
    expect("`(okf-capture skill) templates/decision.md`" in text(M365 / "okf-distill" / "SKILL.md")
           and not (ROOT / M365 / "okf-distill" / "templates" / "decision.md").exists(),
           "okf-distill: does not point to okf-capture's decision.md")
    print("companion files", companions, "; okf-capture ships decision.md and okf-distill points to it")
    print(guide_beside_standard(ROOT / "dist" / "m365"), f"places in dist/m365 carry {GUIDE} beside OKF-STANDARD.md, "
          "byte for byte the source")
    projection = M365 / "okf-projection" / "scripts" / "okf_projection.py"
    expect((ROOT / projection).is_file(), "okf-projection: does not ship okf_projection.py")
    report = json.loads(uv(projection, EX, "--json"))
    slugs = [p["slug"] for p in report["projections"]]
    expect(slugs == ["onboarding-brief"] and report["findings"] == [], report)
    print("exported okf_projection.py checks", slugs, "with no findings")

    expect("scripts/okf_obsidian.py" in text(M365 / "okf-init" / "SKILL.md")
           and (ROOT / init / "okf_obsidian.py").is_file(), "okf-init: names okf_obsidian.py but does not ship it")
    viewer = tmp / "m365-obsidian"
    shutil.copytree(root / "knowledge", viewer)
    uv(init / "okf_obsidian.py", viewer)
    for f in (".obsidian/app.json", ".obsidian/.gitignore", "knowledge.base"):
        expect((viewer / f).is_file(), f"exported okf_obsidian.py did not write {f}")
    print("exported okf_obsidian.py writes the viewer setup")

    q = tmp / "m365-questions"
    shutil.copytree(root / "knowledge", q)
    gen = "generated: { by: human:test, at: 2026-11-02T00:00:00Z }\n"
    (q / "fragments" / "2026-11-02-meeting.md").write_text(
        "---\ntype: Knowledge Fragment\ntitle: M\ndescription: M.\nparticipants: [Alice]\n"
        f"distillation_status: done\n{gen}---\n\n# Record\n\nText.\n", encoding="utf-8")
    for slug, title, status, body in (("who", "Q", "closed", "Who?"), ("whom", "A", "answered", "Whom?")):
        (q / "base" / "questions" / f"{slug}.md").write_text(
            f"---\ntype: Open Question\ntitle: {title}\ndescription: {title}.\nowner: human:test\n"
            f"question_status: {status}\nasked_in: /fragments/2026-11-02-meeting.md\n{gen}---\n\n"
            f"# Question\n\n{body}\n", encoding="utf-8")
    found = {f["code"] for f in json.loads(uv(lint_skill / "scripts" / "okf_lint.py", q, "--json", ok=(0, 1)))["findings"]}
    wanted = {"FRAGMENT_NO_FIELD", "BAD_ACTOR", "BAD_DISTILLATION_STATUS", "BAD_QUESTION_STATUS", "QUESTION_NO_ANSWER"}
    expect(wanted <= found, f"exported okf-lint missed {sorted(wanted - found)}")
    print("exported okf-lint reports", ", ".join(sorted(wanted)))

    sys.path.insert(0, str(ROOT / "build"))
    import export_m365

    expect(export_m365.M365_NO_CLOSING == M365_NO_CLOSING, f"M365_NO_CLOSING is {export_m365.M365_NO_CLOSING!r}")
    shipped = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "dist" / "m365").rglob("okf_close.py"))
    expect(not shipped, f"okf_close.py reaches the M365 package: {shipped}")
    distill = text(M365 / "okf-distill" / "SKILL.md")
    at = distill.find("\n## Closing mode\n") + 1
    expect(at > 0, "the exported okf-distill has no Closing mode note")
    end = distill.find("\n## ", at)
    section = distill[at:end + 1 if end >= 0 else len(distill)]
    expect(section.rstrip() + "\n" == M365_NO_CLOSING, f"the exported Closing mode is {section!r}")
    rest = distill[:at] + distill[at + len(section):]
    for leak in ("okf_close", "## Closing mode", export_m365.CLOSING_ROUTING.strip()):
        expect(leak not in rest, f"the exported okf-distill still holds {leak!r} outside its note")

    def description(md: str) -> str:
        return yaml.safe_load(md.split("---\n")[1])["description"]

    source = description(text(PLUGIN / "skills" / "okf-distill" / "SKILL.md"))
    expect(export_m365.CLOSING_DESCRIPTION in source, "the source okf-distill description has no closing sentence")
    expect(description(distill) == source.replace(export_m365.CLOSING_DESCRIPTION, ""),
           f"the exported okf-distill description is {description(distill)!r}")
    print("exported okf-distill: no okf_close.py, its Closing mode replaced by the note, its description without closing")

    expect(export_m365.M365_NO_VIEWER == M365_NO_VIEWER, f"M365_NO_VIEWER is {export_m365.M365_NO_VIEWER!r}")
    _review_note(M365 / "okf-review" / "SKILL.md", M365_NO_VIEWER)
    leaks = names_viewer(ROOT / "dist" / "m365")
    expect(not leaks, f"dist/m365 names okf_viewer: {leaks}")
    expect(export_m365.AGENT_VIEWER in text(PLUGIN / "agents" / "knowledge-architect.md"),
           "the source agent does not name the Knowledge Viewer's script in the part the M365 package removes")
    agent_md = PLUGIN / "agents" / "knowledge-architect.md"
    planted_agent = tmp / "planted-agent.md"
    planted_agent.write_text(text(agent_md).replace("# Limits\n", "# Limits\n\nRun okf_viewer.py.\n"), encoding="utf-8")
    for where, plant in _viewer_plants():
        _expect_refused(export_m365, tmp, f"m365-{where}", plant)
    _expect_refused(export_m365, tmp, "m365-agent", lambda plugin: None, agent=planted_agent)
    print("exported okf-review: its review page item replaced by the note; dist/m365 names okf_viewer nowhere, and "
          "the export stops on okf_viewer planted in a skill, in okf-review outside that item or in the agent")


# The notes that replace okf-review step 11's review page item in the M365 package and the Copilot pack, exactly
M365_NO_VIEWER = ("    - **A review page private to the person**: the Knowledge Viewer, the review page this channel uses, "
                  "is not available in Microsoft 365 Copilot: this package does not ship the script that builds and "
                  "checks it. Record the person's verification through a structured question, the channel above, or "
                  "run the round from Claude Code.\n")
COPILOT_NO_VIEWER = ("    - **A review page private to the person**: the Knowledge Viewer, the review page this channel "
                     "uses, is not available in this GitHub Copilot pack: the pack does not ship the script that builds "
                     "and checks it. Record the person's verification through a structured question, the channel above, "
                     "or run the round from Claude Code.\n")


def names_viewer(root: Path) -> list[str]:
    """The files under root (or root, a file), and the members of the zips among them, that name okf_viewer."""
    import zipfile

    found = []
    for p in sorted(root.rglob("*")) if root.is_dir() else [root]:
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix() if root.is_dir() else p.name
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as zf:
                found += [f"{rel}:{n}" for n in zf.namelist() if b"okf_viewer" in zf.read(n)]
        elif b"okf_viewer" in p.read_bytes():
            found.append(rel)
    return found


def _review_note(skill_md: Path, note: str) -> None:
    """The exported okf-review carries the note, once, where the review page item stood: after the structured question
    and before the closing bullets of step 11."""
    review = text(skill_md)
    expect(review.count("**A review page private to the person**") == 1 and
           f"`generated.at`.\n{note}    - If neither channel is available" in review,
           f"{skill_md}: step 11 does not carry the note in place of the review page item")


def _viewer_plants():
    """Each plant of okf_viewer outside the part the exporters replace, on a copy of the plugin."""
    def other_skill(plugin: Path) -> None:
        md = plugin / "skills" / "okf-lint" / "SKILL.md"
        md.write_text(md.read_text(encoding="utf-8") + "\nRun okf_viewer.py.\n", encoding="utf-8")

    def review_outside(plugin: Path) -> None:
        md = plugin / "skills" / "okf-review" / "SKILL.md"
        src = md.read_text(encoding="utf-8")
        step = "12. **Index and validate** after any change:"
        expect(step in src, "okf-review has no step 12 to plant okf_viewer in")
        md.write_text(src.replace(step, step[:-1] + " (okf_viewer.py builds nothing here):"), encoding="utf-8")

    return (("skill", other_skill), ("review", review_outside))


def _expect_refused(exporter, tmp: Path, name: str, plant, agent: Path | None = None) -> None:
    """The exporter, run on a copy of the plugin with okf_viewer planted, stops the build naming okf_viewer."""
    import contextlib

    plugin = tmp / f"plugin-{name}"
    shutil.copytree(ROOT / PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__"))
    plant(plugin)
    saved = exporter.PLUGIN, getattr(exporter, "AGENT_SRC", None)
    exporter.PLUGIN = plugin
    if agent is not None:
        exporter.AGENT_SRC = agent
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exporter.main(["--out", str(tmp / f"out-{name}")])
    except SystemExit as e:
        expect("okf_viewer" in str(e.code), f"{name}: the export stopped for another reason: {e.code}")
    else:
        raise Fail(f"{exporter.__name__} exported okf_viewer planted ({name}) without stopping")
    finally:
        exporter.PLUGIN = saved[0]
        if agent is not None:
            exporter.AGENT_SRC = saved[1]


def copilot(tmp: Path) -> None:
    """Copilot pack: every skill exported with its SKILL.md and the @okf agent naming each one; each SKILL.md's
    frontmatter valid, its description within the limits and in the third person; okf-review's review page item
    replaced by the note, okf_viewer named nowhere in the pack, and the export stopping on okf_viewer planted"""
    run("python3", "build/export_copilot.py", "--zip")
    pack = ROOT / "dist" / "copilot"
    sys.path.insert(0, str(ROOT / "build"))
    import export_copilot

    expect(export_copilot.COPILOT_NO_VIEWER == COPILOT_NO_VIEWER,
           f"COPILOT_NO_VIEWER is {export_copilot.COPILOT_NO_VIEWER!r}")
    _review_note(Path("dist/copilot/.github/skills/okf-review/SKILL.md"), COPILOT_NO_VIEWER)
    for where in (pack, ROOT / "dist" / "okf-copilot-pack.zip"):
        leaks = names_viewer(where)
        expect(not leaks, f"{where.relative_to(ROOT)} names okf_viewer: {leaks}")
    for where, plant in _viewer_plants():
        _expect_refused(export_copilot, tmp, f"copilot-{where}", plant)
    print("exported okf-review: its review page item replaced by the note; the Copilot pack names okf_viewer "
          "nowhere, and the export stops on okf_viewer planted in a skill or in okf-review outside that item")
    src = sorted(p.parent.name for p in (ROOT / PLUGIN / "skills").glob("*/SKILL.md"))
    out = sorted(p.parent.name for p in (pack / ".github" / "skills").glob("*/SKILL.md"))
    expect(out == src, f"exported skills differ: source {src}, pack {out}")
    agent = (pack / ".github" / "agents" / "okf.agent.md").read_text(encoding="utf-8")
    missing = [s for s in src if s not in agent]
    expect(not missing, "okf.agent.md does not name: " + ", ".join(missing))
    expect((pack / "AGENTS.okf.md").is_file(), "the pack has no AGENTS.okf.md")
    print("copilot pack:", len(out), "skills, all named by the @okf agent")
    for where in (pack, ROOT / "dist" / "okf-copilot-pack.zip"):
        carried = guide_beside_standard(where)
        print(f"{where.relative_to(ROOT)}: {carried} place(s) carry {GUIDE} beside OKF-STANDARD.md, byte for byte the source")
    for skills in (PLUGIN / "skills", Path("dist/copilot/.github/skills")):
        print(last_line(uv(Path("build/check_skills.py"), skills)))


def builtin_profile(tmp: Path) -> None:
    """the built-in Domain Profile matches §4 of the standard and is inlined byte for byte in each exported
    okf_profile.py (reads the m365 step's output)"""
    print(last_line(uv(S / "okf_profile.py", "--check-builtin", REF / "references" / "OKF-STANDARD.md")))
    src = (ROOT / REF / "profiles" / "knowledge-3.0.md").read_bytes()
    exported = sorted((ROOT / "dist" / "m365").glob("*/skills/*/scripts/okf_profile.py"))
    expect(exported, "no exported okf_profile.py: run the m365 step first")

    def inlined(path: Path) -> list[bytes]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return [n.value.value.encode("utf-8") for n in tree.body
                if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == "BUILTIN_TEXT"
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)]

    differ = [str(p.relative_to(ROOT)) for p in exported if inlined(p) != [src]]
    expect(not differ, "inlined built-in profile differs from the source: " + ", ".join(differ))
    print(len(exported), "exported okf_profile.py inline the built-in profile byte for byte")


def copies(tmp: Path) -> None:
    """build/copies.py writes standard/OKF-WRITING-GUIDE.md equal to its source, and the committed root standard/
    and templates/ match the ones it writes"""
    out = tmp / "copies"
    run("python3", "build/copies.py", out)
    guide = out / "standard" / GUIDE
    expect(guide.is_file() and guide.read_bytes() == (ROOT / REF / "references" / GUIDE).read_bytes(),
           f"build/copies.py does not write standard/{GUIDE} equal to its source")
    try:
        for sub in ("standard", "templates"):
            run("diff", "-rq", sub, out / sub)
    except Fail as e:
        raise Fail(f"root copies are stale: run just copies\n{e}") from None
    print("root standard/ and templates/ match their source")


def m365_agent(tmp: Path) -> None:
    """the M365 agent within its limits and matching build/m365-agent.json (reads the m365 step's output)"""
    expect((ROOT / "dist" / "m365" / "okf-knowledge-architect-m365.zip").is_file(), "no M365 agent zip")
    agent = json.loads(text(Path("dist/m365/agent-package/declarativeAgent.json")))
    config = json.loads(text(Path("build/m365-agent.json")))
    expect(len(agent["instructions"]) <= 8000 and len(agent["agent_skills"]) <= 8, f"{agent['name']}: over the limits")
    expect([s["folder"] for s in agent["agent_skills"]] == ["./skills/" + k for k in config["agent_skills"]],
           "agent_skills differ from build/m365-agent.json")
    print("agent", len(agent["instructions"]), "chars,", len(agent["agent_skills"]), "M365 skills")


def bundles(tmp: Path) -> None:
    """this repo's bundles are on knowledge/3.0; the 2.0 fixture equals examples/knowledge at 00e510e, before
    its migration"""
    for bundle in (Path("knowledge"), EX):
        expect(not json.loads(uv(S / "okf_lint.py", bundle, "--json"))["profile_outdated"], f"{bundle}: profile outdated")
    archive = subprocess.run(["git", "archive", "00e510e", str(EX)], cwd=ROOT, capture_output=True, check=True).stdout
    frozen = tmp / "frozen"
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(frozen, filter="data")
        else:
            tar.extractall(frozen)
    run("diff", "-r", frozen / EX, FIXTURES / "knowledge-2.0")
    print("knowledge and examples/knowledge on knowledge/3.0; the 2.0 fixture is frozen")


def index(tmp: Path) -> None:
    """every index.md of knowledge and examples/knowledge is what okf_index.py would write"""
    for bundle in (Path("knowledge"), EX):
        summary = last_line(uv(S / "okf_index.py", bundle, "--check", ok=(0, 1)))
        expect(summary == "0 index.md out of date", f"{bundle}: {summary}")
        print(bundle, summary)


def workflows(tmp: Path) -> None:
    """each workflow in .claude/workflows/ and the knowledge concept naming it in resource link both ways
    (DEC-0003 decision 5); each session's prompt file in build/sessions/ names the other session, DEC-0006 and the
    runbook, only paths that exist, in 25 lines at most (DEC-0006 decisions 1 and 7); just router and just worker
    start claude under the session's name with files that exist and each session's model and effort, and just
    sessions starts both recipes once each with hc run, in the background, without a parent and under those names,
    with the caller's PATH and just's absolute path, and shows each in the Herdr.app space okf-builder in a tab named
    after its recipe; run against stub programs, just sessions tells a missing herdr-app from a closed Herdr.app and
    its last line names only the sessions it placed"""
    found = sorted(p.relative_to(ROOT) for p in (ROOT / ".claude" / "workflows").glob("*.js"))
    expect(found, "no workflow in .claude/workflows")
    resource = re.compile(r"^resource: (/\.claude/workflows/\S+)\s*$", re.M)
    concepts = [(str(p.relative_to(ROOT / "knowledge")), m.group(1))
                for p in sorted((ROOT / "knowledge").rglob("*.md"))
                for m in [resource.search(p.read_text(encoding="utf-8"))] if m]
    bad = [f"{r}: named by {c}, missing" for c, r in concepts if not (ROOT / r[1:]).is_file()]
    bad += [f"{w}: no concept names it in resource" for w in found if not [c for c, r in concepts if r == f"/{w}"]]
    bad += [f"{w}: does not name knowledge/{c}" for w in found for c, r in concepts
            if r == f"/{w}" and f"knowledge/{c}" not in (ROOT / w).read_text(encoding="utf-8")]
    expect(not bad, "; ".join(bad))
    print(len(found), "workflows linked both ways with", len(concepts), "concepts")
    _sessions(tmp)


SESSIONS = {"router": "okf-router-session", "worker": "okf-worker-session"}
METHOD = ("knowledge/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md", "knowledge/base/runbooks/build-in-layers.md")
SESSION_LINES = 25
ROUTER_SETTINGS = "build/sessions/router.settings.json"
ROUTER_DENY = "Edit(./**)"
SESSION_MODEL = {"router": ("claude-fable-5-2", "low"), "worker": ("claude-opus-5-5", "medium")}


def _in_repo(name: str) -> bool:
    path = (ROOT / name.lstrip("/")).resolve()
    return path.exists() and path.is_relative_to(ROOT)


def _sessions(tmp: Path) -> None:
    """A repository path in a prompt file is any run of path characters holding a slash, in backticks or not."""
    bad = []
    for recipe, session in SESSIONS.items():
        prompt = f"build/sessions/{recipe}.md"
        dry = subprocess.run(["just", "--dry-run", recipe, "--resume"], cwd=ROOT, capture_output=True, text=True)
        expect(dry.returncode == 0, f"just --dry-run {recipe} exited {dry.returncode}\n{dry.stderr.strip()}")
        words = dry.stderr.split()
        flags = dict(zip(words, words[1:]))
        if words[:1] != ["claude"] or flags.get("-n") != session:
            bad.append(f"just {recipe}: does not start claude -n {session}")
        model, effort = SESSION_MODEL[recipe]
        if (flags.get("--model"), flags.get("--effort")) != (model, effort):
            bad.append(f"just {recipe}: passes --model {flags.get('--model')} --effort {flags.get('--effort')}, "
                       f"not --model {model} --effort {effort}")
        if words[-1:] != ["--resume"]:
            bad.append(f"just {recipe}: its arguments do not reach claude")
        passed = {"--append-system-prompt-file": prompt}
        if recipe == "router":
            passed["--settings"] = ROUTER_SETTINGS
        for flag, file in passed.items():
            named = flags.get(flag)
            if named != file:
                bad.append(f"just {recipe}: {flag} names {named}, not {file}")
            if named and not (ROOT / named).is_file():
                bad.append(f"just {recipe}: names {named}, missing")
        if not (ROOT / prompt).is_file():
            bad.append(f"{prompt}: missing")
            continue
        body = (ROOT / prompt).read_text(encoding="utf-8")
        lines = len(body.splitlines())
        if lines > SESSION_LINES:
            bad.append(f"{prompt}: {lines} lines, over {SESSION_LINES}")
        if session not in body:
            bad.append(f"{prompt}: does not name its own session {session}")
        bad += [f"{prompt}: does not name the other session {other}" for other in SESSIONS.values()
                if other != session and other not in body]
        bad += [f"{prompt}: does not name {m}" for m in METHOD if m not in body]
        paths = sorted({m.rstrip(".") for m in re.findall(r"[\w.~-]*(?:/[\w.~-]*)+", body)})
        bad += [f"{prompt}: names {p}, missing from the repository" for p in paths if not _in_repo(p)]
    settings = ROOT / ROUTER_SETTINGS
    if settings.is_file():
        deny = json.loads(settings.read_text(encoding="utf-8")).get("permissions", {}).get("deny", [])
        if ROUTER_DENY not in deny:
            bad.append(f"{ROUTER_SETTINGS}: does not deny {ROUTER_DENY}")
    bad += _hc_sessions()
    bad += _sessions_run(tmp)
    expect(not bad, "; ".join(bad))
    print(len(SESSIONS), "session prompt files name each other and paths that exist; just", " and just ".join(SESSIONS),
          "pass them, the router's with a settings file that denies", ROUTER_DENY)
    print("; ".join(f"just {recipe} passes --model {model} --effort {effort}" for recipe, (model, effort) in SESSION_MODEL.items()))
    print("just sessions starts just", " and just ".join(SESSIONS), "once each with hc run --bg --no-parent, named",
          " and ".join(SESSIONS.values()) + ", through", " ".join(HC_ENV), "and just's absolute path")
    print("just sessions shows both in the Herdr.app space", SPACE + ", in the tabs", " and ".join(SESSIONS))
    print("just sessions, run against stub hc, claude, herdr-app and sleep in", len(SESSIONS_ROWS),
          "cases, gives each case's stdout, stderr and exit code exactly, calls hc label and herdr-app do with exactly "
          "the expected arguments and never calls hc run")


HC_ENV = ["/usr/bin/env", "PATH=$PATH"]
SPACE = "okf-builder"
HERDR_APP_STEPS = {
    rf"herdr-app do space\.new --name {SPACE}\b": f"create the Herdr.app space {SPACE} when it is missing",
    r'hc label "\$1" herdr\.space="\$space"': "label each session's terminal with herdr.space",
    r"herdr-app do tab\.rename\b": "name each session's tab",
    rf"\bplace {SESSIONS['router']} router\b": "place okf-router-session in the tab router",
    rf"\bplace {SESSIONS['worker']} worker\b": "place okf-worker-session in the tab worker",
}


def _hc_sessions() -> list[str]:
    """Read from just --dry-run sessions, which prints the recipe and runs nothing: hc is neither needed nor called.
    hc looks a program up on its server's PATH, so each terminal is given env by its absolute path, the caller's
    PATH and just by its absolute path; the recipe refuses to start when claude is not on that PATH."""
    dry = subprocess.run(["just", "--dry-run", "sessions"], cwd=ROOT, capture_output=True, text=True)
    expect(dry.returncode == 0, f"just --dry-run sessions exited {dry.returncode}\n{dry.stderr.strip()}")
    started, bad = [], []
    for line in re.findall(r"^\s*(hc run\b.*)$", dry.stderr, re.M):
        words = [w for w in shlex.split(line) if not w.startswith(">")]
        at = 2
        while at < len(words) and words[at].startswith("--"):
            at += 2 if words[at] in ("--name", "--cwd") else 1
        options, argv = words[:at], words[at:]
        flags = dict(zip(options, options[1:]))
        program = Path(argv[2]) if len(argv) == 4 else Path()
        resolvable = argv[:2] == HC_ENV and program.is_absolute() and program.name == "just" and program.is_file()
        command = f"just {argv[3]}" if resolvable else " ".join(argv)
        started.append((flags.get("--name"), command))
        if not resolvable:
            bad.append(f"just sessions: hc run for {flags.get('--name')} starts {command or 'no command'}, not "
                       f"{' '.join(HC_ENV)} and just by its absolute path: hc looks a program up on its server's PATH")
        bad += [f"just sessions: hc run for {command or 'no command'} lacks {flag}" for flag in ("--bg", "--no-parent")
                if flag not in options]
        if Path(flags.get("--cwd", "")).resolve() != ROOT.resolve():
            bad.append(f"just sessions: hc run for {command or 'no command'} has --cwd {flags.get('--cwd')}, not the repository root")
    expected = sorted((session, f"just {recipe}") for recipe, session in SESSIONS.items())
    if sorted(started, key=str) != expected:
        bad.append(f"just sessions: hc run starts {started}, not {expected} once each")
    if not re.search(r"^\s*if ! command -v claude\b", dry.stderr, re.M):
        bad.append("just sessions: does not refuse to start when claude is not on the PATH it hands to hc")
    if re.search(r"\bherdr (?:workspace|tab|pane)\b", dry.stderr):
        bad.append("just sessions: still drives herdr 0.9")
    for step, text in HERDR_APP_STEPS.items():
        if not re.search(step, dry.stderr):
            bad.append(f"just sessions: does not {text}")
    return bad


ALREADY = [f"sessions: {s} is already running" for s in SESSIONS.values()]
UNPLACED = {s: f"sessions: {s} is not in the Herdr.app space {SPACE}; reach it with hc attach {s}" for s in SESSIONS.values()}
ATTACH = " and ".join(f"hc attach {s}" for s in SESSIONS.values())
# Each case: whether herdr-app is on PATH, whether its ls succeeds, whether the space okf-builder exists, the sessions
# whose tab is in it, then the rest of stdout and the whole of stderr
SESSIONS_ROWS = {
    "herdr-app not on PATH": (False, False, False, (), [
        f"sessions: herdr-app is not on PATH, so the sessions were not placed in the Herdr.app space {SPACE}; "
        f"reach them with {ATTACH}"], []),
    "herdr-app ls fails": (True, False, False, (), [
        f"sessions: Herdr.app is not open, so neither session is in its window; reach them with {ATTACH}"], []),
    "both placed": (True, True, False, ("okf-router-session", "okf-worker-session"), [
        f"sessions: both are in the Herdr.app space {SPACE}, in the tabs router and worker"], []),
    "both placed, the space exists": (True, True, True, ("okf-router-session", "okf-worker-session"), [
        f"sessions: both are in the Herdr.app space {SPACE}, in the tabs router and worker"], []),
    "only okf-router-session placed": (True, True, True, ("okf-router-session",), [
        f"sessions: okf-router-session is in the Herdr.app space {SPACE}, in the tab router"],
        [UNPLACED["okf-worker-session"]]),
    "only okf-worker-session placed": (True, True, True, ("okf-worker-session",), [
        f"sessions: okf-worker-session is in the Herdr.app space {SPACE}, in the tab worker"],
        [UNPLACED["okf-router-session"]]),
    "neither placed": (True, True, True, (), [], [UNPLACED["okf-router-session"], UNPLACED["okf-worker-session"]]),
}
STUB_HC = """case "$1" in
    server|label|run) exit 0 ;;
    get) printf '{"name": "%s", "state": "live", "address": "terminal-%s"}\\n' "$3" "$3" ;;
    *) exit 1 ;;
esac
"""
STUB_SPACE = "space-1"
STUB_PLACEHOLDER = "placeholder-1"
LABELS = [f"label {s} herdr.space={STUB_SPACE}" for s in SESSIONS.values()]
RENAME = {s: f"do tab.rename --id tab-{s} --name {tab}" for tab, s in SESSIONS.items()}
# Each case's calls to hc label and to herdr-app do, in order
SESSIONS_CALLS = {
    "herdr-app not on PATH": ([], []),
    "herdr-app ls fails": ([], []),
    "both placed": (LABELS, [
        f"do space.new --name {SPACE} --folder {ROOT} --tab placeholder --focus false",
        RENAME["okf-router-session"], RENAME["okf-worker-session"],
        f"do tab.close --id {STUB_PLACEHOLDER} --confirmed true"]),
    "both placed, the space exists": (LABELS, [RENAME["okf-router-session"], RENAME["okf-worker-session"]]),
    "only okf-router-session placed": (LABELS, [RENAME["okf-router-session"]]),
    "only okf-worker-session placed": (LABELS, [RENAME["okf-worker-session"]]),
    "neither placed": (LABELS, []),
}


def _stub(path: Path, bash: str, body: str) -> None:
    """A bash script that records its arguments in calls.<name> beside it, using only bash's builtins"""
    calls = path.parent / f"calls.{path.name}"
    path.write_text(f"#!{bash}\nprintf '%s\\n' \"$*\" >> {shlex.quote(str(calls))}\n{body}", encoding="utf-8")
    path.chmod(0o755)


def _stub_path(stubs: Path) -> str:
    """The stub directory first, then the directories of bash, grep and seq, none of them ~/.local/bin or a directory
    that holds an hc or a herdr-app"""
    dirs = [str(stubs)]
    for program in ("bash", "grep", "seq"):
        found = shutil.which(program)
        expect(found, f"just sessions run: {program} is not on PATH")
        folder = Path(found).parent
        expect(folder != Path.home() / ".local" / "bin" and not any((folder / p).exists() for p in ("hc", "herdr-app")),
               f"just sessions run: {program} lives in {folder}, beside an hc or a herdr-app")
        if str(folder) not in dirs:
            dirs.append(str(folder))
    return ":".join(dirs)


def _calls(path: Path) -> list[str]:
    """The calls a stub recorded, one per line, or none when it was never called"""
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def _sessions_run(tmp: Path) -> list[str]:
    """Runs the real recipe, just sessions, once per case of SESSIONS_ROWS, against stubs under tmp. Before each run,
    hc must resolve to its stub and herdr-app to its stub or to nothing on the run's PATH, or the check fails without
    running the recipe: the real hc and herdr-app are never called."""
    just, bash = shutil.which("just"), shutil.which("bash")
    expect(just and bash, "just sessions run: just or bash is not on PATH")
    bad = []
    for n, (case, (app, opens, space_exists, placed, rest, stderr)) in enumerate(SESSIONS_ROWS.items(), 1):
        stubs = tmp / "sessions-run" / str(n)
        stubs.mkdir(parents=True)
        _stub(stubs / "hc", bash, STUB_HC)
        _stub(stubs / "claude", bash, "exit 0\n")
        _stub(stubs / "sleep", bash, "exit 0\n")
        (stubs / "python3").symlink_to(sys.executable)
        if app:
            tabs = [{"id": f"tab-{s}", "terminals": [{"terminal": f"terminal-{s}"}]} for s in placed]
            spaces = [{"id": STUB_SPACE, "name": SPACE if space_exists else "other", "tabs": tabs}]
            (stubs / "ls.json").write_text(json.dumps({"spaces": spaces}), encoding="utf-8")
            answer = f"printf '%s\\n' \"$(<{shlex.quote(str(stubs / 'ls.json'))})\"" if opens else "exit 1"
            _stub(stubs / "herdr-app", bash, f"""case "$1 ${{2:-}}" in
    "ls ") {answer} ;;
    "do space.new") printf '{{"space": "{STUB_SPACE}", "tab": "{STUB_PLACEHOLDER}"}}\\n' ;;
    "do tab.rename"|"do tab.close") exit 0 ;;
    *) exit 1 ;;
esac
""")
        path = _stub_path(stubs)
        hc = shutil.which("hc", path=path)
        expect(hc == str(stubs / "hc"), f"just sessions run, {case}: hc resolves to {hc}, not the stub, on {path}")
        found = shutil.which("herdr-app", path=path)
        expect(found == (str(stubs / "herdr-app") if app else None),
               f"just sessions run, {case}: herdr-app resolves to {found} on {path}")
        proc = subprocess.run([just, "sessions"], cwd=ROOT, capture_output=True, text=True,
                              env={"PATH": path, "HOME": str(stubs), "TMPDIR": str(stubs)})
        got = (proc.returncode, proc.stdout, proc.stderr)
        want = (0, "".join(f"{line}\n" for line in ALREADY + rest), "".join(f"{line}\n" for line in stderr))
        if got != want:
            bad.append(f"just sessions, {case}: gives exit code, stdout and stderr {got!r}, not {want!r}")
        hc_calls, app_calls = _calls(stubs / "calls.hc"), _calls(stubs / "calls.herdr-app")
        bad += [f"just sessions, {case}: called hc {c}" for c in hc_calls if c.split()[:1] == ["run"]]
        labels, dos = SESSIONS_CALLS[case]
        got_labels = [c for c in hc_calls if c.split()[:1] == ["label"]]
        if got_labels != labels:
            bad.append(f"just sessions, {case}: calls hc {got_labels}, not {labels}")
        got_dos = [c for c in app_calls if c.split()[:1] == ["do"]]
        if got_dos != dos:
            bad.append(f"just sessions, {case}: calls herdr-app {got_dos}, not {dos}")
    return bad


def obsidian_setup(tmp: Path) -> None:
    """this repo's committed Obsidian setup equals okf_obsidian.py's output for the bundle with its Domain Profile
    (ADR-0032 decision 5)"""
    viewer = tmp / "obsidian"
    shutil.copytree(ROOT / "knowledge", viewer, symlinks=True)
    shutil.rmtree(viewer / ".obsidian", ignore_errors=True)
    (viewer / "knowledge.base").unlink(missing_ok=True)
    uv(S / "okf_obsidian.py", viewer)
    for f in (".obsidian/app.json", ".obsidian/.gitignore", "knowledge.base"):
        expect((ROOT / "knowledge" / f).read_bytes() == (viewer / f).read_bytes(),
               f"knowledge/{f} differs from okf_obsidian.py's output: run just obsidian --force")
    print("knowledge/ viewer setup matches okf_obsidian.py")


def _viewer_file(name: str) -> bool:
    return name.endswith("okf_viewer.py") or "okf-standard/viewer/" in name


def viewer_files(root: Path) -> list[str]:
    """The Knowledge Viewer's files under root, inside its zips too: okf_viewer.py and okf-standard/viewer/."""
    import zipfile

    found = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and _viewer_file(p.relative_to(root).as_posix())]
    for z in root.rglob("*.zip"):
        with zipfile.ZipFile(z) as zf:
            found += [f"{z.relative_to(root).as_posix()}:{n}" for n in zf.namelist() if _viewer_file(n)]
    return sorted(found)


def viewer(tmp: Path) -> None:
    """okf_viewer.py builds the page of this repository's knowledge/ and of the example bundle, its template byte for byte and one concept per file lint reads;
    the Claude plugin ships the script and the template, the Microsoft 365 package and the Copilot pack leave both out,
    and the check finds either one planted back (ADR-0042 decision 6); okf-review runs a round with it inside one
    review page item; just viewer rewrites dist/viewer/ on a second run"""
    import zipfile

    sys.path.insert(0, str(ROOT / S))
    from okf_common import scan_bundle
    from okf_lint import find_tree, profile_structure, Report
    from okf_profile import concept_type, resolve_aliases

    head = run("git", "rev-parse", "HEAD").strip()
    template = ROOT / REF / "viewer" / "index.html"
    for bundle in (Path("knowledge"), EX):
        out = tmp / "viewer" / bundle.as_posix().replace("/", "-")
        uv(S / "okf_viewer.py", bundle, "--out", out)
        expect((out / "index.html").read_bytes() == template.read_bytes(), "the built index.html differs from the template")
        data = json.loads((out / "concepts.json").read_text(encoding="utf-8"))
        built = [c["path"] for c in data["concepts"]]
        sc = scan_bundle(ROOT / bundle)
        tree = find_tree(ROOT / bundle, Report())
        prof = profile_structure(ROOT / bundle, sc.docs, tree.domain if tree is not None else None)[0]
        docs = sorted("/" + d.rel for d in sc.docs
                      if d.path.name not in ("index.md", "log.md") and isinstance(d.frontmatter, dict) and d.has_fm_block
                      and concept_type(None, resolve_aliases(prof, d.frontmatter)) != "Conflict Log")
        expect(built == docs, f"{bundle}: concepts.json lists {len(built)} concepts, lint reads {len(docs)}")
        dirty = bool(run("git", "status", "--porcelain", "--", bundle).strip())
        expect((data["commit"], data["dirty"]) == (head, dirty),
               f"{bundle}: concepts.json names {data['commit']} dirty {data['dirty']}, git {head} dirty {dirty}")
        print(f"{bundle}: {len(built)} concepts, commit {head[:7]}{' (dirty)' if dirty else ''}")

    run("just", "plugin")
    with zipfile.ZipFile(ROOT / "okf-builder.plugin") as zf:
        names = set(zf.namelist())
    for want in ("skills/okf-standard/scripts/okf_viewer.py", "skills/okf-standard/viewer/index.html"):
        expect(want in names, f"okf-builder.plugin does not hold {want}")
    run("python3", "build/export_m365.py")
    run("python3", "build/export_copilot.py", "--zip")
    for pkg in (ROOT / "dist" / "m365", ROOT / "dist" / "copilot", ROOT / "dist" / "okf-copilot-pack.zip"):
        if pkg.is_file():
            with zipfile.ZipFile(pkg) as zf:
                leaks = [n for n in zf.namelist() if _viewer_file(n)]
        else:
            leaks = viewer_files(pkg)
        expect(not leaks, f"the Knowledge Viewer reaches {pkg.relative_to(ROOT)}: {leaks}")
    planted = tmp / "planted"
    shutil.copytree(ROOT / "dist" / "copilot", planted)
    (planted / ".github" / "skills" / "okf-standard" / "viewer").mkdir()
    (planted / ".github" / "skills" / "okf-standard" / "viewer" / "index.html").write_text("x", encoding="utf-8")
    (planted / "okf_viewer.py").write_text("x", encoding="utf-8")
    expect(viewer_files(planted) == [".github/skills/okf-standard/viewer/index.html", "okf_viewer.py"],
           f"the packaging check misses a planted viewer file: {viewer_files(planted)}")
    print("okf-builder.plugin ships okf_viewer.py and viewer/index.html; dist/m365 and the Copilot pack hold neither")

    sys.path.insert(0, str(ROOT / "build"))
    import export_m365

    review = text(PLUGIN / "skills" / "okf-review" / "SKILL.md")
    items = export_m365.VIEWER_RE.findall(review)
    expect(len(items) == 1, f"okf-review holds {len(items)} review page items, not one")
    for cmd in ('okf_viewer.py" <bundle> --out ', 'okf_viewer.py" <bundle> --answers '):
        expect(cmd in items[0], f"okf-review's review page item does not run {cmd!r}")
    expect("okf_viewer" not in export_m365.VIEWER_RE.sub("", review), "okf-review names okf_viewer outside its item")
    print("okf-review step 11 builds and checks the page with okf_viewer.py, inside its one review page item")

    concepts = ROOT / "dist" / "viewer" / "concepts.json"
    run("just", "viewer")
    second = run("just", "viewer")
    expect(f"rewritten {concepts}" in second.splitlines(), f"a second just viewer did not rewrite {concepts}:\n{second}")
    print("just viewer run twice rewrites dist/viewer/concepts.json the second time")


def dogfood(tmp: Path) -> None:
    """dogfood state of examples/knowledge: only its 3 known warnings; every fragment is a Knowledge Fragment
    with a distillation_status, aliases resolved; the mapped question Runbook.owner has exactly one gap; its one
    projection, onboarding-brief, has no findings; its two Request instances, req-0001 open and req-0002 closed,
    with the traces of the closing in the parent; the audit finds nothing, and an edit planted after closed_at is
    its one EDITED_AFTER_CLOSE; req-0002 reopened on a copy and closed again by okf_close.py gives the example
    byte for byte; okf-review names EDITED_AFTER_CLOSE"""
    report = json.loads(uv(S / "okf_lint.py", EX, "--json"))
    codes = sorted(f["code"] for f in report["findings"])
    expect(codes == ["BROKEN_LINK", "STALE", "VERIFIED_STALE"], codes)
    print("lint codes", codes)
    instances = [{"path": "requests/req-0001/", "kind": "Request", "state": "open", "concepts": 1, "errors": 0,
                  "warnings": 0},
                 {"path": "requests/req-0002/", "kind": "Request", "state": "closed", "concepts": 5, "errors": 0,
                  "warnings": 0}]
    expect(report["instances"] == instances, report["instances"])
    print("instances", [(i["path"], i["state"]) for i in report["instances"]])

    sys.path.insert(0, str(ROOT / S))
    import okf_common as c
    import okf_profile as p

    questions = [x for x in json.loads(uv(S / "okf_lint.py", EX, "--profiles", "--json"))["questions"]
                 if x.get("field") == "Runbook.owner"]
    expect(len(questions) == 1, "no question mapped to Runbook.owner in --profiles")
    bundle = ROOT / EX
    profile = p.load_profile(bundle)
    docs = [(d.rel, p.resolve_aliases(profile, d.frontmatter))
            for d in (c.load_doc(bundle, f) for f in sorted(bundle.glob("[bf]*/**/*.md"))) if d.frontmatter]
    fragments = [(rel, fm) for rel, fm in docs
                 if rel.startswith("fragments/") and not rel.endswith(("index.md", "log.md"))]
    bad = [rel for rel, fm in fragments
           if not p.is_a(profile, str(fm.get("type")), "Knowledge Fragment") or "distillation_status" not in fm]
    expect(not bad, "not read as a Knowledge Fragment with a distillation_status: " + ", ".join(bad))
    expect(_EX_CLOSING in [rel for rel, _ in fragments], f"{_EX_CLOSING} not read as a fragment")
    runbooks = [(rel, fm) for rel, fm in docs if p.is_a(profile, str(fm.get("type")), "Runbook")]
    gap = [rel for rel, fm in runbooks if fm.get("owner") in (None, "", [], {})]
    expect(gap == ["base/runbooks/consumer-lag-alert.md"], gap)
    print(len(fragments), "fragments read as Knowledge Fragments;", questions[0]["question"], "->",
          len(runbooks), "runbooks, gap", gap)

    report = json.loads(uv(S / "okf_projection.py", EX, "--json"))
    slugs = [x["slug"] for x in report["projections"]]
    expect(slugs == ["onboarding-brief"], slugs)
    expect(report["findings"] == [], report["findings"])
    left = {k: report[k] for k in ("not_checked", "to_recompute", "frozen") if report[k]}
    expect(not left, left)
    print("projections", slugs, "with no findings")

    _closing_traces(bundle)
    _closed_edits(tmp)
    _close_round_trip(tmp)
    expect("EDITED_AFTER_CLOSE" in text(PLUGIN / "skills" / "okf-review" / "SKILL.md"),
           "okf-review does not name EDITED_AFTER_CLOSE")
    print("okf-review names EDITED_AFTER_CLOSE")


_EX_REQ = "requests/req-0002"
_EX_CLOSING = "fragments/2026-11-10-closing-req-0002.md"
_EX_QUESTION = f"{_EX_REQ}/base/questions/export-cadence.md"
_EX_CLOSE = ("--apply", "--fragment", "/" + _EX_CLOSING, "--by", "human:ana", "--actor", "okf-builder/example",
             "--carry", "base/questions/export-cadence.md=base/questions/dispute-export-cadence.md",
             "--at", "2026-11-10T10:05:00+00:00")
# the instance question's generated before okf_close.py carried it, which the round trip restores
_EX_QUESTION_GENERATED = "generated: { by: okf-builder/example, at: 2026-11-09T11:00:00Z }"


def _ledger(path: Path) -> list[tuple[str, list[str]]]:
    """The (Kind, Concept links) of each row of a fragment's # Distillation ledger."""
    body = path.read_text(encoding="utf-8").split("# Distillation", 1)[1]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in body.splitlines()
            if line.startswith("|")][2:]
    return [(r[1], re.findall(r"\]\((/[^)\s]+)\)", r[3])) for r in rows]


def _closing_traces(bundle: Path) -> None:
    """SDR-0024's traces of req-0002's closing, which lint cannot see: the ledger links each instance concept, each
    promoted parent concept cites its instance concept, and each carried question lands on an open parent question
    asked in it."""
    inst = bundle / _EX_REQ
    ledger = _ledger(bundle / _EX_CLOSING)
    linked = {link for _, links in ledger for link in links if link.startswith(f"/{_EX_REQ}/")}
    concepts = {"/" + p.relative_to(bundle).as_posix() for p in (inst / "base").rglob("*.md") if p.name != "index.md"}
    expect(linked == concepts, f"the closing ledger links {sorted(linked)}, the instance holds {sorted(concepts)}")
    for kind, links in ledger:
        if kind != "promote":
            continue
        mine = [x for x in links if x.startswith(f"/{_EX_REQ}/")]
        parents = [x for x in links if not x.startswith(f"/{_EX_REQ}/")]
        expect(len(mine) == 1 and len(parents) == 1, f"promote row links {links}")
        target = bundle / parents[0].lstrip("/")
        expect(target.is_file(), f"promote row's parent concept {parents[0]} does not exist")
        cites = [s.get("resource") for s in _frontmatter(target).get("sources") or [] if isinstance(s, dict)]
        expect(mine[0] in cites, f"{parents[0]} does not cite {mine[0]} in its sources: {cites}")
    carried = [p for p in sorted((inst / "base").rglob("*.md"))
               if p.name != "index.md" and _frontmatter(p).get("question_status") == "carried"]
    expect(carried, "no carried question in the instance")
    for q in carried:
        to = _frontmatter(q).get("carried_to")
        target = (inst / str(to)).resolve() if to else None
        expect(target is not None and target.is_file(), f"{q.relative_to(bundle)}: carried_to {to} does not resolve")
        tfm = _frontmatter(target)
        from_parent = "/" + q.relative_to(bundle).as_posix()
        expect(tfm.get("type") == "Open Question" and tfm.get("question_status") == "open"
               and tfm.get("asked_in") == from_parent,
               f"{to}: not an open Open Question asked in {from_parent}: {tfm.get('question_status')}, "
               f"{tfm.get('asked_in')}")
    print("closing traces:", len(ledger), "ledger rows link the instance's", len(concepts), "concepts;",
          len(carried), "carried question lands on an open parent question")


def _closed_edits(tmp: Path) -> None:
    """The audit finds nothing on the example; an edit after closed_at, planted on a copy, is its one finding."""
    findings = json.loads(uv(S / "okf_audit.py", EX, "--json"))["findings"]
    expect(findings == [], findings)
    copy = tmp / "dogfood-edited" / "knowledge"
    shutil.copytree(ROOT / EX, copy)
    term = copy / _EX_REQ / "base" / "domain" / "req-0002-export-columns.md"
    old = term.read_text(encoding="utf-8")
    new = old.replace("at: 2026-11-09T11:00:00Z }", "at: 2026-11-10T16:00:00Z }")
    expect(new != old, f"{term.name}: generated.at not found")
    term.write_text(new, encoding="utf-8")
    findings = json.loads(uv(S / "okf_audit.py", copy, "--json"))["findings"]
    expected = [{"code": "EDITED_AFTER_CLOSE", "level": "WARN",
                 "path": "requests/req-0002/base/domain/req-0002-export-columns.md", "instance": "requests/req-0002/",
                 "message": "edited after its instance closed: generated.at 2026-11-10T16:00:00+00:00 is later than "
                            "closed_at 2026-11-10T10:05:00+00:00; a closed instance is frozen: restore the concept as "
                            "it was when it closed, or carry the change into the parent"}]
    expect(findings == expected, json.dumps(findings, indent=2))
    print("audit: no finding on the example; the planted edit after closed_at is its one EDITED_AFTER_CLOSE")


def _close_round_trip(tmp: Path) -> None:
    """req-0002 reopened on a copy and closed again with okf_close.py gives the committed example byte for byte; the
    committed instance is ALREADY_CLOSED."""
    for inst in ("requests/req-0001", _EX_REQ):
        summary = last_line(uv(S / "okf_index.py", EX / inst, "--check", ok=(0, 1)))
        expect(summary == "0 index.md out of date", f"{inst}: {summary}")
    copy = tmp / "dogfood-reopened" / "knowledge"
    shutil.copytree(ROOT / EX, copy)
    reopen = {f"{_EX_REQ}/index.md": [(r"^state: closed\n(closed_at: .*\n)?", "state: open\n")],
              _EX_QUESTION: [(r"^question_status: carried\n(carried_to: .*\n)?", "question_status: open\n"),
                             (r"^generated: .*$", _EX_QUESTION_GENERATED)],
              "requests/index.md": [(r"_\(state: closed\)_$", "_(state: open)_")]}
    for rel, subs in reopen.items():
        path = copy / rel
        new = path.read_text(encoding="utf-8")
        for pattern, repl in subs:
            new, n = re.subn(pattern, repl, new, count=1, flags=re.M)
            expect(n == 1, f"{rel}: {pattern} not found")
        path.write_text(new, encoding="utf-8")
    out = uv(S / "okf_close.py", copy / _EX_REQ, *_EX_CLOSE)
    expect(out.rstrip().endswith("then run okf_lint.py on the parent"), f"okf_close.py --apply failed:\n{out}")
    run("diff", "-r", copy, ROOT / EX)
    report = json.loads(uv(S / "okf_close.py", EX / _EX_REQ, "--json", ok=(1,)))
    blockers = [{"code": "ALREADY_CLOSED", "path": "index.md",
                 "message": "it is already closed (closed_at 2026-11-10 10:05:00+00:00)"}]
    expect(report["blockers"] == blockers, report["blockers"])
    print("req-0002 reopened and closed again by okf_close.py is the example byte for byte; it is ALREADY_CLOSED")


_CLOSE_APPLY = ("--apply", "--fragment", "/fragments/2026-11-09-closing-req-0042.md",
                "--carry", "base/questions/who-approves-partial-refunds.md=/base/questions/who-approves-partial-refunds.md",
                "--carry", "C-001=C-002", "--by", "human:test", "--actor", "okf-builder/test", "--at", "2026-11-09T17:00:00Z")
_CLOSE_PLANTS = {  # defect: (file of the copy, old text, new text, failures as (check, subject))
    "a: stays row deleted": ("fragments/2026-11-09-closing-req-0042.md",
                             "| Refund retry | stays | applied | [req-0042: Refund retry]"
                             "(/requests/req-0042/base/runbooks/refund-retry.md) |\n", "",
                             [(2, "/fragments/2026-11-09-closing-req-0042.md")]),
    "b: promoted source removed": ("base/domain/refund-window.md",
                                   "  - { id: req-0042, resource: /requests/req-0042/base/domain/refund-window.md, "
                                   'title: "req-0042: Refund window" }\n', "",
                                   [(3, "/fragments/2026-11-09-closing-req-0042.md")]),
    "c: asked_in changed": ("base/questions/who-approves-partial-refunds.md", "asked_in: /requests/req-0042/",
                            "asked_in: /requests/req-0041/", [(4, "/base/questions/who-approves-partial-refunds.md")]),
    "d: question carry omitted": (None, None, None, [(4, "/base/questions/who-approves-partial-refunds.md")]),
    "e: C-002 not linking the instance": ("conflict-log.md",
                                          "[req-0042's conflict log](/requests/req-0042/conflict-log.md)",
                                          "req-0042's conflict log", [(4, "C-001")]),
    "f: closing fragment in conflict": ("fragments/2026-11-09-closing-req-0042.md", "distillation_status: distilled",
                                        "distillation_status: conflict",
                                        [(2, "/fragments/2026-11-09-closing-req-0042.md")]),
    "pending fragment in the instance": ("requests/req-0042/fragments/2026-11-05-scoping-call.md",
                                         "distillation_status: conflict", "distillation_status: pending",
                                         [(1, "fragments/2026-11-05-scoping-call.md")]),
}


def _tree_hash(root: Path) -> dict:
    import hashlib

    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---\n")[1])


def closing(tmp: Path) -> None:
    """closing of the fixture's open Request with okf_close.py: its report exact; each planted defect or a pending
    fragment fails --apply with its failures and no file changed; --apply then closes it, lint --strict finding
    nothing, the question and the conflict row carried; every concept a promote row links in the parent is a draft
    with no verified; the fixture's index.md files are what okf_index.py would write"""
    for bundle in (CLOSING, CLOSING / "requests" / "req-0042"):
        summary = last_line(uv(S / "okf_index.py", bundle, "--check", ok=(0, 1)))
        expect(summary == "0 index.md out of date", f"{bundle}: {summary}")
        print(bundle, summary)
    close = S / "okf_close.py"
    k = tmp / "closing" / "knowledge"
    shutil.copytree(ROOT / CLOSING, k)
    inst = k / "requests" / "req-0042"
    q = "base/questions/who-approves-partial-refunds.md"
    report = json.loads(uv(close, inst, "--json"))
    expected = {"instance": str(inst), "parent": "../..", "kind": "Request", "state": "open", "blockers": [],
                "concepts": [
                    {"path": "/base/domain/dual-approval.md", "type": "Term", "title": "Dual approval",
                     "from_parent": "/requests/req-0042/base/domain/dual-approval.md", "parent_same_path": None},
                    {"path": "/base/domain/refund-window.md", "type": "Term", "title": "Refund window",
                     "from_parent": "/requests/req-0042/base/domain/refund-window.md",
                     "parent_same_path": "/base/domain/refund-window.md"},
                    {"path": "/" + q, "type": "Open Question", "title": "Who approves partial refunds?",
                     "from_parent": "/requests/req-0042/" + q, "parent_same_path": "/" + q},
                    {"path": "/base/runbooks/refund-retry.md", "type": "Runbook", "title": "Refund retry",
                     "from_parent": "/requests/req-0042/base/runbooks/refund-retry.md", "parent_same_path": None}],
                "questions": [{"path": "/" + q, "owner": "human:maria"}],
                "conflicts": [{"id": "C-001", "state": "open",
                               "description": "Ana says the refund API returns 200 for a refund still pending; Maria "
                                              "says finance reads every 200 as paid"}]}
    expect(report == expected, json.dumps(report, indent=2))
    print("report:", len(report["concepts"]), "concepts, 1 question, 1 conflict, no blocker")

    for name, (rel, old, new, failures) in _CLOSE_PLANTS.items():
        copy = tmp / "closing-planted" / name.split(":")[0].replace(" ", "-") / "knowledge"
        shutil.copytree(ROOT / CLOSING, copy)
        args = list(_CLOSE_APPLY)
        if rel is None:
            del args[3:5]
        else:
            body = (copy / rel).read_text(encoding="utf-8")
            expect(old in body, f"{name}: {old!r} not in {rel}")
            (copy / rel).write_text(body.replace(old, new), encoding="utf-8")
        before = _tree_hash(copy)
        out = uv(close, copy / "requests" / "req-0042", *args, ok=(1,))
        got = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"^FAIL check (\d+): (\S+):", out, re.M)]
        expect(got == failures, f"{name}: failures {got}, expected {failures}\n{out}")
        expect(_tree_hash(copy) == before, f"{name}: --apply changed files after a failed check")
        print(f"planted {name}: exit 1, {got}, no file changed")

    uv(close, inst, *_CLOSE_APPLY)
    found = json.loads(uv(S / "okf_lint.py", k, "--strict", "--json"))
    expect(found["findings"] == [], found["findings"])
    instances = [(i["path"], i["kind"], i["state"]) for i in found["instances"]]
    expect(instances == [("requests/req-0042/", "Request", "closed")], instances)
    fm = _frontmatter(inst / "index.md")
    closed_at = fm.get("closed_at")
    fm["closed_at"] = closed_at.isoformat().replace("+00:00", "Z") if hasattr(closed_at, "isoformat") else closed_at
    want = {"okf_version": "0.2", "okf_profile": "knowledge/3.0", "kind": "Request", "state": "closed",
            "closed_at": "2026-11-09T17:00:00Z", "parent": "../.."}
    expect(fm == want, fm)
    qfm = _frontmatter(inst / q)
    expect(qfm["question_status"] == "carried" and qfm["carried_to"] == "../../" + q, qfm)
    row = next(line for line in (inst / "conflict-log.md").read_text(encoding="utf-8").splitlines()
               if line.startswith("| C-001 "))
    expect([c.strip() for c in row.strip("|").split("|")][4:] == ["carried up to C-002 (`../../conflict-log.md`)",
                                                                 "carried", "human:test"], row)
    print("applied: lint --strict finds nothing;", instances, "; question and C-001 carried")

    ledger = (k / "fragments" / "2026-11-09-closing-req-0042.md").read_text(encoding="utf-8")
    promoted = sorted({m.group(1) for line in ledger.splitlines() if re.match(r"^\|[^|]*\|\s*promote\s*\|", line)
                       for m in re.finditer(r"\]\((/[^)\s]+)\)", line) if not m.group(1).startswith("/requests/")})
    expect(promoted, "no promote row links a parent concept")
    bad = [p for p in promoted if _frontmatter(k / p.lstrip("/")).get("status") != "draft"
           or "verified" in _frontmatter(k / p.lstrip("/"))]
    expect(not bad, f"promoted concepts not a draft without verified: {bad}")
    print("promoted concepts are drafts with no verified:", ", ".join(promoted))


STEPS = {"unit": unit, "init-0.2": init_02, "writing-guide": writing_guide, "decision-template": decision_template, "init-0.1": init_01, "google-fixtures": google_fixtures,
         "migration": migration, "profile-migration": profile_migration, "m365": m365, "copilot": copilot,
         "builtin-profile": builtin_profile, "copies": copies, "m365-agent": m365_agent, "bundles": bundles, "index": index,
         "workflows": workflows, "obsidian-setup": obsidian_setup, "viewer": viewer, "dogfood": dogfood,
         "closing": closing}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("steps", nargs="*", metavar="STEP", help="steps to run (default: all, in order)")
    parser.add_argument("--list", action="store_true", help="list the steps and exit")
    args = parser.parse_args(argv)
    if args.list:
        for name, step in STEPS.items():
            print(f"{name:18} {' '.join(step.__doc__.split())}")
        return 0
    unknown = [s for s in args.steps if s not in STEPS]
    if unknown:
        parser.error(f"unknown step {', '.join(unknown)}; --list names them")
    chosen = args.steps or list(STEPS)
    tmp = Path(tempfile.mkdtemp(prefix="okf-checks-"))
    try:
        for name in chosen:
            print(f"[{name}] {' '.join(STEPS[name].__doc__.split())}")
            try:
                STEPS[name](tmp)
            except Fail as e:
                print(f"FAIL [{name}] {e}")
                return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"OK: {len(chosen)} steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
