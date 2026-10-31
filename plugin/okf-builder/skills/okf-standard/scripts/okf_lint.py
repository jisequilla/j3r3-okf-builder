#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_lint.py — Validate an OKF v0.2 bundle and the knowledge/2.0 profile.

Usage:
    uv run okf_lint.py [path/to/bundle] [--json] [--strict] [--no-profile]

Output: a list of findings with level ERROR / WARN and a code. Exit 1 if there
are errors (or warnings with --strict).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    ACTOR_RE,
    CITATIONS_RE,
    SUPPORTED_VERSIONS,
    V02_KEYS,
    detect_version,
    KEBAB_RE,
    VALID_DISTILLATION,
    VALID_STATUS,
    Doc,
    as_list,
    extract_links,
    find_bundle,
    is_iso,
    is_iso_date_or_datetime,
    resolve_link,
    to_dt,
    walk_bundle,
)


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, code: str, path: str, msg: str) -> None:
        self.items.append({"level": level, "code": code, "path": path, "message": msg})

    def error(self, code, path, msg):
        self.add("ERROR", code, path, msg)

    def warn(self, code, path, msg):
        self.add("WARN", code, path, msg)

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "ERROR"]

    @property
    def warns(self):
        return [i for i in self.items if i["level"] == "WARN"]


def check_index(doc: Doc, bundle: Path, rep: Report, docs_by_path: dict, profile: bool = True) -> None:
    is_root = doc.path.parent.resolve() == bundle.resolve()
    if doc.has_fm_block and not is_root:
        rep.error("INDEX_FM", doc.rel, "index.md outside the root must not have frontmatter (§8)")
    if is_root:
        fm = doc.frontmatter or {}
        if profile and "okf_version" not in fm:
            rep.error("PROFILE_OKF_VERSION", doc.rel, "root index.md must declare okf_version (profile §7.4)")
    body = doc.body
    if not re.search(r"^#\s+\S", body, re.M):
        rep.error("INDEX_STRUCT", doc.rel, "index.md must have at least one '# Title' section (§8)")
    entries = re.findall(r"^\*\s+\[[^\]]+\]\(([^)]+)\)", body, re.M)
    if not entries and "_(empty)_" not in body:
        rep.warn("INDEX_EMPTY", doc.rel, "index.md has no '* [Title](path) - description' entries")
    for e in entries:
        if "#" in e or re.match(r"^[a-z]+:", e):
            continue
        target = resolve_link(bundle, doc, e)
        if target is None:
            continue
        if target.is_dir():
            continue
        if not target.exists():
            rep.warn("INDEX_BROKEN", doc.rel, f"index entry points to a missing file: {e}")
    # Concepts of the directory that are not listed
    listed = set()
    for e in entries:
        t = resolve_link(bundle, doc, e)
        if t is not None:
            listed.add(t.resolve())
            if t.is_dir():
                listed.add((t / "index.md").resolve())
    for p in sorted(doc.path.parent.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_file() and p.suffix == ".md" and p.name not in ("index.md", "log.md"):
            if p.resolve() not in listed:
                rep.warn("INDEX_STALE", doc.rel, f"concept not listed in the index: {p.name}")
        if p.is_dir() and (p / "index.md").exists():
            if (p / "index.md").resolve() not in listed and p.resolve() not in listed:
                rep.warn("INDEX_STALE", doc.rel, f"subdirectory not listed in the index: {p.name}/")


def check_log(doc: Doc, rep: Report) -> None:
    body = doc.body
    dates = re.findall(r"^##\s+(\S+)", body, re.M)
    if not dates:
        rep.error("LOG_STRUCT", doc.rel, "log.md must group entries under '## YYYY-MM-DD' (§9)")
        return
    parsed = []
    for d in dates:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            rep.error("LOG_DATE", doc.rel, f"log date is not ISO 8601 YYYY-MM-DD: {d}")
        else:
            parsed.append(d)
    if parsed != sorted(parsed, reverse=True):
        rep.warn("LOG_ORDER", doc.rel, "log dates must go from newest to oldest")


def check_concept(doc: Doc, bundle: Path, rep: Report, profile: bool, now: datetime, version: str = "0.2") -> None:
    if not doc.has_fm_block:
        rep.error("NO_FRONTMATTER", doc.rel, "concept has no YAML frontmatter block (§11.1)")
        return
    if doc.fm_error:
        rep.error("BAD_YAML", doc.rel, f"YAML frontmatter cannot be parsed: {doc.fm_error}")
        return
    fm = doc.frontmatter or {}
    t = fm.get("type")
    if not t or not str(t).strip():
        rep.error("NO_TYPE", doc.rel, "frontmatter has no non-empty 'type' (§11.2)")
    if "description" not in fm or not fm.get("description"):
        rep.warn("NO_DESCRIPTION", doc.rel, "no 'description' (recommended; it feeds the index.md files)")
    if "title" not in fm:
        rep.warn("NO_TITLE", doc.rel, "no 'title' (recommended)")

    status = fm.get("status")
    if status is not None and status not in VALID_STATUS:
        rep.error("BAD_STATUS", doc.rel, f"status '{status}' is not draft|stable|deprecated (§5.4)")

    has_citations = bool(CITATIONS_RE.search(doc.body))
    if version == "0.2":
        if "timestamp" in fm and "generated" not in fm:
            rep.warn("LEGACY_TIMESTAMP", doc.rel, "'timestamp' is v0.1; migrate it to generated.at (§13.1)")
        if has_citations:
            rep.warn("LEGACY_CITATIONS", doc.rel, "'# Citations' is v0.1; migrate it to 'sources' (§13.1)")
    else:  # 0.1
        v02 = sorted(V02_KEYS & set(fm))
        if v02:
            rep.warn("V02_FIELD_IN_V01", doc.rel, f"v0.2 keys in a 0.1 bundle (kept, not interpreted): {', '.join(v02)}")
        if str(t) == "Attested Computation":
            rep.warn("V02_FIELD_IN_V01", doc.rel, "type 'Attested Computation' is v0.2; in 0.1 it is a generic type")
        ts = fm.get("timestamp")
        if ts is None:
            if profile:
                rep.error("PROFILE_NO_TIMESTAMP", doc.rel, "profile knowledge/2.0 in 0.1 mode requires 'timestamp'")
        elif not is_iso(ts):
            rep.warn("BAD_ISO", doc.rel, f"timestamp '{ts}' is not ISO 8601 with an offset")
        if has_citations:
            m = re.search(r"^#\s+Citations\s*$(.*?)(?=^#\s|\Z)", doc.body, re.M | re.S)
            items = re.findall(r"^\s*(?:\[\d+\]|[-*])\s+\S", m.group(1), re.M) if m else []
            if not items:
                rep.warn("CITATIONS_EMPTY", doc.rel, "'# Citations' has no '[n] ...' or '- ...' entries (v0.1 §8)")

    gen = fm.get("generated")
    if gen is not None:
        if not isinstance(gen, dict) or not gen.get("by"):
            rep.error("BAD_GENERATED", doc.rel, "'generated' requires { by, at } with 'by' (§5.2)")
        else:
            if not ACTOR_RE.match(str(gen["by"])):
                rep.warn("BAD_ACTOR", doc.rel, f"generated.by '{gen['by']}' does not follow the actor convention (§7)")
            if "at" in gen and not is_iso(gen["at"]):
                rep.warn("BAD_ISO", doc.rel, f"generated.at '{gen['at']}' is not ISO 8601 with an offset")
    elif profile and version == "0.2":
        rep.error("PROFILE_NO_GENERATED", doc.rel, "profile knowledge/2.0 requires 'generated: { by, at }'")

    for v in as_list(fm.get("verified")):
        if not isinstance(v, dict) or not v.get("by"):
            rep.error("BAD_VERIFIED", doc.rel, "each 'verified' entry requires { by, at } (§5.2)")
            continue
        if not ACTOR_RE.match(str(v["by"])):
            rep.warn("BAD_ACTOR", doc.rel, f"verified.by '{v['by']}' does not follow the actor convention (§7)")
        if "at" in v and not is_iso(v["at"]):
            rep.warn("BAD_ISO", doc.rel, f"verified.at '{v['at']}' is not ISO 8601 with an offset")

    sa = fm.get("stale_after")
    if sa is not None:
        dt = to_dt(sa)
        if dt is None:
            rep.warn("BAD_ISO", doc.rel, f"stale_after '{sa}' is not ISO 8601 with an offset")
        elif now >= dt and status != "deprecated":
            rep.warn("STALE", doc.rel, f"content stale since {dt.isoformat()} (§5.5): review it, then renew or deprecate it")

    sources = fm.get("sources")
    ids = set()
    if sources is not None:
        if not isinstance(sources, list):
            rep.error("BAD_SOURCES", doc.rel, "'sources' must be a list (§5.1)")
        else:
            for s in sources:
                if not isinstance(s, dict) or not s.get("resource"):
                    rep.error("BAD_SOURCES", doc.rel, "each 'sources' entry requires 'resource' (§5.1)")
                    continue
                if s.get("id"):
                    ids.add(str(s["id"]))
                if "last_modified" in s and not is_iso(s["last_modified"]):
                    rep.warn("BAD_ISO", doc.rel, f"sources[].last_modified '{s['last_modified']}' is not ISO 8601")
    for fn in set(re.findall(r"\[\^([^\]]+)\]", doc.body)):
        if fn not in ids:
            rep.warn("FOOTNOTE_NO_SOURCE", doc.rel, f"footnote [^{fn}] has no matching sources[].id (§5.1)")

    if str(t) == "Attested Computation":
        if not fm.get("runtime"):
            rep.error("AC_NO_RUNTIME", doc.rel, "Attested Computation requires 'runtime' (§10.2)")
        if not fm.get("computation"):
            m = re.search(r"^#\s+Computation\s*$(.*?)(?=^#\s|\Z)", doc.body, re.M | re.S)
            fences = len(re.findall(r"^```", m.group(1), re.M)) // 2 if m else 0
            indented = bool(m and re.search(r"^(    |\t)\S", m.group(1), re.M))
            if not m or (fences != 1 and not indented):
                rep.error("AC_NO_COMPUTATION", doc.rel,
                          "Attested Computation has neither 'computation' nor a single block under '# Computation' (§10.3)")
        for p in as_list(fm.get("parameters")):
            if not isinstance(p, dict) or not p.get("name") or not p.get("type"):
                rep.error("AC_BAD_PARAM", doc.rel, "parameters[] requires { name, type, required } (§10.2)")

    if profile and str(t) == "Knowledge Fragment":
        check_fragment(doc, fm, rep)

    if profile and not KEBAB_RE.match(doc.path.name):
        rep.warn("NAME_KEBAB", doc.rel, "file name is not ASCII kebab-case (profile §2)")

    for link in extract_links(doc.body):
        target = resolve_link(bundle, doc, link)
        if target is None:
            continue
        try:
            target.relative_to(bundle.resolve())
        except ValueError:
            rep.warn("LINK_OUTSIDE", doc.rel, f"link leaves the bundle: {link}")
            continue
        if not target.exists():
            rep.warn("BROKEN_LINK", doc.rel, f"broken link (tolerated by §6.1): {link}")


def _blank(v) -> bool:
    return v is None or (isinstance(v, (str, list, dict)) and not (v.strip() if isinstance(v, str) else v))


def check_fragment(doc: Doc, fm: dict, rep: Report) -> None:
    """Frontmatter of a Knowledge Fragment (ADR-0015); the body sections are not checked."""
    for key in ("occurred_at", "origin", "participants", "distillation_status"):
        if _blank(fm.get(key)):
            rep.warn("FRAGMENT_NO_FIELD", doc.rel, f"Knowledge Fragment has no '{key}' (§4)")
    oa = fm.get("occurred_at")
    if not _blank(oa) and not is_iso_date_or_datetime(oa):
        rep.warn("BAD_ISO", doc.rel, f"occurred_at '{oa}' is neither YYYY-MM-DD nor ISO 8601 with an offset")
    for p in as_list(fm.get("participants")):
        if not ACTOR_RE.match(str(p)):
            rep.warn("BAD_ACTOR", doc.rel, f"participant '{p}' does not follow the actor convention (§7)")
    ds = fm.get("distillation_status")
    if not _blank(ds) and str(ds) not in VALID_DISTILLATION:
        rep.error("BAD_DISTILLATION_STATUS", doc.rel, f"distillation_status '{ds}' is not pending|distilled|conflict (§7)")


def lint(bundle: Path, profile: bool = True, version: str = "auto") -> tuple[Report, str, str]:
    rep = Report()
    now = datetime.now(timezone.utc)
    docs = walk_bundle(bundle)
    by_path = {d.path.resolve(): d for d in docs}

    detected, origin = detect_version(bundle, docs)
    if version == "auto":
        version = detected
    if origin == "mixed":
        rep.warn("MIXED_VERSIONS", "index.md", "concepts mix 0.1 and 0.2 forms and okf_version is missing: bundle half migrated (okf-migrate)")
    if origin == "declared" and detected != version:
        rep.warn("VERSION_MISMATCH", "index.md", f"index.md declares okf_version {detected} but is validated as {version}")
    if origin != "declared" and profile:
        rep.warn("NO_OKF_VERSION", "index.md", f"root index.md has no okf_version; inferred version: {version} ({origin})")

    if profile:
        if not (bundle / "index.md").exists():
            rep.error("PROFILE_NO_INDEX", "index.md", "knowledge/index.md is missing (profile §7.4)")
        if not (bundle / "log.md").exists():
            rep.error("PROFILE_NO_LOG", "log.md", "knowledge/log.md is missing (profile §7.4)")
        proj = bundle / "project.md"
        if not proj.exists():
            rep.error("PROFILE_NO_PROJECT", "project.md", "knowledge/project.md with type: Project is missing (profile §7.4)")
        else:
            d = by_path.get(proj.resolve())
            if d and d.frontmatter and d.frontmatter.get("type") != "Project":
                rep.error("PROFILE_PROJECT_TYPE", "project.md", "project.md must have type: Project")
        types = [d.frontmatter.get("type") for d in docs if d.frontmatter and not d.is_reserved]
        if types.count("Project") > 1:
            rep.error("PROFILE_MANY_PROJECTS", "project.md", "more than one concept has type: Project")
        if types.count("Conflict Log") > 1:
            logs = ", ".join(d.rel for d in docs if d.frontmatter and not d.is_reserved
                             and d.frontmatter.get("type") == "Conflict Log")
            rep.error("PROFILE_MANY_CONFLICT_LOGS", "conflict-log.md", f"more than one concept has type: Conflict Log ({logs})")

    for d in docs:
        if d.path.name == "index.md":
            check_index(d, bundle, rep, by_path, profile)
        elif d.path.name == "log.md":
            if d.has_fm_block and d.frontmatter and d.frontmatter.get("type") not in (None, "Log"):
                rep.warn("LOG_TYPE", d.rel, "log.md with frontmatter should be type: Log, or have no frontmatter")
            check_log(d, rep)
        else:
            check_concept(d, bundle, rep, profile, now, version)
    return rep, version, origin


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="path to the bundle (default: search upwards for knowledge/)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--strict", action="store_true", help="warnings also cause exit 1")
    ap.add_argument("--no-profile", action="store_true", help="validate the OKF spec only, not the knowledge/2.0 profile")
    ap.add_argument("--okf-version", default="auto", choices=("auto", *SUPPORTED_VERSIONS),
                    help="spec version to validate against (auto: okf_version of the root index, or heuristic)")
    args = ap.parse_args(argv)

    bundle = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if bundle is None or not bundle.is_dir():
        print("ERROR: bundle not found (knowledge/index.md). Pass its path.", file=sys.stderr)
        return 2

    rep, version, origin = lint(bundle, profile=not args.no_profile, version=args.okf_version)
    n_docs = len([d for d in walk_bundle(bundle) if not d.is_reserved])
    if args.json:
        print(json.dumps({"bundle": str(bundle), "okf_version": version, "version_origin": origin, "concepts": n_docs, "errors": len(rep.errors),
                          "warnings": len(rep.warns), "findings": rep.items}, ensure_ascii=False, indent=2))
    else:
        for i in rep.items:
            print(f"{i['level']:5} {i['code']:22} {i['path']}: {i['message']}")
        verdict = "CONFORMANT" if not rep.errors else "NOT CONFORMANT"
        print(f"\n{bundle}: OKF {version} ({origin}) · {n_docs} concepts · {len(rep.errors)} errors · {len(rep.warns)} warnings → {verdict}")
    if rep.errors or (args.strict and rep.warns):
        return 1
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_lint.py --test); they also cover okf_common
# --------------------------------------------------------------------------
def _broken_bundle() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        cand = parent / "tests" / "fixtures" / "broken-bundle" / "knowledge"
        if cand.is_dir():
            return cand
    return None


def test_split_frontmatter():
    from okf_common import split_frontmatter

    assert split_frontmatter("---\na: 1\n---\nbody\n") == ("a: 1", "body")
    assert split_frontmatter("no frontmatter\n") == (None, "no frontmatter\n")
    assert split_frontmatter("---\nunclosed: 1\n") == (None, "---\nunclosed: 1\n")
    assert split_frontmatter("----\na: 1\n---\n")[0] is None


def test_parse_yaml_non_dict_is_empty():
    from okf_common import parse_yaml

    assert parse_yaml("- a\n- b\n") == {}
    assert parse_yaml("just a string") == {}
    assert parse_yaml("") == {}
    assert parse_yaml("a: { b: [1, 2] }\n") == {"a": {"b": [1, 2]}}


def test_broken_bundle_fails_with_no_type(capsys):
    import pytest

    bundle = _broken_bundle()
    if bundle is None:
        pytest.skip("tests/fixtures/broken-bundle not present (script copied outside the repo)")
    rep, _, _ = lint(bundle)
    assert [e["code"] for e in rep.errors] == ["NO_TYPE"]
    assert main([str(bundle), "--strict"]) == 1
    assert any(line.startswith("ERROR NO_TYPE ") for line in capsys.readouterr().out.splitlines())


def test_typed_concept_passes(tmp_path):
    (tmp_path / "index.md").write_text("# Terms\n\n* [A](a.md) - An A.\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("---\ntype: Term\ntitle: A\ndescription: An A.\n---\n\nText.\n",
                                   encoding="utf-8")
    rep, _, _ = lint(tmp_path, profile=False)
    assert rep.errors == []


_GEN = "generated: { by: okf-builder/test, at: 2026-10-31T18:00:00Z }\n"
_FRAGMENT = "fragments/2026-10-31-meeting.md"
_FRAGMENT_FIELDS = ("occurred_at: 2026-10-31\norigin: Weekly meeting\n"
                    "participants: [human:alice, okf-builder/claude-opus-5-5]\ndistillation_status: pending\n")
_CONFLICT_LOG = ("---\ntype: Conflict Log\ntitle: Conflict log\ndescription: Conflicts.\nstatus: draft\n" + _GEN +
                 "---\n\n# How it is used\n\nText.\n\n# Conflicts\n\n"
                 "| ID | Source | Description | Kind | Resolution | State | Decided |\n|---|---|---|---|---|---|---|\n")


def _fragment_bundle(tmp_path, fields: str, body: str = "# Record\n\nText.\n\n# Distillation\n\nNone yet.\n",
                     conflict_logs: tuple[str, ...] = ("conflict-log.md",)) -> Path:
    """A complete 0.2 profile bundle with one Knowledge Fragment and the given Conflict Logs."""
    root_entries = "".join(f"* [Conflicts]({c}) - Conflicts.\n" for c in conflict_logs)
    (tmp_path / "index.md").write_text(
        '---\nokf_version: "0.2"\nokf_profile: "knowledge/2.0"\n---\n\n# Project\n\n* [P](project.md) - P.\n'
        + root_entries + "\n# Subdirectories\n\n* [fragments](fragments/index.md) - Fragments.\n", encoding="utf-8")
    (tmp_path / "log.md").write_text("# Bundle history\n\n## 2026-10-31\n* **Creation**: test.\n", encoding="utf-8")
    (tmp_path / "project.md").write_text("---\ntype: Project\ntitle: P\ndescription: P.\n" + _GEN + "---\n\nText.\n",
                                         encoding="utf-8")
    for c in conflict_logs:
        (tmp_path / c).write_text(_CONFLICT_LOG, encoding="utf-8")
    (tmp_path / "fragments").mkdir()
    (tmp_path / "fragments" / "index.md").write_text("# fragments\n\n* [M](2026-10-31-meeting.md) - M.\n",
                                                    encoding="utf-8")
    (tmp_path / _FRAGMENT).write_text("---\ntype: Knowledge Fragment\ntitle: M\ndescription: M.\nstatus: draft\n"
                                      + fields + _GEN + "---\n\n" + body, encoding="utf-8")
    return tmp_path


def _codes(rep: Report, path: str = _FRAGMENT) -> list[tuple[str, str]]:
    return sorted((i["level"], i["code"]) for i in rep.items if i["path"] == path)


def test_is_iso_date_or_datetime():
    from datetime import date
    from okf_common import is_iso_date_or_datetime as ok

    assert ok(date(2026, 10, 31)) and ok("2026-10-31") and ok("2026-10-31T18:28:00+01:00")
    assert ok(datetime(2026, 10, 31, 18, 28, tzinfo=timezone.utc))
    assert not ok(datetime(2026, 10, 31, 18, 28)) and not ok("2026-10-31T18:28:00")
    assert not ok("31/10/2026") and not ok("2026-02-30") and not ok(20261031) and not ok(None)


def test_fragment_with_all_fields_passes(tmp_path):
    rep, _, _ = lint(_fragment_bundle(tmp_path, _FRAGMENT_FIELDS))
    assert rep.items == []


def test_fragment_missing_fields_warn_one_each(tmp_path):
    rep, _, _ = lint(_fragment_bundle(tmp_path, "distillation_status: pending\n"))
    found = [i for i in rep.items if i["path"] == _FRAGMENT]
    assert [(i["level"], i["code"]) for i in found] == [("WARN", "FRAGMENT_NO_FIELD")] * 3
    assert all(any(k in i["message"] for i in found) for k in ("occurred_at", "origin", "participants"))
    assert rep.errors == []


def test_fragment_missing_distillation_status_warns(tmp_path):
    fields = _FRAGMENT_FIELDS.replace("distillation_status: pending\n", "")
    rep, _, _ = lint(_fragment_bundle(tmp_path, fields))
    assert _codes(rep) == [("WARN", "FRAGMENT_NO_FIELD")]


def test_fragment_occurred_at_date_passes(tmp_path):
    rep, _, _ = lint(_fragment_bundle(tmp_path, _FRAGMENT_FIELDS))
    assert _codes(rep) == []


def test_fragment_occurred_at_datetime_with_offset_passes(tmp_path):
    fields = _FRAGMENT_FIELDS.replace("occurred_at: 2026-10-31", "occurred_at: 2026-10-31T18:28:00+01:00")
    rep, _, _ = lint(_fragment_bundle(tmp_path, fields))
    assert _codes(rep) == []


def test_fragment_occurred_at_bad_format_warns(tmp_path):
    for value in ("31/10/2026", "2026-10-31T18:28:00"):
        bundle = tmp_path / value.replace("/", "-").replace(":", "-")
        bundle.mkdir()
        fields = _FRAGMENT_FIELDS.replace("occurred_at: 2026-10-31", f"occurred_at: {value}")
        rep, _, _ = lint(_fragment_bundle(bundle, fields))
        assert _codes(rep) == [("WARN", "BAD_ISO")], value


def test_fragment_participant_not_an_actor_warns(tmp_path):
    fields = _FRAGMENT_FIELDS.replace("[human:alice, ", "[Alice Smith, ")
    rep, _, _ = lint(_fragment_bundle(tmp_path, fields))
    assert _codes(rep) == [("WARN", "BAD_ACTOR")]


def test_fragment_bad_distillation_status_errors(tmp_path):
    fields = _FRAGMENT_FIELDS.replace("distillation_status: pending", "distillation_status: done")
    rep, _, _ = lint(_fragment_bundle(tmp_path, fields))
    assert _codes(rep) == [("ERROR", "BAD_DISTILLATION_STATUS")]


def test_two_conflict_logs_error(tmp_path):
    rep, _, _ = lint(_fragment_bundle(tmp_path, _FRAGMENT_FIELDS, conflict_logs=("conflict-log.md", "conflicts-2.md")))
    assert [i["code"] for i in rep.errors] == ["PROFILE_MANY_CONFLICT_LOGS"]


def test_no_profile_skips_fragment_and_conflict_log_checks(tmp_path):
    fields = "occurred_at: 31/10/2026\nparticipants: [Alice Smith]\ndistillation_status: done\n"
    bundle = _fragment_bundle(tmp_path, fields, conflict_logs=("conflict-log.md", "conflicts-2.md"))
    rep, _, _ = lint(bundle, profile=False)
    assert rep.items == []
    assert main([str(bundle), "--no-profile", "--strict"]) == 0


def test_kdd_style_fragment_warns_only_for_participants(tmp_path):
    fields = ("occurred_at: 2025-04-25T00:00:00+02:00\norigin: \"Presentación AFTI, diapositivas 3-5\"\n"
              "distillation_status: distilled\n")
    body = ("# Contexto de captura\n\n| Campo | Valor |\n|---|---|\n| Fuente | Presentación |\n\n"
            "# Contenido capturado\n\n> Texto tal como aparece.\n\n# Destilado en\n\n* Nada.\n")
    rep, _, _ = lint(_fragment_bundle(tmp_path, fields, body))
    assert [(i["level"], i["code"], i["path"]) for i in rep.items] == [("WARN", "FRAGMENT_NO_FIELD", _FRAGMENT)]
    assert "participants" in rep.items[0]["message"]


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
