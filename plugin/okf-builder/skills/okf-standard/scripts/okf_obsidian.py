#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_obsidian.py — Write the Obsidian viewer setup of a bundle (ADR-0032): workspace configuration for one tool,
neither a knowledge projection nor a platform package.

Usage:
    uv run okf_obsidian.py path/to/bundle [--force]

- Writes, at the bundle root (the directory that holds index.md), which Obsidian opens as the vault:
  - .obsidian/app.json: Markdown links in relative form, updated on rename (useMarkdownLinks, newLinkFormat,
    alwaysUpdateLinks), so the links to a renamed file stay valid;
  - .obsidian/.gitignore: everything in .obsidian/ but app.json and itself, so git keeps the setting and not each
    reader's window state, graph, theme or plugins;
  - knowledge.base: five Bases views, four over base/ (Decisions, Awaiting human review, By type, Going stale) and
    one over fragments/ (Fragments), with index.md and log.md left out.
- Never overwrites an existing file unless given --force; prints `created <path>` or `skipped (exists) <path>` for
  each file. The content is fixed text, so a run is deterministic and idempotent.
- Exit: 2, writing nothing, when the bundle has no index.md; else 0.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

APP_JSON = """{
  "useMarkdownLinks": true,
  "newLinkFormat": "relative",
  "alwaysUpdateLinks": true
}"""

GITIGNORE = """*
!app.json
!.gitignore
"""

KNOWLEDGE_BASE = """filters:
  and:
    - file.ext == "md"
    - file.basename != "index"
    - file.basename != "log"
formulas:
  author: generated.by
  written: generated.at
  stale_in_days: if(stale_after, (date(stale_after) - today()).days.round(0), "")
properties:
  formula.author:
    displayName: Written by
  formula.written:
    displayName: Written at
  formula.stale_in_days:
    displayName: Days to stale
views:
  - type: table
    name: Decisions
    filters:
      and:
        - file.inFolder("base")
        - type == "Architecture Decision"
    groupBy:
      property: decision_status
      direction: ASC
    order:
      - file.name
      - title
      - decision_status
      - status
      - formula.written
  - type: table
    name: Awaiting human review
    filters:
      and:
        - file.inFolder("base")
        - status == "draft"
    order:
      - file.name
      - type
      - formula.author
      - formula.written
  - type: table
    name: By type
    filters:
      and:
        - file.inFolder("base")
    groupBy:
      property: type
      direction: ASC
    order:
      - file.name
      - description
      - status
  - type: table
    name: Going stale
    filters:
      and:
        - file.inFolder("base")
        - stale_after
    order:
      - file.name
      - type
      - stale_after
      - formula.stale_in_days
  - type: table
    name: Fragments
    filters:
      and:
        - file.inFolder("fragments")
    groupBy:
      property: distillation_status
      direction: ASC
    order:
      - file.name
      - occurred_at
      - origin
      - participants
"""

FILES = {
    ".obsidian/app.json": APP_JSON,
    ".obsidian/.gitignore": GITIGNORE,
    "knowledge.base": KNOWLEDGE_BASE,
}


def write(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"skipped (exists) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"created {path}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="bundle root, the directory that holds index.md")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args(argv)

    root = Path(args.bundle).resolve()
    if not (root / "index.md").is_file():
        sys.stderr.write(f"okf_obsidian: {root} is not an OKF bundle (no index.md)\n")
        return 2
    for rel, content in FILES.items():
        print(write(root / rel, content, args.force))
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_obsidian.py --test): each builds a temporary bundle
# --------------------------------------------------------------------------
def _bundle(tmp_path: Path) -> Path:
    b = tmp_path / "knowledge"
    b.mkdir()
    (b / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n---\n\n# K\n', encoding="utf-8")
    return b


def _snapshot(b: Path) -> dict[str, bytes]:
    return {rel: (b / rel).read_bytes() for rel in FILES}


def test_creates_the_three_files(tmp_path, capsys):
    b = _bundle(tmp_path)
    assert main([str(b)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [f"created {b / rel}" for rel in FILES]
    assert _snapshot(b) == {rel: content.encode("utf-8") for rel, content in FILES.items()}
    assert (b / ".obsidian/.gitignore").read_text(encoding="utf-8").splitlines() == ["*", "!app.json", "!.gitignore"]


def test_second_run_skips_and_leaves_bytes(tmp_path, capsys):
    b = _bundle(tmp_path)
    assert main([str(b)]) == 0
    before = _snapshot(b)
    capsys.readouterr()
    assert main([str(b)]) == 0
    assert capsys.readouterr().out.splitlines() == [f"skipped (exists) {b / rel}" for rel in FILES]
    assert _snapshot(b) == before


def test_existing_app_json_left_untouched(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / ".obsidian").mkdir()
    own = '{"vimMode": true}\n'
    (b / ".obsidian/app.json").write_text(own, encoding="utf-8")
    assert main([str(b)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"skipped (exists) {b / '.obsidian/app.json'}"
    assert (b / ".obsidian/app.json").read_text(encoding="utf-8") == own
    assert (b / ".obsidian/.gitignore").read_text(encoding="utf-8") == GITIGNORE
    assert (b / "knowledge.base").read_text(encoding="utf-8") == KNOWLEDGE_BASE


def test_force_rewrites_all_three(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / ".obsidian").mkdir()
    for rel in FILES:
        (b / rel).write_text("edited\n", encoding="utf-8")
    assert main([str(b), "--force"]) == 0
    assert capsys.readouterr().out.splitlines() == [f"created {b / rel}" for rel in FILES]
    assert _snapshot(b) == {rel: content.encode("utf-8") for rel, content in FILES.items()}


def test_no_index_is_exit_2_and_writes_nothing(tmp_path, capsys):
    assert main([str(tmp_path)]) == 2
    assert str(tmp_path.resolve()) in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_base_has_the_five_views_by_layer(tmp_path):
    import yaml

    b = _bundle(tmp_path)
    main([str(b)])
    base = yaml.safe_load((b / "knowledge.base").read_text(encoding="utf-8"))
    # Bases' file.name drops the extension, so index.md and log.md are left out by basename
    assert base["filters"] == {"and": ['file.ext == "md"', 'file.basename != "index"', 'file.basename != "log"']}
    assert len(base["views"]) == 5
    views = {v["name"]: v for v in base["views"]}
    # ADR-0032 decision 3: (filters, groupBy property or None, columns) per view
    adr = {
        "Decisions": (['file.inFolder("base")', 'type == "Architecture Decision"'], "decision_status",
                      ["file.name", "title", "decision_status", "status", "formula.written"]),
        "Awaiting human review": (['file.inFolder("base")', 'status == "draft"'], None,
                                  ["file.name", "type", "formula.author", "formula.written"]),
        "By type": (['file.inFolder("base")'], "type", ["file.name", "description", "status"]),
        "Going stale": (['file.inFolder("base")', "stale_after"], None,
                        ["file.name", "type", "stale_after", "formula.stale_in_days"]),
        "Fragments": (['file.inFolder("fragments")'], "distillation_status",
                      ["file.name", "occurred_at", "origin", "participants"]),
    }
    assert list(views) == list(adr)
    for name, (filters, group, order) in adr.items():
        v = views[name]
        assert v["type"] == "table", name
        assert v["filters"] == {"and": filters}, name
        assert (v.get("groupBy") or {}).get("property") == group, name
        assert v["order"] == order, name


def test_app_json_keeps_links_relative_and_updated(tmp_path):
    import json

    b = _bundle(tmp_path)
    main([str(b)])
    raw = (b / ".obsidian/app.json").read_text(encoding="utf-8")
    want = {"useMarkdownLinks": True, "newLinkFormat": "relative", "alwaysUpdateLinks": True}
    assert json.loads(raw) == want
    # Obsidian saves app.json as JSON.stringify(settings, null, 2), with no final newline; any other bytes are
    # rewritten when a reader opens the vault, leaving the committed file modified
    assert raw == json.dumps(want, indent=2)


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
