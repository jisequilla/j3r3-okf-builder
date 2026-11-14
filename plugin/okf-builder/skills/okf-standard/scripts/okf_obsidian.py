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
- The views read the bundle's Domain Profile in force (knowledge/3.0: the built-in one, the profiles it extends and
  base/profile.md). A view column or filter on a field the profile gives local names to (field aliases, value aliases
  whose `to` sets it) reads the formula okf_<field>: the declared field, else each local name in sorted order, each
  value alias written as a test (`==`, strict, unlike lint's string match); a value alias whose `from` holds the field
  itself is tested before it, as lint replaces it. Decisions takes every type that is a Decision: Decision, the
  types that extend it (Architecture Decision, a bundle's local decision types) and the type aliases of each; By
  type and the type columns read okf_type, which maps each type alias to its declared type. generated.by and
  generated.at are nested keys and are read as written, not through aliases. A bundle whose profile has none of
  these gets KNOWLEDGE_BASE byte for byte.
- A Domain Profile that cannot be read (any PROFILE_* finding), or a bundle that is not knowledge/3.0, gets the views
  with the built-in names and one line on stderr saying so.
- Never overwrites an existing file unless given --force; prints `created <path>`, `rewritten <path>` (with --force)
  or `skipped (exists) <path>` for each file. The content depends only on the Domain Profile, written with sorted
  names and no timestamps, so a run is deterministic and, on the same profile, idempotent; rerun with --force after
  changing an alias or a local type.
- Exit: 2, writing nothing, when the bundle has no index.md or a path the setup needs is taken by something else
  (`.obsidian` as a file, `knowledge.base` as a directory); else 0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from okf_common import PROFILE_30, declared_profile  # noqa: E402
from okf_profile import DECISION, Resolved, _subtypes, is_a, load_profile  # noqa: E402

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
        - or:
            - "type == \\"Decision\\""
            - "type == \\"Architecture Decision\\""
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

# The decision types of the built-in Domain Profile, for a bundle whose own profile is not read
BUILTIN_DECISIONS = [DECISION, "Architecture Decision"]
# The built-in fields the views name, in the order their formulas are written
VIEW_FIELDS = ("decision_status", "description", "distillation_status", "occurred_at", "origin", "participants",
               "stale_after", "status", "title", "type")


def _js(s: str) -> str:
    """A string literal of a Bases expression, also a YAML double-quoted scalar."""
    return json.dumps(s, ensure_ascii=False)


def _lit(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    return _js(str(v))


def _note(key: str) -> str:
    return f"note[{_js(key)}]"


def _chain(steps: list[tuple[str, str]], last: str = '""') -> str:
    """if(c1, v1, if(c2, v2, ... last))."""
    out = last
    for cond, val in reversed(steps):
        out = f"if({cond}, {val}, {out})"
    return out


def _test(frm: dict) -> str:
    return " && ".join(f"{_note(k)} == {_lit(v)}" for k, v in frm.items())


def view_names(r: Resolved | None) -> tuple[dict, dict, str, list[str]]:
    """What the views read for the Domain Profile r: (formulas okf_* → expression, built-in field → the name a view
    reads, the expression the Decisions filter compares, the type names that filter accepts)."""
    formulas: dict = {}
    if r is None:
        return formulas, {f: f for f in VIEW_FIELDS}, "type", list(BUILTIN_DECISIONS)
    for f in VIEW_FIELDS:
        local = sorted(n for n, a in r.aliases["fields"].items() if a["to"] == f)
        values = [va for va in r.aliases["values"] if f in va["to"]]
        if not local and not values:
            continue
        own = [(_test(va["from"]), _lit(va["to"][f])) for va in values if f in va["from"]]
        rest = [(_test(va["from"]), _lit(va["to"][f])) for va in values if f not in va["from"]]
        formulas[f"okf_{f}"] = _chain(own + [(x, x) for x in (f, *map(_note, local))] + rest)
    as_written = formulas.get("okf_type", "type")
    type_aliases = sorted(r.aliases["types"].items())
    if type_aliases:
        formulas["okf_type"] = _chain([(f"{as_written} == {_js(n)}", _js(a["to"])) for n, a in type_aliases],
                                      last=as_written)
    reads = {f: f"formula.okf_{f}" if f"okf_{f}" in formulas else f for f in VIEW_FIELDS}
    others = set(_subtypes(r, DECISION)) | {n for n, a in r.aliases["types"].items() if is_a(r, a["to"], DECISION)}
    return formulas, reads, reads["type"] if as_written != "type" else "type", [DECISION, *sorted(others)]


def render_base(r: Resolved | None) -> str:
    """knowledge.base for the Domain Profile r; with no aliases and no local type extending Decision (or r None),
    KNOWLEDGE_BASE."""
    formulas, n, typed, decisions = view_names(r)
    decision_filter = ["        - or:", *(f"            - {_js(f'{typed} == {_js(t)}')}" for t in decisions)]
    stale = n["stale_after"]
    lines = [
        "filters:", "  and:", '    - file.ext == "md"', '    - file.basename != "index"', '    - file.basename != "log"',
        "formulas:", "  author: generated.by", "  written: generated.at",
        f'  stale_in_days: if({stale}, (date({stale}) - today()).days.round(0), "")',
        *(f"  {k}: {_js(v)}" for k, v in sorted(formulas.items())),
        "properties:",
        "  formula.author:", "    displayName: Written by",
        "  formula.written:", "    displayName: Written at",
        "  formula.stale_in_days:", "    displayName: Days to stale",
        *(x for k in sorted(formulas) for x in (f"  formula.{k}:", f"    displayName: {k[4:]}")),
        "views:",
        "  - type: table", "    name: Decisions", "    filters:", "      and:", '        - file.inFolder("base")',
        *decision_filter,
        "    groupBy:", f"      property: {n['decision_status']}", "      direction: ASC",
        "    order:", "      - file.name", f"      - {n['title']}", f"      - {n['decision_status']}",
        f"      - {n['status']}", "      - formula.written",
        "  - type: table", "    name: Awaiting human review", "    filters:", "      and:",
        '        - file.inFolder("base")', f'        - {n["status"]} == "draft"',
        "    order:", "      - file.name", f"      - {n['type']}", "      - formula.author", "      - formula.written",
        "  - type: table", "    name: By type", "    filters:", "      and:", '        - file.inFolder("base")',
        "    groupBy:", f"      property: {n['type']}", "      direction: ASC",
        "    order:", "      - file.name", f"      - {n['description']}", f"      - {n['status']}",
        "  - type: table", "    name: Going stale", "    filters:", "      and:", '        - file.inFolder("base")',
        f"        - {stale}",
        "    order:", "      - file.name", f"      - {n['type']}", f"      - {stale}", "      - formula.stale_in_days",
        "  - type: table", "    name: Fragments", "    filters:", "      and:", '        - file.inFolder("fragments")',
        "    groupBy:", f"      property: {n['distillation_status']}", "      direction: ASC",
        "    order:", "      - file.name", f"      - {n['occurred_at']}", f"      - {n['origin']}",
        f"      - {n['participants']}",
    ]
    return "\n".join(lines) + "\n"


def bundle_profile(root: Path) -> tuple[Resolved | None, str | None]:
    """The Domain Profile the views read, or None with the stderr line that says why the built-in names are used."""
    declared = declared_profile(root)
    if declared != PROFILE_30:
        return None, (f"okf_obsidian: the views name the built-in Domain Profile's fields: profile "
                      f"{declared or '(none declared)'} reads no Domain Profile")
    try:
        r = load_profile(root)
    except Exception as e:  # noqa: BLE001
        return None, f"okf_obsidian: the views name the built-in Domain Profile's fields: the profile cannot be read: {e}"
    if r.findings:
        f = r.findings[0]
        more = f" (and {len(r.findings) - 1} more)" if len(r.findings) > 1 else ""
        return None, (f"okf_obsidian: the views name the built-in Domain Profile's fields: the Domain Profile cannot "
                      f"be read: {f['code']} {f['path']}: {f['message']}{more}; see okf_lint.py --profiles")
    return r, None


def write(path: Path, content: str, force: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return f"skipped (exists) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"{'rewritten' if existed else 'created'} {path}"


def blocked(root: Path) -> list[str]:
    """The paths the setup needs that something else holds: a parent that is not a directory, a target that is one."""
    out = []
    for rel in FILES:
        target = root / rel
        if target.parent.exists() and not target.parent.is_dir():
            out.append(f"{target.parent} is not a directory")
        elif target.is_dir():
            out.append(f"{target} is a directory")
    return sorted(set(out))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="bundle root, the directory that holds index.md")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args(argv)

    root = Path(args.bundle).resolve()
    if not (root / "index.md").is_file():
        sys.stderr.write(f"okf_obsidian: {root} is not an OKF bundle (no index.md)\n")
        return 2
    taken = blocked(root)
    if taken:
        for msg in taken:
            sys.stderr.write(f"okf_obsidian: {msg}; nothing written\n")
        return 2
    prof, why = bundle_profile(root)
    if why:
        sys.stderr.write(why + "\n")
    files = {**FILES, "knowledge.base": render_base(prof)}
    for rel, content in files.items():
        print(write(root / rel, content, args.force))
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_obsidian.py --test): each builds a temporary bundle
# --------------------------------------------------------------------------
def _bundle(tmp_path: Path) -> Path:
    b = tmp_path / "knowledge"
    b.mkdir(parents=True)
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
    assert out == [f"skipped (exists) {b / '.obsidian/app.json'}", f"created {b / '.obsidian/.gitignore'}",
                   f"created {b / 'knowledge.base'}"]
    assert (b / ".obsidian/app.json").read_text(encoding="utf-8") == own
    assert (b / ".obsidian/.gitignore").read_text(encoding="utf-8") == GITIGNORE
    assert (b / "knowledge.base").read_text(encoding="utf-8") == KNOWLEDGE_BASE


def test_force_rewrites_all_three(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / ".obsidian").mkdir()
    for rel in FILES:
        (b / rel).write_text("edited\n", encoding="utf-8")
    assert main([str(b), "--force"]) == 0
    assert capsys.readouterr().out.splitlines() == [f"rewritten {b / rel}" for rel in FILES]
    assert _snapshot(b) == {rel: content.encode("utf-8") for rel, content in FILES.items()}


def test_force_on_a_fresh_bundle_reports_created(tmp_path, capsys):
    b = _bundle(tmp_path)
    assert main([str(b), "--force"]) == 0
    assert capsys.readouterr().out.splitlines() == [f"created {b / rel}" for rel in FILES]


def test_taken_paths_are_exit_2_and_write_nothing(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / ".obsidian").write_text("not a directory\n", encoding="utf-8")
    (b / "knowledge.base").mkdir()
    assert main([str(b), "--force"]) == 2
    err = capsys.readouterr().err
    assert f"{b / '.obsidian'} is not a directory" in err and f"{b / 'knowledge.base'} is a directory" in err
    assert (b / ".obsidian").read_text(encoding="utf-8") == "not a directory\n"
    assert sorted(p.name for p in b.iterdir()) == [".obsidian", "index.md", "knowledge.base"]
    assert list((b / "knowledge.base").iterdir()) == []


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
        "Decisions": (['file.inFolder("base")', {"or": ['type == "Decision"', 'type == "Architecture Decision"']}],
                      "decision_status",
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


_GEN = "generated: { by: test/agent, at: 2026-11-06T00:00:00Z }\n"


def _with_profile(tmp_path: Path, keys: str) -> Path:
    b = _bundle(tmp_path)
    (b / "base").mkdir()
    (b / "base/profile.md").write_text("---\ntype: Domain Profile\ntitle: P\ndescription: The taxonomy.\nstatus: draft\n"
                                       + keys.rstrip("\n") + "\n" + _GEN + "---\n\n# What this bundle holds\n\nText.\n",
                                       encoding="utf-8")
    return b


def _base_of(b: Path, capsys=None) -> tuple[dict, str]:
    import yaml

    assert main([str(b), "--force"]) == 0
    if capsys is not None:
        assert capsys.readouterr().err == ""
    raw = (b / "knowledge.base").read_text(encoding="utf-8")
    return yaml.safe_load(raw), raw


def _views(base: dict) -> dict:
    return {v["name"]: v for v in base["views"]}


def test_a_bundle_without_aliases_gets_knowledge_base_byte_for_byte(tmp_path, capsys):
    no_profile = _bundle(tmp_path / "a")
    # a local type that extends a type that is no Decision, and a field of its own: nothing the views read
    plain = _with_profile(tmp_path / "b", "types:\n  Client Meeting:\n    extends: Knowledge Fragment\n    fields:\n"
                                          "      client: { type: string }\n")
    for b in (no_profile, plain):
        assert _base_of(b, capsys)[1] == KNOWLEDGE_BASE, b
    this_repo = Path(__file__).resolve().parents[5] / "knowledge"
    if (this_repo / "knowledge.base").is_file():  # this repository's own bundle, when the script runs from it
        r, why = bundle_profile(this_repo)
        assert why is None and render_base(r) == (this_repo / "knowledge.base").read_text(encoding="utf-8")


def test_a_field_alias_is_read_through_a_formula(tmp_path, capsys):
    b = _with_profile(tmp_path, 'aliases:\n  fields: { "estado de decisión": decision_status }\n')
    base, _ = _base_of(b, capsys)
    assert base["formulas"]["okf_decision_status"] == (
        'if(decision_status, decision_status, if(note["estado de decisión"], note["estado de decisión"], ""))')
    assert base["properties"]["formula.okf_decision_status"] == {"displayName": "decision_status"}
    d = _views(base)["Decisions"]
    assert d["groupBy"]["property"] == "formula.okf_decision_status"
    assert d["order"] == ["file.name", "title", "formula.okf_decision_status", "status", "formula.written"]
    # several local names for one field are chained in sorted order
    b2 = _with_profile(tmp_path / "two", "aliases:\n  fields: { zona: origin, area: origin }\n")
    base2, _ = _base_of(b2, capsys)
    assert base2["formulas"]["okf_origin"] == (
        'if(origin, origin, if(note["area"], note["area"], if(note["zona"], note["zona"], "")))')
    assert _views(base2)["Fragments"]["order"] == ["file.name", "occurred_at", "formula.okf_origin", "participants"]


def test_value_aliases_map_to_the_declared_values(tmp_path, capsys):
    b = _with_profile(tmp_path, "aliases:\n  values:\n"
                                "    - { from: { ingerido: true }, to: { distillation_status: distilled } }\n"
                                "    - { from: { ingerido: false }, to: { distillation_status: pending } }\n"
                                "    - { from: { fase: 3, origen: chat }, to: { distillation_status: pending } }\n")
    base, _ = _base_of(b, capsys)
    assert base["formulas"]["okf_distillation_status"] == (
        'if(distillation_status, distillation_status, if(note["ingerido"] == true, "distilled", '
        'if(note["ingerido"] == false, "pending", if(note["fase"] == 3 && note["origen"] == "chat", "pending", ""))))')
    assert _views(base)["Fragments"]["groupBy"]["property"] == "formula.okf_distillation_status"
    # a value alias whose from holds the field itself replaces it (resolve_aliases), so it is tested first
    b2 = _with_profile(tmp_path / "own", "aliases:\n  values:\n"
                                         "    - { from: { decision_status: aceptado }, to: { decision_status: accepted } }\n")
    base2, _ = _base_of(b2, capsys)
    assert base2["formulas"]["okf_decision_status"] == (
        'if(note["decision_status"] == "aceptado", "accepted", if(decision_status, decision_status, ""))')


def test_type_aliases_and_local_subtypes_join_decisions_and_by_type(tmp_path, capsys):
    b = _with_profile(tmp_path, "types:\n  Product ADR:\n    extends: Architecture Decision\n"
                                "aliases:\n  types: { Decisión: Architecture Decision, ADR de producto: Product ADR, "
                                "Glosario: Glossary }\n")
    base, _ = _base_of(b, capsys)
    v = _views(base)
    assert v["Decisions"]["filters"] == {"and": ['file.inFolder("base")', {"or": [
        'type == "Decision"', 'type == "ADR de producto"', 'type == "Architecture Decision"', 'type == "Decisión"',
        'type == "Product ADR"']}]}
    assert base["formulas"]["okf_type"] == (
        'if(type == "ADR de producto", "Product ADR", if(type == "Decisión", "Architecture Decision", '
        'if(type == "Glosario", "Glossary", type)))')
    assert v["By type"]["groupBy"]["property"] == "formula.okf_type"
    assert v["Awaiting human review"]["order"][1] == v["Going stale"]["order"][1] == "formula.okf_type"
    # a local subtype alone joins Decisions but needs no mapping
    b2 = _with_profile(tmp_path / "sub", "types:\n  Product ADR:\n    extends: Architecture Decision\n")
    base2, _ = _base_of(b2, capsys)
    assert _views(base2)["Decisions"]["filters"]["and"][1] == {
        "or": ['type == "Decision"', 'type == "Architecture Decision"', 'type == "Product ADR"']}
    assert "okf_type" not in base2["formulas"] and _views(base2)["By type"]["groupBy"]["property"] == "type"


# --- Decisions accepts every type that is a Decision (SDR-0026) ---
_STANDARD_DECISION = ("types:\n  Standard Decision:\n    extends: Decision\n    description: A decision about the standard\n"
                      "    directory: /base/decisions/standard/\n    prefix: SDR\n")


def _decisions_view(b: Path, capsys) -> dict:
    return _views(_base_of(b, capsys)[0])["Decisions"]


def test_decisions_accepts_decision_and_every_type_that_extends_it(tmp_path, capsys):
    rest = {"groupBy": {"property": "decision_status", "direction": "ASC"},
            "order": ["file.name", "title", "decision_status", "status", "formula.written"]}
    # a bundle that declares a local decision type
    assert _decisions_view(_with_profile(tmp_path / "local", _STANDARD_DECISION), capsys) == {
        "type": "table", "name": "Decisions", **rest,
        "filters": {"and": ['file.inFolder("base")', {"or": [
            'type == "Decision"', 'type == "Architecture Decision"', 'type == "Standard Decision"']}]}}
    # a bundle with no local decision type, with or without a base/profile.md
    for b in (_bundle(tmp_path / "none"), _with_profile(tmp_path / "plain", "types:\n  Note: { description: A note }\n")):
        assert _decisions_view(b, capsys) == {
            "type": "table", "name": "Decisions", **rest,
            "filters": {"and": ['file.inFolder("base")', {"or": [
                'type == "Decision"', 'type == "Architecture Decision"']}]}}, b


def test_an_alias_of_any_decision_type_joins_decisions(tmp_path, capsys):
    b = _with_profile(tmp_path, _STANDARD_DECISION + "aliases:\n  types: { Decisión: Decision, Norma: Standard Decision, "
                                                     "Glosario: Glossary }\n")
    assert _decisions_view(b, capsys)["filters"] == {"and": ['file.inFolder("base")', {"or": [
        'type == "Decision"', 'type == "Architecture Decision"', 'type == "Decisión"', 'type == "Norma"',
        'type == "Standard Decision"']}]}
    # the alias of Decision alone
    b2 = _with_profile(tmp_path / "one", "aliases:\n  types: { Decisión: Decision }\n")
    assert _decisions_view(b2, capsys)["filters"] == {"and": ['file.inFolder("base")', {"or": [
        'type == "Decision"', 'type == "Architecture Decision"', 'type == "Decisión"']}]}


def test_aliases_of_status_and_stale_after_feed_filters_and_formulas(tmp_path, capsys):
    b = _with_profile(tmp_path, "aliases:\n  fields: { estado: status, caduca: stale_after, tipo: type }\n")
    base, _ = _base_of(b, capsys)
    v = _views(base)
    assert v["Awaiting human review"]["filters"]["and"][1] == 'formula.okf_status == "draft"'
    assert v["Going stale"]["filters"]["and"][1] == "formula.okf_stale_after"
    assert base["formulas"]["stale_in_days"] == (
        'if(formula.okf_stale_after, (date(formula.okf_stale_after) - today()).days.round(0), "")')
    # a field alias of type: Decisions compares the coalesced type
    assert v["Decisions"]["filters"]["and"][1] == {
        "or": ['formula.okf_type == "Decision"', 'formula.okf_type == "Architecture Decision"']}


def test_names_with_quotes_colons_and_hashes_stay_valid_yaml(tmp_path, capsys):
    names = ['di "x"', "a: b", "c #d", "back\\slash"]
    fields = ", ".join(f"{json.dumps(n)}: decision_status" for n in names)
    b = _with_profile(tmp_path, f"types:\n  Product ADR:\n    extends: Architecture Decision\n"
                                f"aliases:\n  fields: {{ {fields} }}\n  types: {{ \"tipo: #1 \\\"q\\\"\": Product ADR }}\n")
    base, _ = _base_of(b, capsys)
    formula = base["formulas"]["okf_decision_status"]
    for n in names:
        assert f"note[{json.dumps(n, ensure_ascii=False)}]" in formula, n
    assert f'type == {json.dumps("tipo: #1 " + chr(34) + "q" + chr(34))}' in _views(base)["Decisions"]["filters"]["and"][1]["or"]


def test_an_unreadable_profile_gets_the_built_in_names_and_one_line(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base").mkdir()
    (b / "base/profile.md").write_text("---\ntype: Domain Profile\naliases: [not, a, map]\n---\n\nText.\n", encoding="utf-8")
    assert main([str(b)]) == 0
    err = capsys.readouterr().err.splitlines()
    assert len(err) == 1 and "PROFILE_INVALID" in err[0] and "built-in" in err[0]
    assert (b / "knowledge.base").read_text(encoding="utf-8") == KNOWLEDGE_BASE
    # a knowledge/2.0 bundle reads no Domain Profile, even with aliases
    old = tmp_path / "old"
    old.mkdir()
    (old / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\n---\n\n# K\n', encoding="utf-8")
    (old / "base").mkdir()
    (old / "base/profile.md").write_text("---\ntype: Domain Profile\naliases: { fields: { estado: status } }\n---\n",
                                         encoding="utf-8")
    assert main([str(old)]) == 0
    err = capsys.readouterr().err.splitlines()
    assert len(err) == 1 and "knowledge/2.0" in err[0]
    assert (old / "knowledge.base").read_text(encoding="utf-8") == KNOWLEDGE_BASE


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
