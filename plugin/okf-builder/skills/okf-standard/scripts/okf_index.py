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
    find_bundle,
    load_doc,
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
    "references": "Mirrored external material, execution skills and attesters.",
    "skills": "Execution instructions (executors) for computations.",
    "attesters": "Deterministic receipt verification code.",
}

# Order of the sections (types) in the index; the rest follow alphabetically.
TYPE_ORDER = [
    "Project", "Architecture View", "Architecture Decision", "Term", "Glossary",
    "System", "API", "Dataset", "Table", "Metric", "Attested Computation",
    "Runbook", "Playbook", "Policy", "Reference",
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


def build_index(bundle: Path, d: Path) -> str:
    is_root = d.resolve() == bundle.resolve()
    concepts = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix == ".md" and p.name not in RESERVED:
            doc = load_doc(bundle, p)
            fm = doc.frontmatter or {}
            concepts.append((str(fm.get("type") or "Other"), fm.get("title") or p.stem,
                             fm.get("description") or "", p.name, fm.get("status")))
    subdirs = [p for p in sorted(d.iterdir()) if p.is_dir() and not p.name.startswith(".")
               and (bool(list(p.rglob("*.md"))) if not (is_root and p.name == PROJECTIONS_DIR)
                    else (p / "index.md").is_file())]

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
    holding a .md, without hidden directories and never inside the root projections/."""
    top = sub or bundle
    below = [p for p in sorted(top.rglob("*")) if p.is_dir() and not any(
        part.startswith(".") for part in p.relative_to(bundle).parts)]
    return [d for d in [top, *below] if not in_projections(bundle, d)
            and (d == bundle or any(q.suffix == ".md" for q in d.rglob("*.md")))]


def regenerate(bundle: Path, targets: list[Path], check: bool = False) -> int:
    """Write (or, with check, report) each out-of-date index.md of `targets`; return how many differ."""
    changed = 0
    for d in targets:
        new = build_index(bundle, d)
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
        targets = [d] if d == bundle or any(q.suffix == ".md" for q in d.rglob("*.md")) else []
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


def test_default_root_frontmatter_is_30(tmp_path):
    k = tmp_path / "knowledge"
    (k / "base").mkdir(parents=True)
    main([str(k)])
    assert f'okf_profile: "{PROFILE_30}"' in (k / "index.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
