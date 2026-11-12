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
           "okf_obsidian", "okf_close")
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
    """M365 export: within the companion limit, each exported skill self-contained, its okf_migrate.py migrating
    the knowledge/2.0 fixture, its okf_projection.py checking the example bundle's projection, its okf-init
    shipping a running okf_obsidian.py and its okf-lint reporting the fragment and question codes"""
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
            mods = {n.module for n in ast.walk(ast.parse(py.read_text(encoding="utf-8")))
                    if isinstance(n, ast.ImportFrom) and n.module} | {
                a.name for n in ast.walk(ast.parse(py.read_text(encoding="utf-8")))
                if isinstance(n, ast.Import) for a in n.names}
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


def copilot(tmp: Path) -> None:
    """Copilot pack: every skill exported with its SKILL.md and the @okf agent naming each one; each SKILL.md's
    frontmatter valid, its description within the limits and in the third person"""
    run("python3", "build/export_copilot.py")
    pack = ROOT / "dist" / "copilot"
    src = sorted(p.parent.name for p in (ROOT / PLUGIN / "skills").glob("*/SKILL.md"))
    out = sorted(p.parent.name for p in (pack / ".github" / "skills").glob("*/SKILL.md"))
    expect(out == src, f"exported skills differ: source {src}, pack {out}")
    agent = (pack / ".github" / "agents" / "okf.agent.md").read_text(encoding="utf-8")
    missing = [s for s in src if s not in agent]
    expect(not missing, "okf.agent.md does not name: " + ", ".join(missing))
    expect((pack / "AGENTS.okf.md").is_file(), "the pack has no AGENTS.okf.md")
    print("copilot pack:", len(out), "skills, all named by the @okf agent")
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
    """the committed root standard/ and templates/ match the ones build/copies.py writes"""
    out = tmp / "copies"
    run("python3", "build/copies.py", out)
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
    (ADR-0028 decision 5)"""
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


def dogfood(tmp: Path) -> None:
    """dogfood state of examples/knowledge: only its 3 known warnings; every fragment is a Knowledge Fragment
    with a distillation_status, aliases resolved; the mapped question Runbook.owner has exactly one gap; its one
    projection, onboarding-brief, has no findings"""
    codes = sorted(f["code"] for f in json.loads(uv(S / "okf_lint.py", EX, "--json"))["findings"])
    expect(codes == ["BROKEN_LINK", "STALE", "VERIFIED_STALE"], codes)
    print("lint codes", codes)

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
    with no verified"""
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


STEPS = {"unit": unit, "init-0.2": init_02, "init-0.1": init_01, "google-fixtures": google_fixtures,
         "migration": migration, "profile-migration": profile_migration, "m365": m365, "copilot": copilot,
         "builtin-profile": builtin_profile, "copies": copies, "m365-agent": m365_agent, "bundles": bundles, "index": index,
         "workflows": workflows, "obsidian-setup": obsidian_setup, "dogfood": dogfood,
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
