#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_init.py — Create the knowledge/ structure of the knowledge/3.0 profile (OKF v0.2).

Usage:
    uv run okf_init.py --root /path/to/repo --title "My project" \
        --description "One sentence" --actor human:jisequilla [--repo-url URL] \
        [--purpose "What problem it solves, for whom"] [--dirs architecture,decisions,...] [--force]
    uv run okf_init.py --instance Request --id req-42 --in knowledge \
        --title "Refund for order 42" --description "One sentence" --actor human:jisequilla [--dirs decisions]

Creates the three layers: fragments/ (with its index.md), base/ with one typed
directory per --dirs entry, and projections/ (with only a .gitkeep: it is not OKF).
project.md holds no placeholder: what init knows is filled in (title, description,
repository URL, and Purpose from --purpose or else the description), and the rows
and sections it cannot fill (Scope, Team and ownership, empty Key links rows) are
left out, so a fresh bundle has no SECTION_EMPTY; the Knowledge map links only the
typed directories created. Existing files are not overwritten unless --force is given.
Idempotent.

With --instance, init opens a unit of work instead (standard §2.2, ADR-0039): an
operational bundle of that kind, with no typed directory unless --dirs names some,
in the kind's directory of the --in bundle, whose root index.md declares okf_version,
okf_profile, kind, state: open and parent: ../..; okf-index then runs on the new
instance and on its holder. The kind must be one with a directory that the holder
holds (every such kind for a domain bundle, the kinds its kind holds otherwise);
otherwise nothing is written and the exit code is 2.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    BASE_DIR,
    FRAGMENTS_DIR,
    PROFILE_30,
    PROJECTIONS_DIR,
    TABLE_SEP_RE,
    body_sections,
    content_lines,
    declared_profile,
    now_iso,
    parse_yaml,
    placeholder_line,
    root_frontmatter,
    scan_body,
    split_frontmatter,
    table_cells,
)

_HERE = Path(__file__).resolve().parent
TEMPLATES = _HERE.parent / "templates"   # okf-standard/scripts/ → okf-standard/templates/
DEFAULT_DIRS = ["architecture", "decisions", "domain", "systems", "apis", "data",
                "metrics", "computations", "runbooks", "playbooks", "policies", "questions", "references"]
DIR_DESC = {
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
    "fragments": "Records of events, distilled into the base.",
    "base": "The project's knowledge, in typed directories.",
    "skills": "Execution instructions (executors) for computations.",
    "attesters": "Deterministic receipt verification code.",
}


def render(name: str, **vars) -> str:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def set_section(text: str, title: str, content: str) -> str:
    """The '# title' section of a rendered template with its body replaced by content."""
    lines = text.split("\n")
    for sec in body_sections(lines):
        if sec.level == 1 and sec.title == title:
            return "\n".join(lines[:sec.line + 1] + ["", content, ""] + lines[sec.end:])
    return text


def prune_unfilled(text: str) -> str:
    """A rendered template without what was left unfilled: each placeholder line (placeholder_line) goes, a table
    left with its header alone goes with it, and then each section with no content left (content_lines), its
    heading included. Code fences and HTML comments are kept as they are, and so is the frontmatter."""
    head, sep, body = text.partition("\n---\n") if text.startswith("---\n") else ("", "", text)
    lines = body.split("\n")
    hidden = [b.code or b.in_comment for b in scan_body(lines)]
    kept: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if hidden[i]:
            kept.append(line)
            i += 1
            continue
        is_header = table_cells(line) is not None and i + 1 < len(lines) and bool(TABLE_SEP_RE.match(lines[i + 1]))
        if is_header:
            j = i + 2
            while j < len(lines) and table_cells(lines[j]) is not None:
                j += 1
            rows = [r for r in lines[i + 2:j] if not placeholder_line(r)]
            if rows or j == i + 2:
                kept += [line, lines[i + 1], *rows]
            i = j
            continue
        if not placeholder_line(line):
            kept.append(line)
        i += 1
    while True:
        empty = [s for s in body_sections(kept) if not content_lines(kept[s.line + 1:s.end])]
        if not empty:
            break
        s = empty[-1]
        kept = kept[:s.line] + kept[s.end:]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip("\n") + "\n"
    return head + sep + "\n" + out if sep else out


MAP_LINK_RE = re.compile(r"^\* \[[^\]]*\]\(/base/([^/)]+)/index\.md\)")


def prune_map(text: str, dirs: list[str]) -> str:
    """project.md without the Knowledge map links to a typed directory not created (a --dirs that leaves it out)."""
    return "\n".join(line for line in text.split("\n")
                     if not ((m := MAP_LINK_RE.match(line)) and m.group(1) not in dirs))


class Refusal(Exception):
    """An --instance init that cannot be done; nothing has been written."""


def instance_target(holder: Path, kind: str, ident: str) -> tuple[Path, str]:
    """The directory of the new instance and the kind's declared id; Refusal when the holder is no bundle, the kind
    is unknown, abstract or not held by the holder, or the id is no single path segment."""
    from okf_lint import held_kinds  # noqa: E402
    from okf_profile import PROFILE_30 as P30, canonical_kind, kind_in_force, load_profile, operational_kinds

    if not ident.strip() or ident != ident.strip() or ident in (".", "..") or "/" in ident or "\\" in ident:
        raise Refusal(f"--id '{ident}' must be one directory name (no '/', no surrounding blanks, not '.' or '..')")
    hfm = root_frontmatter(holder)
    if not (holder / "index.md").is_file() or hfm.get("okf_version") is None:
        raise Refusal(f"--in {holder} is not a bundle (no index.md declaring okf_version)")
    if hfm.get("state") == "closed":
        raise Refusal(f"--in {holder} is closed: a closed instance is frozen and nothing in it is edited (standard §2.2)")
    domain, fm = holder, hfm
    for _ in range(32):
        if fm.get("kind") in (None, "Domain Bundle"):
            break
        par = fm.get("parent")
        if not isinstance(par, str) or not par.strip():
            raise Refusal(f"{domain} has no parent, so the domain bundle of its tree cannot be found")
        domain = (domain / par).resolve()
        fm = root_frontmatter(domain)
        if fm.get("okf_version") is None:
            raise Refusal(f"parent {par} is not a bundle (no index.md declaring okf_version)")
    else:
        raise Refusal("no domain bundle within 32 parents")
    prof = load_profile(domain, read_own=declared_profile(domain) == P30)
    ops = operational_kinds(prof)
    k = canonical_kind(prof, kind)
    if k not in ops:
        raise Refusal(f"'{kind}' is no operational kind in force (kinds with a directory: {', '.join(ops) or 'none'})")
    held = held_kinds(hfm, prof)
    if k not in held:
        raise Refusal(f"{holder} does not hold {k} (it holds: {', '.join(held) or 'nothing'})")
    target = holder / kind_in_force(prof, k)["directory"].strip("/") / ident
    if target.exists() and not target.is_dir():
        raise Refusal(f"--id '{ident}' names a file of {target.parent.name}/, not an instance directory")
    return target, k


def write(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"skipped (exists) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"created {path}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--title", required=True, help="project title")
    ap.add_argument("--description", required=True, help="one-sentence project description")
    ap.add_argument("--actor", required=True, help="human:<id> | process:<id> | <agent>/<version>")
    ap.add_argument("--repo-url", default="", help="repository URL for project.md")
    ap.add_argument("--purpose", default="", help="the Purpose of project.md: what problem the project solves and "
                                                  "for whom (default: the description)")
    ap.add_argument("--tags", default="", help="comma-separated tags for project.md")
    ap.add_argument("--dirs", default=None, help="comma-separated typed directories to create under base/ (default: "
                                               f"{','.join(DEFAULT_DIRS)}; none for --instance)")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--okf-version", default="0.2", choices=("0.1", "0.2"),
                    help="OKF version of the bundle (0.1 only to interoperate with older consumers)")
    ap.add_argument("--instance", metavar="KIND", help="open an operational bundle of this kind (ADR-0039)")
    ap.add_argument("--id", dest="ident", help="with --instance: the instance's directory name")
    ap.add_argument("--in", dest="holder", help="with --instance: the bundle that holds it (a domain bundle or an "
                                                "instance)")
    args = ap.parse_args(argv)

    holder = None
    keys = [f'okf_version: "{args.okf_version}"', f'okf_profile: "{PROFILE_30}"']
    if args.instance is not None:
        if args.ident is None or args.holder is None:
            print("--instance needs --id and --in", file=sys.stderr)
            return 2
        if args.okf_version != "0.2":
            print("an operational bundle is OKF v0.2 (knowledge/3.0)", file=sys.stderr)
            return 2
        holder = Path(args.holder).resolve()
        try:
            k, kind = instance_target(holder, args.instance, args.ident)
        except Refusal as e:
            print(f"okf-init: {e}", file=sys.stderr)
            return 2
        keys += [f"kind: {kind}", "state: open", "parent: ../.."]
    else:
        k = Path(args.root).resolve() / "knowledge"
    dirs_arg = args.dirs if args.dirs is not None else ("" if holder is not None else ",".join(DEFAULT_DIRS))
    dirs = [d.strip() for d in dirs_arg.split(",") if d.strip()]
    now = now_iso()
    log = []

    project = render("project.md", title=args.title, one_sentence_description=args.description,
                     repo_url=args.repo_url, tags=args.tags, actor=args.actor, now=now)
    project = set_section(project, "Purpose", (args.purpose or args.description).strip())
    log.append(write(k / "project.md", prune_unfilled(prune_map(project, dirs)), args.force))

    root_idx = ['---', *keys, '---', '',
                '# Project', '', f'* [{args.title}](project.md) - {args.description}', '',
                '# Subdirectories', '']
    for d in (FRAGMENTS_DIR, BASE_DIR):
        root_idx.append(f"* [{d}]({d}/index.md) - {DIR_DESC[d]}")
    log.append(write(k / "index.md", "\n".join(root_idx) + "\n", args.force))

    log.append(write(k / "log.md", render("log.md", date=date.today().isoformat()), args.force))

    def empty_index(path: Path, name: str) -> None:
        desc = DIR_DESC.get(name, f"Concepts in {name}.")
        log.append(write(path / "index.md", f"# {name}\n\n> {desc}\n\n_(empty)_\n", args.force))

    empty_index(k / FRAGMENTS_DIR, FRAGMENTS_DIR)
    empty_index(k / BASE_DIR, BASE_DIR)
    for d in dirs:
        empty_index(k / BASE_DIR / d, d)
        if d == "references":
            for sub in ("skills", "attesters"):
                empty_index(k / BASE_DIR / d / sub, sub)
    log.append(write(k / PROJECTIONS_DIR / ".gitkeep", "", args.force))
    print("\n".join(log))
    # Normalize the indexes with the same generator as okf-index
    from okf_index import main as index_main  # noqa: E402
    if args.okf_version == "0.1":
        from okf_migrate import main as migrate_main  # noqa: E402
        migrate_main([str(k), "--to", "0.1", "--force"])
    index_main([str(k)])
    if holder is not None:
        index_main([str(holder)])
        print(f"\n{kind} instance opened in {k}")
        return 0
    print(f"\nBundle initialized in {k} (OKF v{args.okf_version})")
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_init.py --test)
# --------------------------------------------------------------------------
_ARGS = ["--title", "T", "--description", "D", "--actor", "human:test"]


def test_creates_profile_structure(tmp_path):
    assert main(["--root", str(tmp_path), *_ARGS]) == 0
    k = tmp_path / "knowledge"
    assert (k / "project.md").is_file()
    for d in ("decisions", "policies", "references/skills", "references/attesters"):
        assert (k / "base" / d / "index.md").is_file(), d
    assert 'okf_profile: "knowledge/3.0"' in (k / "index.md").read_text(encoding="utf-8")
    raw, _ = split_frontmatter((k / "project.md").read_text(encoding="utf-8"))
    fm = parse_yaml(raw)
    assert (fm["type"], fm["title"], fm["description"]) == ("Project", "T", "D")
    assert fm["generated"]["by"] == "human:test"


def test_creates_questions_listed_in_base_index(tmp_path):
    assert main(["--root", str(tmp_path), *_ARGS]) == 0
    k = tmp_path / "knowledge"
    assert (k / "base" / "questions" / "index.md").is_file()
    base = (k / "base" / "index.md").read_text(encoding="utf-8")
    assert "* [questions](questions/index.md) - Questions nobody has answered yet, each with an owner." in base
    from okf_index import DIR_DESCRIPTIONS
    assert DIR_DESCRIPTIONS["questions"] == DIR_DESC["questions"]


def test_custom_dirs_leave_questions_out(tmp_path):
    assert main(["--root", str(tmp_path), *_ARGS, "--dirs", "decisions"]) == 0
    assert not (tmp_path / "knowledge" / "base" / "questions").exists()


def test_creates_empty_fragments_without_conflict_log(tmp_path):
    assert main(["--root", str(tmp_path), *_ARGS]) == 0
    k = tmp_path / "knowledge"
    assert (k / "fragments" / "index.md").is_file()
    assert not (k / "conflict-log.md").exists()


def test_creates_3_0_layout(tmp_path):
    assert main(["--root", str(tmp_path), *_ARGS, "--dirs", "decisions,integrations"]) == 0
    k = tmp_path / "knowledge"
    assert sorted(p.name for p in k.iterdir()) == ["base", "fragments", "index.md", "log.md", "project.md",
                                                   "projections"]
    assert sorted(p.name for p in (k / "base").iterdir()) == ["decisions", "index.md", "integrations"]
    assert [p.name for p in (k / "projections").iterdir()] == [".gitkeep"]
    index = (k / "index.md").read_text(encoding="utf-8")
    assert "* [base](base/index.md) - The project's knowledge, in typed directories." in index
    assert "* [fragments](fragments/index.md) - Records of events, distilled into the base." in index
    assert "projections" not in index
    assert "* [decisions](decisions/index.md)" in (k / "base" / "index.md").read_text(encoding="utf-8")
    assert "> The project's knowledge, in typed directories." in (k / "base" / "index.md").read_text(encoding="utf-8")


def test_default_3_0_init_lints_clean(tmp_path):
    from okf_lint import lint

    assert main(["--root", str(tmp_path), *_ARGS]) == 0
    k = tmp_path / "knowledge"
    assert sorted(p.name for p in (k / "base").iterdir()) == sorted(["index.md", *DEFAULT_DIRS])
    assert not (k / "fragments" / "fragments").exists() and not (k / "base" / "fragments").exists()
    rep, _, _ = lint(k)
    assert rep.items == []


def test_a_fresh_bundle_lints_at_0_warnings_under_strict_in_both_versions(tmp_path, capsys):
    from okf_lint import main as lint_main

    for v in ("0.2", "0.1"):
        assert main(["--root", str(tmp_path / v), *_ARGS, "--okf-version", v]) == 0
        capsys.readouterr()
        assert lint_main([str(tmp_path / v / "knowledge"), "--strict"]) == 0, v
        assert " 0 errors · 0 warnings " in capsys.readouterr().out, v


def _project_body(tmp_path, *extra: str) -> str:
    assert main(["--root", str(tmp_path), *_ARGS, *extra]) == 0
    return split_frontmatter((tmp_path / "knowledge" / "project.md").read_text(encoding="utf-8"))[1]


def test_project_md_holds_what_init_knows_and_no_placeholder(tmp_path):
    body = _project_body(tmp_path / "a")
    assert "{{" not in body and "..." not in body and "| |" not in body
    assert "# Purpose\n\nD\n" in body  # the description, without --purpose
    for gone in ("# Scope", "# Team and ownership", "# Key links", "| Board |"):
        assert gone not in body, gone
    assert "# Knowledge map\n\n* [Architecture](/base/architecture/index.md)" in body
    body = _project_body(tmp_path / "b", "--purpose", "Refunds for the shop's buyers.",
                         "--repo-url", "https://github.com/acme/shop")
    assert "# Purpose\n\nRefunds for the shop's buyers.\n" in body
    assert "# Key links\n\n| Resource | URL |\n|---|---|\n| Repository | https://github.com/acme/shop |\n\n" in body
    for gone in ("| Board |", "| Environments |", "| Observability |", "# Scope", "# Team and ownership"):
        assert gone not in body, gone


def test_prune_unfilled_drops_placeholder_lines_header_only_tables_and_emptied_sections():
    text = ("---\ntype: Project\n---\n\n# Purpose\n\nKnown.\n\n# Scope\n\n- In scope: ...\n- Out of scope: ...\n\n"
            "# Team\n\n| Role | Who |\n|---|---|\n| Owner | |\n\n# Links\n\n| Resource | URL |\n|---|---|\n"
            "| Repository | https://x |\n| Board | |\n\n# Notes\n\n{{later}}\n\n## Kept\n\nText.\n")
    assert prune_unfilled(text) == ("---\ntype: Project\n---\n\n# Purpose\n\nKnown.\n\n# Links\n\n"
                                    "| Resource | URL |\n|---|---|\n| Repository | https://x |\n\n# Notes\n\n## Kept\n\n"
                                    "Text.\n")


def test_prune_unfilled_keeps_content_that_holds_braces_code_and_comments():
    text = ("# Purpose\n\nThe chart sets `{{ .Values.image.tag }}` from CI.\n\n# Scope\n\nJinja uses {{ }} delimiters\n"
            "run: echo ${{ secrets.DEPLOY_KEY }}\n\n# Build\n\n```yaml\nimage: {{tag}}\n- ...\n```\n\n"
            "# Notes\n\n<!--\n{{later}}\n-->\nKept.\n")
    assert prune_unfilled(text) == text


def test_does_not_overwrite_without_force(tmp_path):
    main(["--root", str(tmp_path), *_ARGS])
    project = tmp_path / "knowledge" / "project.md"
    project.write_text("edited by hand\n", encoding="utf-8")
    main(["--root", str(tmp_path), *_ARGS])
    assert project.read_text(encoding="utf-8") == "edited by hand\n"


def test_okf_version_01(tmp_path):
    main(["--root", str(tmp_path), *_ARGS, "--okf-version", "0.1"])
    k = tmp_path / "knowledge"
    assert 'okf_version: "0.1"' in (k / "index.md").read_text(encoding="utf-8")
    raw, _ = split_frontmatter((k / "project.md").read_text(encoding="utf-8"))
    fm = parse_yaml(raw)
    assert "timestamp" in fm and "generated" not in fm



# --- --instance: an operational bundle in its kind's directory (standard §2.2, ADR-0039) ---
_INST = ["--title", "R1", "--description", "Refund one.", "--actor", "human:test"]


def _kinds_domain(tmp_path, extra_profile: str = ""):
    from okf_lint import _KINDS_PROFILE, _tree_bundle

    return _tree_bundle(tmp_path / "knowledge", profile=_KINDS_PROFILE + extra_profile)


def _files(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def _codes(k: Path) -> list:
    from okf_lint import lint

    return sorted((i["level"], i["code"], i["path"]) for i in lint(k)[0].items)


def test_instance_opens_a_request_in_its_kind_directory_and_lints_clean(tmp_path):
    k = _kinds_domain(tmp_path)
    assert main(["--instance", "Request", "--id", "r1", "--in", str(k), *_INST]) == 0
    r1 = k / "requests" / "r1"
    assert _files(r1) == ["base", "base/index.md", "fragments", "fragments/index.md", "index.md", "log.md",
                          "project.md", "projections", "projections/.gitkeep"]
    raw, _ = split_frontmatter((r1 / "index.md").read_text(encoding="utf-8"))
    assert parse_yaml(raw) == {"okf_version": "0.2", "okf_profile": "knowledge/3.0", "kind": "Request",
                               "state": "open", "parent": "../.."}
    assert "* [r1](r1/index.md)" in (k / "requests" / "index.md").read_text(encoding="utf-8")
    assert "* [requests](requests/index.md)" in (k / "index.md").read_text(encoding="utf-8")
    assert _codes(k) == []


def test_instance_kind_given_by_a_type_alias_is_written_as_the_declared_id(tmp_path):
    k = _kinds_domain(tmp_path, "aliases:\n  types: { Pedido: Request }\n")
    assert main(["--instance", "Pedido", "--id", "r1", "--in", str(k), *_INST]) == 0
    raw, _ = split_frontmatter((k / "requests" / "r1" / "index.md").read_text(encoding="utf-8"))
    assert parse_yaml(raw)["kind"] == "Request"
    assert _codes(k) == []


def test_instance_opens_inside_an_instance_that_holds_its_kind(tmp_path):
    k = _kinds_domain(tmp_path)
    assert main(["--instance", "Release", "--id", "v1", "--in", str(k), *_INST]) == 0
    assert main(["--instance", "Request", "--id", "r2", "--in", str(k / "releases" / "v1"), *_INST]) == 0
    r2 = k / "releases" / "v1" / "requests" / "r2"
    raw, _ = split_frontmatter((r2 / "index.md").read_text(encoding="utf-8"))
    assert parse_yaml(raw) == {"okf_version": "0.2", "okf_profile": "knowledge/3.0", "kind": "Request",
                               "state": "open", "parent": "../.."}
    assert "* [r2](r2/index.md)" in (k / "releases" / "v1" / "requests" / "index.md").read_text(encoding="utf-8")
    assert _codes(k) == []


def _refused(tmp_path, capsys, holder_rel: str, *extra: str) -> str:
    k = _kinds_domain(tmp_path)
    assert main(["--instance", "Release", "--id", "v1", "--in", str(k), *_INST]) == 0
    before = _files(k)
    capsys.readouterr()
    assert main([*extra, "--in", str(k / holder_rel), *_INST]) == 2
    assert _files(k) == before
    return capsys.readouterr().err


def test_instance_refuses_a_kind_its_holder_does_not_hold(tmp_path, capsys):
    err = _refused(tmp_path, capsys, "releases/v1", "--instance", "Incident", "--id", "i1")
    assert "does not hold Incident (it holds: Request)" in err


def test_instance_refuses_an_unknown_or_abstract_kind(tmp_path, capsys):
    for kind in ("Bug", "Operational Bundle"):
        err = _refused(tmp_path / kind, capsys, "", "--instance", kind, "--id", "x")
        assert "(kinds with a directory: Request, Incident, Release)" in err, kind


def test_instance_refuses_a_holder_that_is_no_bundle(tmp_path, capsys):
    err = _refused(tmp_path, capsys, "base", "--instance", "Request", "--id", "x")
    assert "is not a bundle" in err


def test_instance_refuses_an_id_that_is_no_single_directory_name(tmp_path, capsys):
    for i, ident in enumerate(("", ".", "..", "a/b", "../r")):
        err = _refused(tmp_path / str(i), capsys, "", "--instance", "Request", "--id", ident)
        assert "must be one directory name" in err, ident


def test_instance_refuses_a_blank_id_or_one_naming_a_file_of_the_kind_directory(tmp_path, capsys):
    for i, ident in enumerate((" ", " r1", "index.md")):
        k = _kinds_domain(tmp_path / str(i))
        assert main(["--instance", "Request", "--id", "r0", "--in", str(k), *_INST]) == 0
        before = _files(k)
        capsys.readouterr()
        assert main(["--instance", "Request", "--id", ident, "--in", str(k), *_INST]) == 2, ident
        assert _files(k) == before, ident
        assert "--id" in capsys.readouterr().err, ident


def test_instance_refuses_a_closed_holder(tmp_path, capsys):
    k = _kinds_domain(tmp_path)
    assert main(["--instance", "Release", "--id", "v1", "--in", str(k), *_INST]) == 0
    idx = k / "releases" / "v1" / "index.md"
    idx.write_text(idx.read_text(encoding="utf-8").replace("state: open\n", "state: closed\nclosed_at: "
                                                           "2026-11-12T09:00:00Z\n", 1), encoding="utf-8")
    before = _files(k)
    capsys.readouterr()
    assert main(["--instance", "Request", "--id", "r9", "--in", str(k / "releases" / "v1"), *_INST]) == 2
    assert _files(k) == before
    assert "is closed" in capsys.readouterr().err


def test_instance_over_an_existing_one_skips_its_files(tmp_path):
    k = _kinds_domain(tmp_path)
    assert main(["--instance", "Request", "--id", "r1", "--in", str(k), *_INST]) == 0
    project = k / "requests" / "r1" / "project.md"
    project.write_text(project.read_text(encoding="utf-8").replace("Refund one.\n\n", "Edited.\n\n", 1),
                       encoding="utf-8")
    edited = project.read_text(encoding="utf-8")
    assert main(["--instance", "Request", "--id", "r1", "--in", str(k), *_INST]) == 0
    assert project.read_text(encoding="utf-8") == edited


def test_knowledge_map_links_only_the_directories_created(tmp_path):
    body = _project_body(tmp_path, "--dirs", "questions")
    assert "/base/" not in body and "# Knowledge map" not in body
    assert _codes(tmp_path / "knowledge") == []
    body = _project_body(tmp_path / "b", "--dirs", "decisions,questions")
    assert body.rstrip().endswith("# Knowledge map\n\n* [Decisions](/base/decisions/index.md)")
    assert body.count("/base/") == 1


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
