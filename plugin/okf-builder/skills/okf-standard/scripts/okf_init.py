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

Creates the three layers: fragments/ (with its index.md), base/ with one typed
directory per --dirs entry, and projections/ (with only a .gitkeep: it is not OKF).
project.md holds no placeholder: what init knows is filled in (title, description,
repository URL, and Purpose from --purpose or else the description), and the rows
and sections it cannot fill (Scope, Team and ownership, empty Key links rows) are
left out, so a fresh bundle has no SECTION_EMPTY. Existing files are not
overwritten unless --force is given. Idempotent.
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
    now_iso,
    parse_yaml,
    placeholder_line,
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
    ap.add_argument("--dirs", default=",".join(DEFAULT_DIRS), help="comma-separated typed directories to create under base/")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--okf-version", default="0.2", choices=("0.1", "0.2"),
                    help="OKF version of the bundle (0.1 only to interoperate with older consumers)")
    args = ap.parse_args(argv)

    k = Path(args.root).resolve() / "knowledge"
    dirs = [d.strip() for d in args.dirs.split(",") if d.strip()]
    now = now_iso()
    log = []

    project = render("project.md", title=args.title, one_sentence_description=args.description,
                     repo_url=args.repo_url, tags=args.tags, actor=args.actor, now=now)
    project = set_section(project, "Purpose", (args.purpose or args.description).strip())
    log.append(write(k / "project.md", prune_unfilled(project), args.force))

    root_idx = ['---', f'okf_version: "{args.okf_version}"', f'okf_profile: "{PROFILE_30}"', '---', '',
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


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
