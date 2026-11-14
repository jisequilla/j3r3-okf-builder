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
- A directory with no index.md yet is described by the built-in text of a layer or typed directory of the
  standard (fragments/, base/, base/<name>/), else by the description of the first type of the Domain Profile
  in force that declares it as its directory (base/decisions/architecture/, a local type's directory), else by
  the built-in text for its name, else "Concepts in <name>.".
- Lists, in the directory of each kind the bundle holds (standard §2.2, §5.1), its instances under
  `# Instances`, each with its project.md description and its state; the kind's description from the
  Domain Profile is that index's blockquote and the parent's description of the directory. On an
  instance it finds the domain profile through the `parent` chain, as lint does.
- Keeps the root frontmatter (okf_version, okf_profile) and any section whose
  heading starts with "# Notes" (or "# Notas").
- Never writes into or below the root projections/ (not OKF, ADR-0019); the root
  index lists it only if projections/index.md exists.
- Skips what lint's scan leaves out, as lint does: the paths .okfignore matches,
  nested bundles (an operational instance included: run okf_index.py on it) and
  non-OKF directories. It writes no index.md there and lists neither ignored paths
  nor non-OKF directories; a nested bundle stays listed in its parent's index, and
  a directory holding only nested bundles (a kind directory) keeps its index.md.
- A path with a hidden directory (a name starting with '.') never counts as content
  and never gets an index.md; nor does anything below a non-OKF directory, which
  counts as content of no ancestor. --dir into either exits 2 and writes nothing.
- --check: writes nothing; exit 1 if any index.md would change.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    BASE_DIR,
    PROFILE_30,
    PROJECTIONS_DIR,
    RESERVED,
    Scan,
    find_bundle,
    load_doc,
    root_frontmatter,
    scan_bundle,
    split_frontmatter,
)
from okf_lint import Report, find_tree, kind_instances  # noqa: E402
from okf_profile import Resolved, kind_in_force, load_profile  # noqa: E402

DIR_DESCRIPTIONS = {
    "fragments": "Records of events, distilled into the base.",
    "base": "The project's knowledge, in typed directories.",
    "architecture": "Architecture views and principles.",
    "decisions": "Decisions: what was decided, why, and what else was considered.",
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
    "Project", "Architecture View", "Decision", "Architecture Decision", "Term", "Glossary",
    "System", "API", "Dataset", "Table", "Metric", "Attested Computation",
    "Runbook", "Playbook", "Policy", "Open Question", "Reference",
]


def plural_heading(t: str) -> str:
    table = {
        "Project": "Project",
        "Architecture View": "Architecture views",
        "Decision": "Decisions",
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


def dir_description(d: Path, rel: str | None = None, types: dict | None = None) -> str:
    """The description of directory d, whose bundle-relative path is rel (default: its name): the blockquote of its
    index.md; else DIR_DESCRIPTIONS when d is a layer or typed directory of the standard (<name>/ or base/<name>/);
    else the description of the type that declares rel as its directory (types: type_dirs); else DIR_DESCRIPTIONS by
    name; else "Concepts in <name>."."""
    idx = d / "index.md"
    if idx.exists():
        _, body = split_frontmatter(idx.read_text(encoding="utf-8"))
        m = re.search(r"^>[ \t]*(.+)$", body, re.M)  # optional descriptive blockquote
        if m:
            return m.group(1).strip()
    rel = d.name if rel is None else rel
    if rel in (d.name, f"{BASE_DIR}/{d.name}") and d.name in DIR_DESCRIPTIONS:
        return DIR_DESCRIPTIONS[d.name]
    if types and rel in types:
        return types[rel]
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


def hidden(rel: str) -> bool:
    """A bundle-relative path with a segment whose name starts with '.'."""
    return any(part.startswith(".") for part in rel.split("/"))


def left_out(bundle: Path, sc: Scan, p: Path) -> str | None:
    """Why p is not part of the bundle ('.okfignore', 'nested bundle', 'hidden', 'not OKF', 'inside the non-OKF
    directory <d>'), or None. What lies below an ignored directory or a nested bundle is left out with it, a file with
    its non-OKF directory, and a directory with a hidden segment (lint's scan never walks into one); a directory below
    a non-OKF directory, and every file in it, is left out with that directory too."""
    rel = _rel(bundle, p)
    if rel == ".":
        return None
    as_dir = rel + "/"
    if any(as_dir.startswith(e) if e.endswith("/") else rel == e for e in sc.ignored):
        return ".okfignore"
    if any(as_dir.startswith(n) for n in sc.nested):
        return "nested bundle"
    if p.is_dir() and hidden(rel):
        return "hidden"
    home = rel.rpartition("/")[0] + "/" if p.is_file() else as_dir
    if any(home == d for d, _ in sc.not_okf):
        return "not OKF"
    above = [d for d, _ in sc.not_okf if home.startswith(d)]
    if above:
        return f"inside the non-OKF directory {above[0]}"
    return None


def holds_content(bundle: Path, sc: Scan, d: Path) -> bool:
    """d holds a .md below it, outside every hidden directory, that is not left out (left_out), or a nested bundle (a
    kind directory holds only its instances)."""
    rel = _rel(bundle, d)
    pre = "" if rel == "." else rel + "/"
    return (any(left_out(bundle, sc, q) is None for q in d.rglob("*.md") if not hidden(_rel(bundle, q.parent)))
            or any(n.startswith(pre) for n in sc.nested))


def profiles_of(bundle: Path) -> tuple[Resolved, Resolved]:
    """The Domain Profile in force in this bundle and that of the domain bundle of its tree (found through the parent
    chain for an instance, else the same). A broken parent chain is printed on stderr and the bundle's own profile is
    used."""
    rep = Report()
    tree = find_tree(bundle, rep)
    for i in rep.items:
        print(f"WARNING: {i['code']}: {i['message']}", file=sys.stderr)
    domain = tree.domain if tree is not None else None
    prof = load_profile(bundle, domain=domain)
    return prof, domain or prof


def type_dirs(prof: Resolved) -> dict[str, str]:
    """The directory each type of the Domain Profile declares (bundle-relative, no trailing slash) with that type's
    description, ending in a period; when several types declare one directory, the first in the profile's order that
    has a description."""
    out: dict[str, str] = {}
    for t in prof.types.values():
        rel = str(t.get("directory") or "").strip("/")
        desc = str(t.get("description") or "").strip()
        if rel and desc and rel not in out:
            out[rel] = desc if desc.endswith(".") else desc + "."
    return out


def kind_dirs(bundle: Path, sc: Scan,
              profs: tuple[Resolved, Resolved] | None = None) -> dict[str, tuple[str, list[str]]]:
    """The directory of each kind this bundle holds (bundle-relative, no trailing slash): the kind's description from
    the Domain Profile (the domain bundle's, found through the parent chain for an instance) and its instances
    (scan.nested form). profs: profiles_of(bundle), read here when not given."""
    prof, domain = profs if profs is not None else profiles_of(bundle)
    out = {}
    for k, d, rels in kind_instances(bundle, root_frontmatter(bundle), prof, domain, sc):
        desc = kind_in_force(domain, k)["description"]
        out[d.rstrip("/")] = (str(desc).strip() if desc else f"Instances of {k}.", rels)
    return out


def instance_entry(inst: Path) -> str:
    """`* [id](id/index.md) - <project.md description> _(state: <state>)_` for an instance of a kind directory."""
    pj = inst / "project.md"
    fm = (load_doc(inst, pj).frontmatter if pj.is_file() else None) or {}
    desc = fm.get("description") if isinstance(fm, dict) else None
    state = root_frontmatter(inst).get("state")
    line = f"* [{inst.name}]({inst.name}/index.md)"
    if desc:
        line += f" - {desc}"
    return line + (f" _(state: {state})_" if state is not None and str(state).strip() else " _(no state)_")


def build_index(bundle: Path, d: Path, sc: Scan | None = None, kinds: dict | None = None,
                types: dict | None = None) -> str:
    sc = sc if sc is not None else scan_bundle(bundle)
    if kinds is None or types is None:
        profs = profiles_of(bundle)
        kinds = kinds if kinds is not None else kind_dirs(bundle, sc, profs)
        types = types if types is not None else type_dirs(profs[0])
    is_root = d.resolve() == bundle.resolve()
    kind_desc, instances = kinds.get(_rel(bundle, d), (None, []))
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
                    or (left_out(bundle, sc, p) is None and holds_content(bundle, sc, p)))
               and _rel(bundle, p) + "/" not in instances]

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
        out.append(f"> {kind_desc or dir_description(d, _rel(bundle, d), types)}\n")

    for t in ordered:
        out.append(f"# {plural_heading(t)}\n")
        for _, title, desc, fname, status in groups[t]:
            tag = " _(deprecated)_" if status == "deprecated" else (" _(draft)_" if status == "draft" else "")
            line = f"* [{title}]({fname})"
            if desc:
                line += f" - {desc}"
            out.append(line + tag)
        out.append("")
    if instances:
        out.append("# Instances\n")
        out += [instance_entry(bundle / rel.rstrip("/")) for rel in instances]
        out.append("")
    if subdirs:
        out.append("# Subdirectories\n")
        for s in subdirs:
            rel = _rel(bundle, s)
            desc = kinds[rel][0] if rel in kinds else dir_description(s, rel, types)
            out.append(f"* [{s.name}]({s.name}/index.md) - {desc}")
        out.append("")
    if not ordered and not subdirs and not instances:
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
    profs = profiles_of(bundle)
    kinds, types = kind_dirs(bundle, sc, profs), type_dirs(profs[0])
    for d in targets:
        new = build_index(bundle, d, sc, kinds, types)
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
    assert ("* [decisions](decisions/index.md) - Decisions: what was decided, why, and what else was considered."
            in base)
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


# --- every type that is a Decision, in base/decisions/ and its subfolders (ADR-0041) ---
_STANDARD_DECISION = ("types:\n  Standard Decision:\n    extends: Decision\n    description: A decision about the standard\n"
                      "    directory: /base/decisions/standard/\n    prefix: SDR\n")
_DECISIONS = {"base/decisions/DEC-0001-how-we-work.md": ("Decision", "DEC-0001: How we work", "How we work decided."),
              "base/decisions/architecture/ADR-0001-use-kafka.md": ("Architecture Decision", "ADR-0001: Use Kafka",
                                                                    "Kafka decided."),
              "base/decisions/standard/SDR-0001-format.md": ("Standard Decision", "SDR-0001: Format", "Format decided.")}
_DECISIONS_DESC = "Decisions: what was decided, why, and what else was considered."


def _concept(k: Path, rel: str, type_: str, title: str, desc: str) -> None:
    (k / rel).parent.mkdir(parents=True, exist_ok=True)
    (k / rel).write_text(f'---\ntype: {type_}\ntitle: "{title}"\ndescription: {desc}\nstatus: draft\n---\n\n# Context\n',
                         encoding="utf-8")


def _decisions_bundle(tmp: Path, profile: str = _STANDARD_DECISION) -> Path:
    """D: a knowledge/3.0 bundle whose profile declares Standard Decision, with one decision of each of the three
    types in its type's directory and no index.md below base/."""
    k = tmp / "knowledge"
    (k / "base").mkdir(parents=True)
    (k / "index.md").write_text(f'---\nokf_version: "0.2"\nokf_profile: "{PROFILE_30}"\n---\n\n# Project\n\n_(empty)_\n',
                                encoding="utf-8")
    (k / "base" / "profile.md").write_text("---\ntype: Domain Profile\ntitle: P\ndescription: The taxonomy.\nstatus: draft\n"
                                           + profile + "---\n\n# What this bundle holds\n\nText.\n", encoding="utf-8")
    for rel, concept in _DECISIONS.items():
        _concept(k, rel, *concept)
    return k


def _decision_indexes(k: Path) -> dict:
    return {d: (k / "base" / d / "index.md").read_text(encoding="utf-8")
            for d in ("decisions", "decisions/architecture", "decisions/standard")}


def test_decisions_and_their_subfolders_are_described_by_their_types(tmp_path):
    k = _decisions_bundle(tmp_path)
    for d in ("base/decisions/standard", "base/decisions/architecture", "base/decisions", "base", "."):
        assert main([str(k), "--dir", d]) == 0
    assert _decision_indexes(k) == {
        "decisions": f"> {_DECISIONS_DESC}\n\n"
                     "# Decisions\n\n* [DEC-0001: How we work](DEC-0001-how-we-work.md) - How we work decided. _(draft)_\n\n"
                     "# Subdirectories\n\n"
                     "* [architecture](architecture/index.md) - A decision about how a system is built (ADR).\n"
                     "* [standard](standard/index.md) - A decision about the standard.\n",
        "decisions/architecture": "> A decision about how a system is built (ADR).\n\n# Architecture decisions\n\n"
                                  "* [ADR-0001: Use Kafka](ADR-0001-use-kafka.md) - Kafka decided. _(draft)_\n",
        "decisions/standard": "> A decision about the standard.\n\n# Standard Decision\n\n"
                              "* [SDR-0001: Format](SDR-0001-format.md) - Format decided. _(draft)_\n"}
    assert main([str(k), "--check"]) == 0
    # the same bodies when the parent is written first and describes subfolders that have no index.md yet
    k2 = _decisions_bundle(tmp_path / "top-down")
    assert main([str(k2)]) == 0
    assert _decision_indexes(k2) == _decision_indexes(k)


def test_decisions_of_both_types_in_one_directory_list_decisions_first(tmp_path):
    k = _decisions_bundle(tmp_path, profile="")
    for rel in list(_DECISIONS)[1:]:
        (k / rel).unlink()
    _concept(k, "base/decisions/ADR-0001-use-kafka.md", "Architecture Decision", "ADR-0001: Use Kafka", "Kafka decided.")
    assert main([str(k)]) == 0
    assert (k / "base/decisions/index.md").read_text(encoding="utf-8") == (
        f"> {_DECISIONS_DESC}\n\n"
        "# Decisions\n\n* [DEC-0001: How we work](DEC-0001-how-we-work.md) - How we work decided. _(draft)_\n\n"
        "# Architecture decisions\n\n* [ADR-0001: Use Kafka](ADR-0001-use-kafka.md) - Kafka decided. _(draft)_\n")


def test_a_typed_directory_is_described_by_the_type_that_declares_it(tmp_path):
    profile = ("types:\n  Meeting Note:\n    description: What a meeting settled.\n    directory: /base/meetings/\n"
               "  Review Note:\n    description: A second type of the same directory\n    directory: /base/meetings/\n"
               "  System View:\n    description: How one system is laid out\n    directory: /base/systems/architecture/\n")
    k = _decisions_bundle(tmp_path, profile=profile)
    for rel, type_ in (("base/meetings/kickoff.md", "Meeting Note"), ("base/systems/architecture/billing.md", "System View"),
                       ("base/architecture/context.md", "Architecture View"), ("base/systems/decisions/x.md", "Term")):
        _concept(k, rel, type_, "T", "D.")
    assert main([str(k)]) == 0
    first = {d: (k / "base" / d / "index.md").read_text(encoding="utf-8").partition("\n")[0]
             for d in ("meetings", "systems/architecture", "decisions/architecture", "architecture", "systems",
                       "systems/decisions", "decisions")}
    assert first == {
        # the first type in the profile's order; a description that ends in a period gains none
        "meetings": "> What a meeting settled.",
        # never the text of the top-level directory of the same name when a type declares the subfolder
        "systems/architecture": "> How one system is laid out.",
        "decisions/architecture": "> A decision about how a system is built (ADR).",
        # a typed directory of the standard keeps its built-in text, not its type's description
        "architecture": "> Architecture views and principles.",
        "systems": "> Services, modules and deployable components.",
        "decisions": f"> {_DECISIONS_DESC}",
        # a subfolder no type declares is described by its name, as before
        "systems/decisions": f"> {_DECISIONS_DESC}"}
    assert "* [meetings](meetings/index.md) - What a meeting settled.\n" in (k / "base/index.md").read_text(encoding="utf-8")
    # an existing index.md's blockquote wins over the type's description
    idx = k / "base/decisions/architecture/index.md"
    idx.write_text(idx.read_text(encoding="utf-8").replace("> A decision about how a system is built (ADR).", "> Our ADRs."),
                   encoding="utf-8")
    assert main([str(k)]) == 0
    assert idx.read_text(encoding="utf-8").startswith("> Our ADRs.\n")
    assert "* [architecture](architecture/index.md) - Our ADRs.\n" in (k / "base/decisions/index.md").read_text(encoding="utf-8")


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
        "> A request\n\n# Instances\n\n* [req-1](req-1/index.md) - P. _(state: open)_\n")
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


def _hidden_and_vendor(tmp: Path) -> Path:
    """H: a clean bundle, indexed, then a hidden directory under base/hid/ and an OKF Term below the non-OKF
    base/x/vendor/."""
    from okf_lint import _tree_bundle

    k = _tree_bundle(tmp / "knowledge")
    (k / "base" / "decisions").mkdir()
    (k / "base" / "decisions" / "index.md").write_text("# decisions\n\n_(empty)_\n", encoding="utf-8")
    assert main([str(k)]) == 0
    for rel, text in (("base/hid/.cache/a.md", "plain\n"), ("base/x/vendor/README.md", "# readme\n"),
                      ("base/x/vendor/deep/term.md", "---\ntype: Term\ntitle: Deep\ndescription: A term.\n"
                                                     "generated: { by: human:test, at: 2026-11-13T09:00:00Z }\n---\n\n"
                                                     "# Definition\n\nText.\n")):
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
    return k


def test_hidden_paths_and_what_lies_below_a_non_okf_directory_get_no_index(tmp_path, capsys):
    k = _hidden_and_vendor(tmp_path)
    base_index = (k / "base" / "index.md").read_bytes()
    lint_before = _lint_view(k)
    assert lint_before == ([], ["base/x/vendor/ is not OKF: 1 Markdown file without OKF frontmatter and no index.md, "
                                "skipped"])
    capsys.readouterr()
    for extra in ([], ["--dir", "base/hid"], ["--dir", "base/x"]):
        rc = main([str(k), *extra, "--check"])
        assert (capsys.readouterr().out.splitlines(), rc) == (["0 index.md out of date"], 0), extra
    before = _tree(k)
    for d, why in (("base/hid/.cache", "hidden"), ("base/x/vendor/deep", "inside the non-OKF directory base/x/vendor/"),
                   ("base/x/vendor", "not OKF")):
        assert main([str(k), "--dir", d, "--check"]) == 2, d
        assert capsys.readouterr().err == f"ERROR: {d}/ is not part of this bundle ({why}); okf-index does not write there.\n"
        assert _tree(k) == before, d
    assert main([str(k)]) == 0
    assert capsys.readouterr().out.splitlines() == ["0 index.md regenerated"]
    assert [p.relative_to(k).as_posix() for p in (k / "base").rglob("index.md")
            if p.parent.name not in ("base", "decisions")] == []
    assert (k / "base" / "index.md").read_bytes() == base_index
    assert _lint_view(k) == lint_before


def test_an_instance_indexed_as_its_own_bundle_keeps_its_root_frontmatter(tmp_path):
    k = _plant(tmp_path)
    req = k / "requests" / "req-1"
    fm = (req / "index.md").read_text(encoding="utf-8").partition("---\n\n")[0]
    assert main([str(req)]) == 0
    assert (req / "index.md").read_text(encoding="utf-8").startswith(fm + "---\n\n# ")
    assert main([str(req), "--check"]) == 0


# --- the directory of each kind lists its instances and their states (standard §2.2, §5.1; ADR-0039 decision 3) ---
def _kinds(tmp: Path) -> Path:
    """K: okf_lint._domain with its three kinds and four instances, one of them held by an instance."""
    from okf_lint import _OPEN, _domain

    return _domain(tmp, {"requests/req-1": _OPEN,
                         "incidents/inc-1": "kind: Incident\nstate: closed\nparent: ../..\nclosed_at: 2026-11-10T09:00:00Z\n",
                         "releases/rel-1": "kind: Release\nstate: open\nparent: ../..\n",
                         "releases/rel-1/requests/req-9": "kind: Request\nstate: in-review\nparent: ../..\n"})


def test_kind_index_lists_instances_with_state(tmp_path):
    k = _kinds(tmp_path)
    assert main([str(k)]) == 0
    want = {"requests": "> A request\n\n# Instances\n\n* [req-1](req-1/index.md) - P. _(state: open)_\n",
            "incidents": "> An incident\n\n# Instances\n\n* [inc-1](inc-1/index.md) - P. _(state: closed)_\n",
            "releases": "> A release\n\n# Instances\n\n* [rel-1](rel-1/index.md) - P. _(state: open)_\n"}
    assert {d: (k / d / "index.md").read_text(encoding="utf-8") for d in want} == want
    assert main([str(k), "--check"]) == 0
    (k / "requests" / "index.md").unlink()
    assert main([str(k), "--dir", "requests"]) == 0
    assert (k / "requests" / "index.md").read_text(encoding="utf-8") == want["requests"]


def test_root_lists_kind_dirs_with_their_description(tmp_path):
    k = _kinds(tmp_path)
    main([str(k)])
    root = (k / "index.md").read_text(encoding="utf-8")
    assert root.partition("# Subdirectories\n\n")[2] == (
        "* [base](base/index.md) - The project's knowledge, in typed directories.\n"
        "* [fragments](fragments/index.md) - Records of events, distilled into the base.\n"
        "* [incidents](incidents/index.md) - An incident\n"
        "* [releases](releases/index.md) - A release\n"
        "* [requests](requests/index.md) - A request\n")


def test_instance_holding_a_kind_indexes_its_kind_dir(tmp_path):
    k = _kinds(tmp_path)
    rel = k / "releases" / "rel-1"
    fm = (rel / "index.md").read_text(encoding="utf-8").partition("---\n\n")[0]
    assert main([str(rel)]) == 0
    assert (rel / "requests" / "index.md").read_text(encoding="utf-8") == (
        "> A request\n\n# Instances\n\n* [req-9](req-9/index.md) - P. _(state: in-review)_\n")
    root = (rel / "index.md").read_text(encoding="utf-8")
    assert root.startswith(fm + "---\n\n") and "* [requests](requests/index.md) - A request\n" in root
    assert main([str(rel), "--check"]) == 0


def test_an_instance_holding_no_kind_has_no_kind_index(tmp_path):
    k = _kinds(tmp_path)
    req = k / "requests" / "req-1"
    assert kind_dirs(req, scan_bundle(req)) == {}
    assert main([str(req)]) == 0
    assert [p.relative_to(req).as_posix() for p in sorted(req.rglob("index.md"))
            if "# Instances" in p.read_text(encoding="utf-8") or "_(state:" in p.read_text(encoding="utf-8")] == []


def test_state_change_makes_kind_index_out_of_date(tmp_path, capsys):
    k = _kinds(tmp_path)
    main([str(k)])
    idx = k / "requests" / "req-1" / "index.md"
    idx.write_text(idx.read_text(encoding="utf-8").replace("state: open", "state: in-review"), encoding="utf-8")
    capsys.readouterr()
    assert main([str(k), "--check"]) == 1
    assert capsys.readouterr().out == "OUT OF DATE requests/index.md\n1 index.md out of date\n"


def test_kind_description_comes_from_the_profile(tmp_path, capsys):
    from okf_profile import OWN_REL

    k = _kinds(tmp_path)
    main([str(k)])
    prof = k / OWN_REL
    prof.write_text(prof.read_text(encoding="utf-8").replace("description: A request", "description: A customer request"),
                    encoding="utf-8")
    capsys.readouterr()
    assert main([str(k), "--check"]) == 1
    assert capsys.readouterr().out == "OUT OF DATE index.md\nOUT OF DATE requests/index.md\n2 index.md out of date\n"
    main([str(k)])
    assert (k / "requests" / "index.md").read_text(encoding="utf-8").startswith("> A customer request\n")


def test_kind_index_edge_entries(tmp_path):
    from okf_lint import _OPEN, _domain

    k = _domain(tmp_path, {"requests/req-1": _OPEN, "requests/req-0": _OPEN, "requests/req-2": "kind: Request\nparent: ../..\n",
                           "requests/req-3": _OPEN})
    pj = k / "requests" / "req-1" / "project.md"
    pj.write_text(pj.read_text(encoding="utf-8").replace("description: P.\n", ""), encoding="utf-8")
    (k / "requests" / "req-3" / "project.md").unlink()
    idx = k / "requests" / "index.md"
    idx.write_text(idx.read_text(encoding="utf-8") + "\n# Notes\n\nKept by hand.\n", encoding="utf-8")
    main([str(k)])
    assert idx.read_text(encoding="utf-8") == (
        "> A request\n\n# Instances\n\n"
        "* [req-0](req-0/index.md) - P. _(state: open)_\n"
        "* [req-1](req-1/index.md) _(state: open)_\n"
        "* [req-2](req-2/index.md) - P. _(no state)_\n"
        "* [req-3](req-3/index.md) _(state: open)_\n"
        "\n# Notes\n\nKept by hand.\n")


def test_lint_clean_after_index(tmp_path):
    k = _kinds(tmp_path)
    before = _lint_view(k)
    assert before[0] == []
    main([str(k)])
    assert _lint_view(k) == before


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
