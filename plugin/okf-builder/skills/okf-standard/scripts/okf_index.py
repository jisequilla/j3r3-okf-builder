#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_index.py — Regenerate the index.md files of an OKF bundle from the frontmatter.

Usage:
    uv run okf_index.py [path/to/bundle] [--check] [--dir SUBDIR]

- Groups concepts by `type` inside each directory.
- Lists subdirectories with the first sentence of their own index.md, or their name.
- Keeps the root frontmatter (okf_version, okf_profile) and any section whose
  heading starts with "# Notes" (or "# Notas").
- Never writes into or below the root projections/ (not OKF, ADR-0019); the root
  index lists it only if projections/index.md exists.
- Skips what lint's scan leaves out, as lint does: the paths .okfignore matches,
  nested bundles (an operational instance included: run okf_index.py on it) and
  non-OKF directories. It writes no index.md there and lists neither ignored paths
  nor non-OKF directories; a nested bundle stays listed in its parent's index, and
  a directory holding only nested bundles (a kind directory) keeps its index.md.
- --check: writes nothing; exit 1 if any index.md would change.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    PROFILE_30,
    PROJECTIONS_DIR,
    RESERVED,
    Scan,
    find_bundle,
    load_doc,
    scan_bundle,
    split_frontmatter,
)

DIR_DESCRIPTIONS = {
    "fragments": "Records of events, distilled into the base.",
    "base": "The project's knowledge, in typed directories.",
    "architecture": "Architecture views and principles.",
    "decisions": "Architecture decision records (ADR).",
    "domain": "Glossary and business concepts.",
    "systems": "Services, modules and deployable components.",
    "apis": "API contracts and their semantics.",
    "data": "Datasets, tables and schemas.",
    "metrics": "Metric and KPI definitions.",
    "computations": "Sanctioned computations (Attested Computation).",
    "runbooks": "Operational and incident procedures.",
    "playbooks": "Team and business procedures.",
    "policies": "Rules, standards and compliance.",
    "questions": "Questions nobody has answered yet, each with an owner.",
    "references": "Mirrored external material, execution skills and attesters.",
    "skills": "Execution instructions (executors) for computations.",
    "attesters": "Deterministic receipt verification code.",
}

# Order of the sections (types) in the index; the rest follow alphabetically.
TYPE_ORDER = [
    "Project", "Architecture View", "Architecture Decision", "Term", "Glossary",
    "System", "API", "Dataset", "Table", "Metric", "Attested Computation",
    "Runbook", "Playbook", "Policy", "Open Question", "Reference",
]


def plural_heading(t: str) -> str:
    table = {
        "Project": "Project",
        "Architecture View": "Architecture views",
        "Architecture Decision": "Architecture decisions",
        "Term": "Terms",
        "Glossary": "Glossary",
        "System": "Systems",
        "API": "APIs",
        "Dataset": "Datasets",
        "Table": "Tables",
        "Metric": "Metrics",
        "Attested Computation": "Attested computations",
        "Runbook": "Runbooks",
        "Playbook": "Playbooks",
        "Policy": "Policies",
        "Open Question": "Open questions",
        "Reference": "References",
    }
    return table.get(t, t)


def dir_description(d: Path) -> str:
    idx = d / "index.md"
    if idx.exists():
        _, body = split_frontmatter(idx.read_text(encoding="utf-8"))
        m = re.search(r"^>[ \t]*(.+)$", body, re.M)  # optional descriptive blockquote
        if m:
            return m.group(1).strip()
    return DIR_DESCRIPTIONS.get(d.name, f"Concepts in {d.name}.")


def existing_root_fm_and_notes(idx: Path) -> tuple[str, str]:
    if not idx.exists():
        return "", ""
    text = idx.read_text(encoding="utf-8")
    raw, body = split_frontmatter(text)
    fm = f"---\n{raw}\n---\n\n" if raw is not None else ""
    notes = ""
    m = re.search(r"^(#[ \t]+(?:Notes|Notas).*)", body, re.M | re.S)
    if m:
        notes = m.group(1).rstrip() + "\n"
    return fm, notes


def _rel(bundle: Path, p: Path) -> str:
    return p.resolve().relative_to(bundle.resolve()).as_posix()


def left_out(bundle: Path, sc: Scan, p: Path) -> str | None:
    """Why lint's scan leaves p out of the bundle ('.okfignore', 'nested bundle', 'not OKF'), or None. What lies below
    an ignored directory or a nested bundle is left out with it, a file with its non-OKF directory; a directory below a
    non-OKF directory is judged on its own."""
    rel = _rel(bundle, p)
    if rel == ".":
        return None
    as_dir = rel + "/"
    if any(as_dir.startswith(e) if e.endswith("/") else rel == e for e in sc.ignored):
        return ".okfignore"
    if any(as_dir.startswith(n) for n in sc.nested):
        return "nested bundle"
    home = rel.rpartition("/")[0] + "/" if p.is_file() else as_dir
    if any(home == d for d, _ in sc.not_okf):
        return "not OKF"
    return None


def holds_content(bundle: Path, sc: Scan, d: Path) -> bool:
    """d holds a .md below it that lint's scan does not leave out, or a nested bundle (a kind directory holds only its
    instances)."""
    rel = _rel(bundle, d)
    pre = "" if rel == "." else rel + "/"
    return (any(left_out(bundle, sc, q) is None for q in d.rglob("*.md"))
            or any(n.startswith(pre) for n in sc.nested))


def build_index(bundle: Path, d: Path, sc: Scan | None = None) -> str:
    sc = sc if sc is not None else scan_bundle(bundle)
    is_root = d.resolve() == bundle.resolve()
    concepts = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix == ".md" and p.name not in RESERVED and left_out(bundle, sc, p) is None:
            doc = load_doc(bundle, p)
            fm = doc.frontmatter or {}
            concepts.append((str(fm.get("type") or "Other"), fm.get("title") or p.stem,
                             fm.get("description") or "", p.name, fm.get("status")))
    subdirs = [p for p in sorted(d.iterdir()) if p.is_dir() and not p.name.startswith(".")
               and ((p / "index.md").is_file() if is_root and p.name == PROJECTIONS_DIR
                    else left_out(bundle, sc, p) == "nested bundle"
                    or (left_out(bundle, sc, p) is None and holds_content(bundle, sc, p)))]

    groups: dict[str, list] = {}
    for c in concepts:
        groups.setdefault(c[0], []).append(c)
    ordered = sorted(groups, key=lambda t: (TYPE_ORDER.index(t) if t in TYPE_ORDER else 99, t))

    out = []
    fm_prefix, notes = ("", "")
    if is_root:
        fm_prefix, notes = existing_root_fm_and_notes(d / "index.md")
        if not fm_prefix:
            fm_prefix = f'---\nokf_version: "0.2"\nokf_profile: "{PROFILE_30}"\n---\n\n'
    else:
        _, notes = existing_root_fm_and_notes(d / "index.md")
        out.append(f"> {dir_description(d)}\n")

    for t in ordered:
        out.append(f"# {plural_heading(t)}\n")
        for _, title, desc, fname, status in groups[t]:
            tag = " _(deprecated)_" if status == "deprecated" else (" _(draft)_" if status == "draft" else "")
            line = f"* [{title}]({fname})"
            if desc:
                line += f" - {desc}"
            out.append(line + tag)
        out.append("")
    if subdirs:
        out.append("# Subdirectories\n")
        for s in subdirs:
            out.append(f"* [{s.name}]({s.name}/index.md) - {dir_description(s)}")
        out.append("")
    if not ordered and not subdirs:
        out.append(f"# {d.name}\n")
        out.append("_(empty)_\n")
    body = "\n".join(out).rstrip() + "\n"
    if notes:
        body += "\n" + notes
    return fm_prefix + body


def in_projections(bundle: Path, d: Path) -> bool:
    rel = d.resolve().relative_to(bundle.resolve()).parts
    return bool(rel) and rel[0] == PROJECTIONS_DIR


def index_targets(bundle: Path, sub: Path | None = None) -> list[Path]:
    """Directories whose index.md is regenerated: `sub` (default: the bundle) and every directory below it
    holding a .md lint's scan keeps or a nested bundle, without hidden directories, never inside the root projections/
    and never where lint's scan leaves the path out (.okfignore, a nested bundle, a non-OKF directory)."""
    sc = scan_bundle(bundle)
    top = sub or bundle
    below = [p for p in sorted(top.rglob("*")) if p.is_dir() and not any(
        part.startswith(".") for part in p.relative_to(bundle).parts)]
    return [d for d in [top, *below] if not in_projections(bundle, d) and left_out(bundle, sc, d) is None
            and (d == bundle or holds_content(bundle, sc, d))]


def regenerate(bundle: Path, targets: list[Path], check: bool = False) -> int:
    """Write (or, with check, report) each out-of-date index.md of `targets`; return how many differ."""
    changed = 0
    sc = scan_bundle(bundle)
    for d in targets:
        new = build_index(bundle, d, sc)
        idx = d / "index.md"
        old = idx.read_text(encoding="utf-8") if idx.exists() else None
        if old != new:
            changed += 1
            rel = idx.relative_to(bundle).as_posix()
            if check:
                print(f"OUT OF DATE {rel}")
            else:
                idx.write_text(new, encoding="utf-8")
                print(f"WROTE {rel}")
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="path to the bundle (default: search upwards for knowledge/)")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if any index.md is out of date")
    ap.add_argument("--dir", help="regenerate only this subdirectory (relative to the bundle)")
    args = ap.parse_args(argv)

    bundle = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if bundle is None:
        print("ERROR: bundle not found (knowledge/index.md). Pass its path.", file=sys.stderr)
        return 2

    if args.dir:
        d = bundle / args.dir
        if in_projections(bundle, d):
            print(f"ERROR: {PROJECTIONS_DIR}/ is not OKF; okf-index does not write there.", file=sys.stderr)
            return 2
        sc = scan_bundle(bundle)
        reason = left_out(bundle, sc, d)
        if reason is not None:
            why = "nested bundle: run okf_index.py on it" if reason == "nested bundle" else reason
            print(f"ERROR: {_rel(bundle, d)}/ is not part of this bundle ({why}); okf-index does not write there.",
                  file=sys.stderr)
            return 2
        targets = [d] if d == bundle or holds_content(bundle, sc, d) else []
    else:
        targets = index_targets(bundle)
    changed = regenerate(bundle, targets, args.check)
    if args.check:
        print(f"{changed} index.md out of date")
        return 1 if changed else 0
    print(f"{changed} index.md regenerated")
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_index.py --test)
# --------------------------------------------------------------------------
def _bundle(tmp: Path) -> Path:
    k = tmp / "knowledge"
    (k / "decisions").mkdir(parents=True)
    (k / "policies").mkdir()
    (k / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\n---\n\n'
                                "# Project\n\n_(empty)_\n\n# Notes\n\nKept by hand.\n", encoding="utf-8")
    (k / "decisions" / "index.md").write_text("# decisions\n\n> Decisions.\n\n# Notas\n\nGuardado a mano.\n",
                                              encoding="utf-8")
    (k / "decisions" / "ADR-0001-x.md").write_text(
        "---\ntype: Architecture Decision\ntitle: X\ndescription: The X decision.\n---\n\n# Context\n", encoding="utf-8")
    (k / "policies" / "index.md").write_text(">\nNext line, not a description.\n", encoding="utf-8")
    return k


def test_notes_sections_survive(tmp_path):
    k = _bundle(tmp_path)
    assert main([str(k)]) == 0
    assert "Kept by hand." in (k / "index.md").read_text(encoding="utf-8").splitlines()
    decisions = (k / "decisions" / "index.md").read_text(encoding="utf-8")
    assert "Guardado a mano." in decisions.splitlines()
    assert "* [X](ADR-0001-x.md) - The X decision." in decisions


def test_empty_blockquote_does_not_pull_next_line(tmp_path):
    k = _bundle(tmp_path)
    main([str(k)])
    root = (k / "index.md").read_text(encoding="utf-8")
    assert "Next line, not a description." not in root
    assert "* [policies](policies/index.md) - Rules, standards and compliance." in root


def test_check_reports_then_clears(tmp_path):
    k = _bundle(tmp_path)
    assert main([str(k), "--check"]) == 1
    main([str(k)])
    assert main([str(k), "--check"]) == 0


def _bundle_30(tmp: Path) -> Path:
    k = tmp / "knowledge"
    (k / "base" / "decisions").mkdir(parents=True)
    (k / "fragments").mkdir()
    (k / "projections" / "deck").mkdir(parents=True)
    (k / "index.md").write_text(f'---\nokf_version: "0.2"\nokf_profile: "{PROFILE_30}"\n---\n\n# Project\n\n_(empty)_\n',
                                encoding="utf-8")
    (k / "fragments" / "index.md").write_text("# fragments\n\n_(empty)_\n", encoding="utf-8")
    (k / "base" / "decisions" / "ADR-0001-x.md").write_text(
        "---\ntype: Architecture Decision\ntitle: X\ndescription: The X decision.\n---\n\n# Context\n", encoding="utf-8")
    (k / "projections" / "deck" / "content.md").write_text("Not OKF.\n", encoding="utf-8")
    return k


def test_30_root_lists_layers_and_base_lists_typed_dirs(tmp_path):
    k = _bundle_30(tmp_path)
    assert main([str(k)]) == 0
    root = (k / "index.md").read_text(encoding="utf-8")
    assert "* [fragments](fragments/index.md) - Records of events, distilled into the base." in root
    assert "* [base](base/index.md) - The project's knowledge, in typed directories." in root
    assert "projections" not in root and "decisions" not in root
    base = (k / "base" / "index.md").read_text(encoding="utf-8")
    assert base.startswith("> The project's knowledge, in typed directories.\n")
    assert "* [decisions](decisions/index.md) - Architecture decision records (ADR)." in base
    assert "* [X](ADR-0001-x.md) - The X decision." in (k / "base" / "decisions" / "index.md").read_text(encoding="utf-8")
    assert sorted(p.name for p in (k / "projections").rglob("*")) == ["content.md", "deck"]
    assert main([str(k), "--check"]) == 0


def test_30_projections_listed_only_with_its_index(tmp_path):
    k = _bundle_30(tmp_path)
    (k / "projections" / "index.md").write_text("# projections\n\n> Derived views.\n", encoding="utf-8")
    main([str(k)])
    assert "* [projections](projections/index.md) - Derived views." in (k / "index.md").read_text(encoding="utf-8")
    assert (k / "projections" / "index.md").read_text(encoding="utf-8") == "# projections\n\n> Derived views.\n"
    assert not (k / "projections" / "deck" / "index.md").exists()
    assert main([str(k), "--dir", "projections/deck"]) == 2


def test_questions_dir_has_default_description_and_heading(tmp_path):
    k = _bundle_30(tmp_path)
    (k / "base" / "questions").mkdir()
    (k / "base" / "questions" / "who-owns-refunds.md").write_text(
        "---\ntype: Open Question\ntitle: Who owns refunds?\ndescription: Nobody owns refunds yet.\n---\n\n# Question\n",
        encoding="utf-8")
    main([str(k)])
    base = (k / "base" / "index.md").read_text(encoding="utf-8")
    assert "* [questions](questions/index.md) - Questions nobody has answered yet, each with an owner." in base
    questions = (k / "base" / "questions" / "index.md").read_text(encoding="utf-8")
    assert "# Open questions\n\n* [Who owns refunds?](who-owns-refunds.md) - Nobody owns refunds yet." in questions


def test_default_root_frontmatter_is_30(tmp_path):
    k = tmp_path / "knowledge"
    (k / "base").mkdir(parents=True)
    main([str(k)])
    assert f'okf_profile: "{PROFILE_30}"' in (k / "index.md").read_text(encoding="utf-8")


# --- what lint's scan leaves out: .okfignore, nested bundles, non-OKF directories (standard §2, §2.2) ---
_INSTANCES = ("requests/req-1", "incidents/inc-1", "releases/rel-1")


def _plant(tmp: Path) -> Path:
    """K: a domain bundle with four instances (okf_lint._domain), an .okfignore'd directory and file, a non-OKF
    directory and a nested bundle that is no instance."""
    from okf_lint import _OPEN, _domain, _tree_bundle

    k = _domain(tmp, {"requests/req-1": _OPEN,
                      "incidents/inc-1": "kind: Incident\nstate: closed\nparent: ../..\nclosed_at: 2026-11-10T09:00:00Z\n",
                      "releases/rel-1": "kind: Release\nstate: open\nparent: ../..\n",
                      "releases/rel-1/requests/req-9": "kind: Request\nstate: in-review\nparent: ../..\n"})
    (k / ".okfignore").write_text("base/scratch/\nbase/wip.md\n", encoding="utf-8")
    (k / "base" / "scratch").mkdir()
    (k / "base" / "scratch" / "draft.md").write_text("---\ntype: Term\ntitle: Draft\ndescription: D.\n---\n\n# Definition\n",
                                                     encoding="utf-8")
    (k / "base" / "wip.md").write_text("---\ntype: Term\ntitle: WIP\ndescription: W.\n---\n\n# Definition\n", encoding="utf-8")
    (k / "base" / "vendor").mkdir()
    (k / "base" / "vendor" / "readme.md").write_text("# Vendor\n\nPlain Markdown.\n", encoding="utf-8")
    _tree_bundle(k / "base" / "other-bundle")
    return k


def _tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _lint_view(k: Path) -> tuple[list, list]:
    from okf_lint import lint

    rep = lint(k)[0]
    return sorted((i["code"], i["path"]) for i in rep.items), list(rep.notices)


def test_index_leaves_each_instance_byte_identical(tmp_path):
    k = _plant(tmp_path)
    before = {rel: _tree(k / rel) for rel in _INSTANCES}
    assert main([str(k)]) == 0
    assert {rel: _tree(k / rel) for rel in _INSTANCES} == before
    assert (k / "requests/req-1/index.md").read_text(encoding="utf-8").startswith(
        '---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\nkind: Request\nstate: open\nparent: ../..\n---\n')
    assert main([str(k), "--check"]) == 0


def test_lint_findings_and_notices_unchanged_by_index(tmp_path):
    k = _plant(tmp_path)
    before = _lint_view(k)
    assert before[0] == []
    main([str(k)])
    assert _lint_view(k) == before


def test_index_writes_only_outside_excluded_paths(tmp_path, capsys):
    k = _plant(tmp_path)
    (k / "requests" / "index.md").unlink()  # the kind directory holds nothing but its instance: still a target
    capsys.readouterr()
    assert main([str(k)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "WROTE index.md", "WROTE base/index.md", "WROTE fragments/index.md", "WROTE incidents/index.md",
        "WROTE releases/index.md", "WROTE requests/index.md", "6 index.md regenerated"]


def test_parent_index_skips_ignored_and_not_okf(tmp_path):
    k = _plant(tmp_path)
    main([str(k)])
    assert (k / "base/index.md").read_text(encoding="utf-8") == (
        "> The project's knowledge, in typed directories.\n\n# Domain Profile\n\n* [DP](profile.md) - DP. _(draft)_\n\n"
        "# Subdirectories\n\n* [other-bundle](other-bundle/index.md) - Concepts in other-bundle.\n")
    assert (k / "requests/index.md").read_text(encoding="utf-8") == (
        "> Concepts in requests.\n\n# Subdirectories\n\n* [req-1](req-1/index.md) - Concepts in req-1.\n")
    assert not (k / "base/scratch/index.md").exists() and not (k / "base/vendor/index.md").exists()


def test_dir_into_excluded_path_exits_2(tmp_path, capsys):
    k = _plant(tmp_path)
    before = _tree(k)
    for d, why in (("requests/req-1", "nested bundle: run okf_index.py on it"), ("base/scratch", ".okfignore"),
                   ("base/vendor", "not OKF"), ("base/other-bundle", "nested bundle: run okf_index.py on it")):
        capsys.readouterr()
        assert main([str(k), "--dir", d]) == 2
        assert capsys.readouterr().err == f"ERROR: {d}/ is not part of this bundle ({why}); okf-index does not write there.\n"
        assert _tree(k) == before


def test_an_instance_indexed_as_its_own_bundle_keeps_its_root_frontmatter(tmp_path):
    k = _plant(tmp_path)
    req = k / "requests" / "req-1"
    fm = (req / "index.md").read_text(encoding="utf-8").partition("---\n\n")[0]
    assert main([str(req)]) == 0
    assert (req / "index.md").read_text(encoding="utf-8").startswith(fm + "---\n\n# ")
    assert main([str(req), "--check"]) == 0


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
