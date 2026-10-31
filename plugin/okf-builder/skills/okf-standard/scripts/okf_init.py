#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_init.py — Create the knowledge/ structure of the knowledge/2.0 profile (OKF v0.2).

Usage:
    uv run okf_init.py --root /path/to/repo --title "My project" \
        --description "One sentence" --actor human:jisequilla [--repo-url URL] \
        [--dirs architecture,decisions,...] [--force]

Existing files are not overwritten unless --force is given. Idempotent.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import now_iso, parse_yaml, split_frontmatter  # noqa: E402

_HERE = Path(__file__).resolve().parent
TEMPLATES = _HERE.parent / "templates"   # okf-standard/scripts/ → okf-standard/templates/
DEFAULT_DIRS = ["architecture", "decisions", "domain", "systems", "apis", "data",
                "metrics", "computations", "runbooks", "playbooks", "policies", "references", "fragments"]
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
    "references": "Mirrored external material, execution skills and attesters.",
    "fragments": "Knowledge fragments: records of events, before and after distillation.",
    "skills": "Execution instructions (executors) for computations.",
    "attesters": "Deterministic receipt verification code.",
}


def render(name: str, **vars) -> str:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


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
    ap.add_argument("--tags", default="", help="comma-separated tags for project.md")
    ap.add_argument("--dirs", default=",".join(DEFAULT_DIRS), help="comma-separated directories to create")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--okf-version", default="0.2", choices=("0.1", "0.2"),
                    help="OKF version of the bundle (0.1 only to interoperate with older consumers)")
    args = ap.parse_args(argv)

    k = Path(args.root).resolve() / "knowledge"
    dirs = [d.strip() for d in args.dirs.split(",") if d.strip()]
    now = now_iso()
    log = []

    log.append(write(k / "project.md", render(
        "project.md", title=args.title, one_sentence_description=args.description,
        repo_url=args.repo_url, tags=args.tags, actor=args.actor, now=now), args.force))

    root_idx = ['---', f'okf_version: "{args.okf_version}"', 'okf_profile: "knowledge/2.0"', '---', '',
                '# Project', '', f'* [{args.title}](project.md) - {args.description}', '',
                '# Subdirectories', '']
    for d in dirs:
        root_idx.append(f"* [{d}]({d}/index.md) - {DIR_DESC.get(d, f'Concepts in {d}.')}")
    log.append(write(k / "index.md", "\n".join(root_idx) + "\n", args.force))

    log.append(write(k / "log.md", render("log.md", date=date.today().isoformat()), args.force))

    for d in dirs:
        desc = DIR_DESC.get(d, f"Concepts in {d}.")
        log.append(write(k / d / "index.md", f"# {d}\n\n> {desc}\n\n_(empty)_\n", args.force))
        if d == "references":
            for sub in ("skills", "attesters"):
                log.append(write(k / d / sub / "index.md",
                                 f"# {sub}\n\n> {DIR_DESC[sub]}\n\n_(empty)_\n", args.force))
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
        assert (k / d / "index.md").is_file(), d
    assert 'okf_profile: "knowledge/2.0"' in (k / "index.md").read_text(encoding="utf-8")
    raw, _ = split_frontmatter((k / "project.md").read_text(encoding="utf-8"))
    fm = parse_yaml(raw)
    assert (fm["type"], fm["title"], fm["description"]) == ("Project", "T", "D")
    assert fm["generated"]["by"] == "human:test"


def test_creates_empty_fragments_without_conflict_log(tmp_path):
    assert main(["--root", str(tmp_path), *_ARGS]) == 0
    k = tmp_path / "knowledge"
    assert (k / "fragments" / "index.md").is_file()
    assert not (k / "conflict-log.md").exists()


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
