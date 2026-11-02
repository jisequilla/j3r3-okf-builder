#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_lint.py — Validate an OKF v0.2 bundle and its knowledge profile (3.0, or the outdated 2.0).

Usage:
    uv run okf_lint.py [path/to/bundle] [--json] [--strict] [--no-profile]
    uv run okf_lint.py <bundle> --profiles [<path>] [--json]

Output: a list of findings with level ERROR / WARN and a code. Exit 1 if there
are errors (or warnings with --strict). Notices are neither and never fail.

In a knowledge/3.0 bundle the Domain Profile (built-in layer, extends,
base/profile.md) must be well formed (okf_profile.py); --profiles lists what is
in force at a path and which source declared each item. Each concept is checked
against the requirements in force for its type that carry their own code: the
built-in profile keeps the per-field checks of a Knowledge Fragment and an Open
Question under their codes and levels. --no-profile applies no Domain Profile.

The profile is the okf_profile of the root index.md; a bundle without one is
treated as knowledge/2.0. A knowledge/2.0 bundle stays valid, and lint prints a
notice (neither a warning nor an error) before the summary line; --json carries
it as "profile_outdated". projections/ at the root is not OKF and is skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    ACTOR_RE,
    CITATIONS_RE,
    DATE_RE,
    SUPPORTED_VERSIONS,
    V02_KEYS,
    detect_version,
    KEBAB_RE,
    LAYER_DIRS,
    PROFILE_20,
    PROFILE_30,
    VALID_STATUS,
    Doc,
    as_list,
    declared_profile,
    extract_links,
    find_bundle,
    is_iso,
    is_iso_date_or_datetime,
    resolve_link,
    to_dt,
    walk_bundle,
)
from okf_profile import (IGNORED_20_NOTICE, Resolved, _lvl, bundle_path, format_in_force, ignored_in_20,  # noqa: E402
                         in_force, is_a, load_profile, misplaced, type_in_force)


OUTDATED_NOTICE = f"profile {PROFILE_20} is outdated: run okf_migrate.py --profile {PROFILE_30}"


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.notices: list[str] = []  # neither warnings nor errors; they never fail --strict
        self.profile_outdated = False

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


def check_concept(doc: Doc, bundle: Path, rep: Report, profile: bool, now: datetime, version: str = "0.2",
                  pname: str = PROFILE_20, prof: Resolved | None = None, forces: dict | None = None) -> None:
    """One concept: the spec-level checks, then, when prof is given, the Domain Profile in force for its type
    (forces caches type_in_force per type)."""
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
                rep.error("PROFILE_NO_TIMESTAMP", doc.rel, f"profile {pname} in 0.1 mode requires 'timestamp'")
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
        rep.error("PROFILE_NO_GENERATED", doc.rel, f"profile {pname} requires 'generated: {{ by, at }}'")

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

    if prof is not None and str(t) in prof.types:
        force = forces.get(str(t)) if forces is not None else None
        if force is None:
            force = type_in_force(prof, str(t))
            if forces is not None:
                forces[str(t)] = force
        check_profile_fields(doc, fm, str(t), prof, force, rep)
        if is_a(prof, str(t), "Open Question"):
            check_review_due(doc, fm, rep, now)

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


def value_ok(ftype: str, v, values: list | None = None) -> bool:
    """A value of one of the field types of §4.1 other than list (a list is checked item by item)."""
    if ftype == "actor":
        return bool(ACTOR_RE.match(str(v)))
    if ftype == "enum":
        return str(v) in [str(x) for x in values or []]
    if ftype == "date_or_datetime":
        return is_iso_date_or_datetime(v)
    if ftype == "datetime":
        return is_iso(v)
    if ftype == "date":
        return (isinstance(v, date) and not isinstance(v, datetime)) or (
            isinstance(v, str) and bool(DATE_RE.match(v)) and is_iso_date_or_datetime(v))
    if ftype == "path":
        return isinstance(v, str) and v.startswith("/")
    if ftype == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if ftype == "boolean":
        return isinstance(v, bool)
    return isinstance(v, str)


def _breach(fid: str, ftype: str, v, values: list, item: bool) -> str:
    label = fid[:-1] if item and fid.endswith("s") else fid  # an item of participants is a participant
    if ftype == "actor":
        return f"{label} '{v}' does not follow the actor convention (§7)"
    if ftype == "enum":
        return f"{label} '{v}' is not {'|'.join(str(x) for x in values)} (§7)"
    if ftype == "date_or_datetime":
        return f"{label} '{v}' is neither YYYY-MM-DD nor ISO 8601 with an offset"
    return f"{label} '{v}' is not a {ftype} (§4.1)"


def _rule_applies(prof: Resolved, t: str, fm: dict, when: dict) -> bool:
    return all(is_a(prof, t, str(v)) if k == "type" else str(fm.get(k)) == str(v) for k, v in when.items())


def check_profile_fields(doc: Doc, fm: dict, t: str, prof: Resolved, force: dict, rep: Report) -> None:
    """The requirements of the Domain Profile in force for type t that carry their own code (§4.1).

    Two passes. First each required field that is missing, a blank value included, in declaration order.
    Then each field's value in declaration order, each field followed by the rules whose first required
    field it is; the rules that require no declared field come last. A blank value of a required scalar
    field is reported once, as missing. A list is checked item by item, a single value as a one-item list,
    so a blank text or map given as a list is missing and also an item of the wrong form."""
    fields, required = force["fields"], force["required"]
    for fid, req in required.items():
        if req.get("code") and _blank(fm.get(fid)):
            owner = fields[fid]["declared_by"] if fid in fields else t
            rep.add(req["level"].upper(), req["code"], doc.rel, f"{owner} has no '{fid}' (§4)")
    rules = [r for r in prof.rules if r.get("code") and _rule_applies(prof, t, fm, r["when"])]

    def check_rules(at: str | None) -> None:
        for r in rules:
            if next((f for f in r["require"] if f in fields), None) != at:
                continue
            cond = " and ".join(f"{k} is {v}" for k, v in r["when"].items() if k != "type")
            for f in r["require"]:
                if _blank(fm.get(f)):
                    rep.add(_lvl(r).upper(), r["code"], doc.rel, f"{cond} but '{f}' is missing (§4)")

    for fid, d in fields.items():
        v = fm.get(fid)
        item = d.get("type") == "list"
        if d.get("code") and v is not None and (item or not (d.get("required") and _blank(v))):
            ftype = d.get("of") if item else d.get("type")
            values = [x["value"] for x in d.get("values") or []]
            for x in (as_list(v) if item else [v]):
                if not value_ok(ftype, x, values):
                    rep.add(_lvl(d).upper(), d["code"], doc.rel, _breach(fid, ftype, x, values, item))
        check_rules(fid)
    check_rules(None)


def utc_date(v) -> date | None:
    """The UTC calendar date of a YYYY-MM-DD or an ISO 8601 datetime with an offset; None otherwise."""
    if not is_iso_date_or_datetime(v):
        return None
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).date()
    if isinstance(v, date):
        return v
    if DATE_RE.match(v):
        return date.fromisoformat(v)
    try:
        return to_dt(v).astimezone(timezone.utc).date()
    except (ValueError, AttributeError):
        return None


def check_review_due(doc: Doc, fm: dict, rep: Report, now: datetime) -> None:
    """An open question past its review_on (ADR-0026 decision 6); the form of review_on is a profile check."""
    ro = fm.get("review_on")
    due = utc_date(ro) if ro is not None else None
    if due is not None and str(fm.get("question_status")) == "open" and due < now.date():
        rep.warn("QUESTION_REVIEW_DUE", doc.rel, f"open question due for review since {due.isoformat()}")


def check_layers(docs: list[Doc], rep: Report) -> None:
    """knowledge/3.0: concepts live in base/ or fragments/; the root holds project.md and the Conflict Log."""
    for d in docs:
        parts = d.rel.split("/")
        if len(parts) == 1:
            t = (d.frontmatter or {}).get("type")
            if d.is_reserved or (d.rel == "project.md" and t == "Project") or t == "Conflict Log":
                continue
            rep.error("PROFILE_OUTSIDE_LAYER", d.rel,
                      f"profile {PROFILE_30}: a concept at the root must live in base/ or fragments/")
        elif parts[0] not in LAYER_DIRS:
            rep.error("PROFILE_OUTSIDE_LAYER", d.rel,
                      f"profile {PROFILE_30}: {parts[0]}/ is not a layer; move it under base/")


def profile_structure(bundle: Path, docs: list[Doc]) -> tuple[Resolved, list[dict], list[str]]:
    """The Domain Profile in force, its structural findings (§7 rule 14) and its notices; lint and --profiles share it."""
    if declared_profile(bundle) == PROFILE_30:
        prof = load_profile(bundle, read_own=True)
        return prof, prof.findings + misplaced(docs, prof), []
    return load_profile(bundle, read_own=False), [], [IGNORED_20_NOTICE.format(rel=rel) for rel in ignored_in_20(docs)]


def lint(bundle: Path, profile: bool = True, version: str = "auto") -> tuple[Report, str, str]:
    rep = Report()
    now = datetime.now(timezone.utc)
    docs = walk_bundle(bundle)
    by_path = {d.path.resolve(): d for d in docs}
    declared = declared_profile(bundle)
    pname = declared or PROFILE_20
    prof = None  # --no-profile: no Domain Profile, the built-in one included
    if profile:
        rep.profile_outdated = pname == PROFILE_20
        if declared == PROFILE_30:
            check_layers(docs, rep)
        prof, findings, notices = profile_structure(bundle, docs)
        for i in findings:
            rep.add(i["level"], i["code"], i["path"], i["message"])
        rep.notices += notices

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

    forces: dict = {}
    for d in docs:
        if d.path.name == "index.md":
            check_index(d, bundle, rep, by_path, profile)
        elif d.path.name == "log.md":
            if d.has_fm_block and d.frontmatter and d.frontmatter.get("type") not in (None, "Log"):
                rep.warn("LOG_TYPE", d.rel, "log.md with frontmatter should be type: Log, or have no frontmatter")
            check_log(d, rep)
        else:
            check_concept(d, bundle, rep, profile, now, version, pname, prof, forces)
    return rep, version, origin


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="path to the bundle (default: search upwards for knowledge/)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--strict", action="store_true", help="warnings also cause exit 1")
    ap.add_argument("--no-profile", action="store_true", help="validate the OKF spec only, not the knowledge profile")
    ap.add_argument("--okf-version", default="auto", choices=("auto", *SUPPORTED_VERSIONS),
                    help="spec version to validate against (auto: okf_version of the root index, or heuristic)")
    ap.add_argument("--profiles", nargs="?", const="/", metavar="PATH",
                    help="list the Domain Profile in force at PATH (a bundle path such as /base/clients/, or a "
                         "file or directory inside the bundle; default /) and which source declared each item")
    args = ap.parse_args(argv)

    bundle = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if bundle is None or not bundle.is_dir():
        print("ERROR: bundle not found (knowledge/index.md). Pass its path.", file=sys.stderr)
        return 2
    if args.profiles is not None:
        if args.no_profile:
            print("ERROR: --profiles lists the Domain Profile and --no-profile turns every one off; pass one of them",
                  file=sys.stderr)
            return 2
        prof, findings, notices = profile_structure(bundle, walk_bundle(bundle))
        info = {**in_force(prof, bundle_path(bundle, args.profiles)), "findings": findings, "notices": notices}
        print(json.dumps(info, ensure_ascii=False, indent=2, default=str) if args.json else format_in_force(info))
        return 1 if findings else 0

    rep, version, origin = lint(bundle, profile=not args.no_profile, version=args.okf_version)
    n_docs = len([d for d in walk_bundle(bundle) if not d.is_reserved])
    if args.json:
        print(json.dumps({"bundle": str(bundle), "okf_version": version, "version_origin": origin, "concepts": n_docs, "errors": len(rep.errors),
                          "warnings": len(rep.warns), "profile_outdated": rep.profile_outdated, "notices": rep.notices,
                          "findings": rep.items},
                         ensure_ascii=False, indent=2))
    else:
        for i in rep.items:
            print(f"{i['level']:5} {i['code']:22} {i['path']}: {i['message']}")
        for n in rep.notices:
            print(f"NOTICE {n}")
        if rep.profile_outdated:
            print(f"NOTICE {OUTDATED_NOTICE}")
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
                     conflict_logs: tuple[str, ...] = ("conflict-log.md",), profile: str = "knowledge/2.0") -> Path:
    """A complete 0.2 profile bundle with one Knowledge Fragment and the given Conflict Logs."""
    root_entries = "".join(f"* [Conflicts]({c}) - Conflicts.\n" for c in conflict_logs)
    (tmp_path / "index.md").write_text(
        f'---\nokf_version: "0.2"\nokf_profile: "{profile}"\n---\n\n# Project\n\n* [P](project.md) - P.\n'
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


def test_impossible_datetimes_warn_bad_iso(tmp_path):
    """A datetime that matches the ISO pattern but names no real moment warns BAD_ISO; it never crashes lint."""
    for n, line in enumerate(('stale_after: "2026-02-30T00:00:00Z"\n',
                              'verified: { by: human:alice, at: "2026-13-40T09:00:00+00:00" }\n')):
        bundle = tmp_path / str(n)
        bundle.mkdir()
        rep, _, _ = lint(_fragment_bundle(bundle, _FRAGMENT_FIELDS + line))
        assert _codes(rep) == [("WARN", "BAD_ISO")], line
    bundle = tmp_path / "generated"
    bundle.mkdir()
    k = _fragment_bundle(bundle, _FRAGMENT_FIELDS)
    f = k / _FRAGMENT
    f.write_text(f.read_text(encoding="utf-8").replace("at: 2026-10-31T18:00:00Z", 'at: "2026-11-01T25:00:00Z"'), encoding="utf-8")
    rep, _, _ = lint(k)
    assert _codes(rep) == [("WARN", "BAD_ISO")]


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


def _bundle_30(tmp_path) -> Path:
    """A clean knowledge/3.0 bundle: one fragment, the Conflict Log at the root, an empty base/."""
    k = _fragment_bundle(tmp_path, _FRAGMENT_FIELDS, profile=PROFILE_30)
    index = k / "index.md"
    index.write_text(index.read_text(encoding="utf-8") + "* [base](base/index.md) - Base.\n", encoding="utf-8")
    (k / "base").mkdir()
    (k / "base" / "index.md").write_text("# base\n\n_(empty)_\n", encoding="utf-8")
    return k


def test_30_bundle_passes(tmp_path):
    rep, _, _ = lint(_bundle_30(tmp_path))
    assert rep.items == [] and not rep.profile_outdated


def test_30_concept_outside_layer_errors(tmp_path):
    k = _bundle_30(tmp_path)
    (k / "decisions").mkdir()
    (k / "decisions" / "x.md").write_text("---\ntype: Architecture Decision\ntitle: X\ndescription: X.\n" + _GEN
                                          + "---\n\nText.\n", encoding="utf-8")
    (k / "loose.md").write_text("---\ntype: Term\ntitle: L\ndescription: L.\n" + _GEN + "---\n\nText.\n",
                                encoding="utf-8")
    (k / ".hidden").mkdir()
    (k / ".hidden" / "y.md").write_text("no frontmatter\n", encoding="utf-8")
    (k / "notes.txt").write_text("not markdown\n", encoding="utf-8")
    rep, _, _ = lint(k)
    outside = sorted((i["path"], i["level"]) for i in rep.items if i["code"] == "PROFILE_OUTSIDE_LAYER")
    assert outside == [("decisions/x.md", "ERROR"), ("loose.md", "ERROR")]
    assert all("knowledge/3.0" in i["message"] for i in rep.items if i["code"] == "PROFILE_OUTSIDE_LAYER")


def test_20_bundle_has_no_layer_check(tmp_path):
    k = _fragment_bundle(tmp_path, _FRAGMENT_FIELDS)
    (k / "loose.md").write_text("---\ntype: Term\ntitle: L\ndescription: L.\n" + _GEN + "---\n\nText.\n",
                                encoding="utf-8")
    rep, _, _ = lint(k)
    assert not [i for i in rep.items if i["code"] == "PROFILE_OUTSIDE_LAYER"]


def _domain_profile(keys: str) -> str:
    return ("---\ntype: Domain Profile\ntitle: Domain Profile\ndescription: The taxonomy.\nstatus: draft\n" + keys
            + _GEN + "---\n\n# What this bundle holds\n\nText.\n")


_BROKEN_PROFILES = {
    "PROFILE_INVALID": ("types:\n  T:\n    fields:\n      f: { type: text }\n", {}),
    "PROFILE_DUPLICATE_ID": ("types:\n  Term: {}\n", {}),
    "PROFILE_REDEFINED": ("types:\n  Contract:\n    extends: Term\n    fields:\n      signed_on: { type: date }\n"
                          "  Supplier Contract:\n    extends: Contract\n    fields:\n      signed_on: { type: date }\n", {}),
    "PROFILE_UNREADABLE": ('extends: ["https://example.com/acme/profile.md"]\n', {}),
    "PROFILE_MISPLACED": ("types: {}\n", {"base/other/profile.md": "types: {}\n"}),
}


def test_lint_and_profiles_report_each_structural_finding_of_the_domain_profile(tmp_path, capsys):
    import json as _json

    for code, (keys, extra) in _BROKEN_PROFILES.items():
        (tmp_path / code).mkdir()
        k = _bundle_30(tmp_path / code)
        for rel, text in {"base/profile.md": keys, **extra}.items():
            (k / rel).parent.mkdir(parents=True, exist_ok=True)
            (k / rel).write_text(_domain_profile(text), encoding="utf-8")
        rep, _, _ = lint(k)
        assert ("ERROR", code) in {(i["level"], i["code"]) for i in rep.items}, (code, rep.items)
        capsys.readouterr()
        assert main([str(k)]) == 1, code
        assert f"ERROR {code}" in capsys.readouterr().out, code
        assert main([str(k), "--json"]) == 1, code
        assert code in {i["code"] for i in _json.loads(capsys.readouterr().out)["findings"]}, code
        # --profiles reports the same structural findings, so the two agree on the exit code
        assert main([str(k), "--profiles"]) == 1, code
        assert f"ERROR {code}" in capsys.readouterr().out, code
        assert main([str(k), "--profiles", "--json"]) == 1, code
        found = {(i["code"], i["path"]) for i in _json.loads(capsys.readouterr().out)["findings"]}
        assert found == {(i["code"], i["path"]) for i in rep.items if i["code"].startswith("PROFILE_")}, code


def test_profiles_in_a_20_bundle_gives_the_ignore_notice(tmp_path, capsys):
    import json as _json

    k = _fragment_bundle(tmp_path, _FRAGMENT_FIELDS)
    (k / "base").mkdir()
    (k / "base" / "profile.md").write_text(_domain_profile("types:\n  T:\n    fields:\n      f: { type: text }\n"),
                                           encoding="utf-8")
    capsys.readouterr()
    assert main([str(k), "--profiles"]) == 0
    assert "NOTICE Domain Profile base/profile.md ignored" in capsys.readouterr().out
    assert main([str(k), "--profiles", "--json"]) == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["findings"] == [] and data["notices"] == [IGNORED_20_NOTICE.format(rel="base/profile.md")]


def test_30_projections_are_skipped(tmp_path, capsys):
    k = _bundle_30(tmp_path)
    proj = k / "projections" / "deck"
    (proj / "render").mkdir(parents=True)
    (proj / "projection.yaml").write_text("lifecycle: [unclosed\n", encoding="utf-8")
    (proj / "content.md").write_text("no frontmatter, [broken](/nowhere.md)\n", encoding="utf-8")
    (proj / "render" / "index.md").write_text("---\nbad: [\n---\n", encoding="utf-8")
    rep, _, _ = lint(k)
    assert rep.items == []
    assert main([str(k), "--strict"]) == 0
    assert " 3 concepts " in capsys.readouterr().out


def test_20_notice_and_profile_outdated(tmp_path, capsys):
    import json as _json

    k = _fragment_bundle(tmp_path, _FRAGMENT_FIELDS)
    assert main([str(k), "--strict"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-3] == "NOTICE profile knowledge/2.0 is outdated: run okf_migrate.py --profile knowledge/3.0"
    assert " 0 errors " in out[-1]
    assert main([str(k), "--json"]) == 0
    assert _json.loads(capsys.readouterr().out)["profile_outdated"] is True
    assert main([str(k), "--no-profile"]) == 0
    assert "outdated" not in capsys.readouterr().out
    assert main([str(k), "--no-profile", "--json"]) == 0
    assert _json.loads(capsys.readouterr().out)["profile_outdated"] is False


def test_missing_profile_is_outdated_20(tmp_path, capsys):
    import json as _json

    k = _fragment_bundle(tmp_path, _FRAGMENT_FIELDS)
    index = k / "index.md"
    index.write_text(index.read_text(encoding="utf-8").replace('okf_profile: "knowledge/2.0"\n', ""), encoding="utf-8")
    assert main([str(k), "--json"]) == 0
    assert _json.loads(capsys.readouterr().out)["profile_outdated"] is True


def test_30_json_profile_outdated_false(tmp_path, capsys):
    import json as _json

    assert main([str(_bundle_30(tmp_path)), "--json"]) == 0
    out = capsys.readouterr().out
    assert _json.loads(out)["profile_outdated"] is False and "NOTICE" not in out


def test_profile_messages_name_the_declared_profile(tmp_path):
    k = _bundle_30(tmp_path)
    frag = k / _FRAGMENT
    frag.write_text(frag.read_text(encoding="utf-8").replace(_GEN, ""), encoding="utf-8")
    rep, _, _ = lint(k)
    [msg] = [i["message"] for i in rep.items if i["code"] == "PROFILE_NO_GENERATED"]
    assert msg == "profile knowledge/3.0 requires 'generated: { by, at }'"


_QUESTION = "base/questions/who-approves-refunds.md"
_QUESTION_FIELDS = "owner: human:alice\nquestion_status: open\nasked_in: /fragments/2026-10-31-meeting.md\n"
_BAD_QUESTION = "owner: Alice\nquestion_status: closed\nreview_on: next week\n"


def _question_bundle(tmp_path, fields: str, profile: str = PROFILE_30) -> Path:
    """A clean bundle with one Open Question: under base/questions/ in 3.0, under questions/ in 2.0."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    if profile == PROFILE_30:
        k, qdir = _bundle_30(tmp_path), "base/questions"
        (k / "base" / "index.md").write_text("# Subdirectories\n\n* [questions](questions/index.md) - Questions.\n",
                                             encoding="utf-8")
    else:
        k, qdir = _fragment_bundle(tmp_path, _FRAGMENT_FIELDS), "questions"
        index = k / "index.md"
        index.write_text(index.read_text(encoding="utf-8") + "* [questions](questions/index.md) - Questions.\n",
                         encoding="utf-8")
    (k / qdir).mkdir()
    (k / qdir / "index.md").write_text("# Open questions\n\n* [Q](who-approves-refunds.md) - Q.\n", encoding="utf-8")
    (k / qdir / "who-approves-refunds.md").write_text(
        "---\ntype: Open Question\ntitle: Q\ndescription: Q.\nstatus: draft\n" + fields + _GEN
        + "---\n\n# Question\n\nWho approves refunds?\n", encoding="utf-8")
    return k


def _qcodes(tmp_path, fields: str, profile: str = PROFILE_30, path: str = _QUESTION) -> list[tuple[str, str]]:
    """Findings of the question; asserts the rest of the bundle stays clean."""
    rep, _, _ = lint(_question_bundle(tmp_path, fields, profile))
    assert [i for i in rep.items if i["path"] != path] == []
    return _codes(rep, path)


def _json_codes(capsys, k: Path, exit_code: int) -> set[tuple[str, str]]:
    import json as _json

    assert main([str(k), "--json"]) == exit_code
    return {(i["level"], i["code"]) for i in _json.loads(capsys.readouterr().out)["findings"] if i["path"] == _QUESTION}


def test_question_with_all_fields_passes(tmp_path):
    assert _qcodes(tmp_path, _QUESTION_FIELDS + "blocks: [/base/decisions/x.md]\nreview_on: 2999-01-01\n") == []


def test_question_missing_fields_warn_one_each(tmp_path):
    rep, _, _ = lint(_question_bundle(tmp_path, ""))
    found = [i for i in rep.items if i["path"] == _QUESTION]
    assert [(i["level"], i["code"]) for i in found] == [("WARN", "QUESTION_NO_FIELD")] * 3
    assert all(any(k in i["message"] for i in found) for k in ("owner", "question_status", "asked_in"))
    assert rep.errors == []


def test_question_missing_asked_in_only_warns(tmp_path):
    fields = _QUESTION_FIELDS.replace("asked_in: /fragments/2026-10-31-meeting.md\n", "")
    assert _qcodes(tmp_path, fields) == [("WARN", "QUESTION_NO_FIELD")]


def test_question_bad_status_errors(tmp_path):
    fields = _QUESTION_FIELDS.replace("question_status: open", "question_status: closed")
    assert _qcodes(tmp_path, fields) == [("ERROR", "BAD_QUESTION_STATUS")]


def test_question_owner_not_an_actor_warns(tmp_path):
    fields = _QUESTION_FIELDS.replace("owner: human:alice", "owner: Alice")
    assert _qcodes(tmp_path, fields) == [("WARN", "BAD_ACTOR")]


def test_question_answered_without_answered_by_warns(tmp_path):
    fields = _QUESTION_FIELDS.replace("question_status: open", "question_status: answered")
    assert _qcodes(tmp_path / "a", fields) == [("WARN", "QUESTION_NO_ANSWER")]
    assert _qcodes(tmp_path / "b", fields + "answered_by: /base/decisions/x.md\n") == []


def test_question_review_due_only_while_open(tmp_path):
    from datetime import timedelta

    today = datetime.now(timezone.utc).date()
    yesterday = (today - timedelta(days=1)).isoformat()
    due = [("WARN", "QUESTION_REVIEW_DUE")]
    cases = [("open", yesterday, due), ("open", f'"{yesterday}"', due), ("open", "2020-01-01T09:00:00+01:00", due),
             ("open", today.isoformat(), []), ("open", "2999-01-01", []),
             ("answered", "2020-01-01", []), ("dropped", "2020-01-01", [])]
    for n, (qs, review_on, expected) in enumerate(cases):
        fields = (_QUESTION_FIELDS.replace("question_status: open", f"question_status: {qs}")
                  + f"review_on: {review_on}\n" + ("answered_by: /base/x.md\n" if qs == "answered" else ""))
        assert _qcodes(tmp_path / str(n), fields) == expected, (qs, review_on)


def test_question_review_on_bad_format_warns(tmp_path):
    for n, value in enumerate(("next week", "2026-11-10T09:00:00", '"2026-02-30"',
                               '"2026-02-30T09:00:00Z"', '"2026-13-40T09:00:00+00:00"', '"2026-11-01T25:00:00Z"')):
        assert _qcodes(tmp_path / str(n), _QUESTION_FIELDS + f"review_on: {value}\n") == [("WARN", "BAD_ISO")], value


def test_question_frontmatter_paths_are_not_link_checked(tmp_path):
    """Lint resolves body links only, never frontmatter paths (sources included): a missing target adds nothing."""
    fields = (_QUESTION_FIELDS.replace("question_status: open", "question_status: answered")
              .replace("/fragments/2026-10-31-meeting.md", "/fragments/missing.md")
              + "blocks: [/base/missing.md]\nanswered_by: /base/missing-answer.md\n")
    assert _qcodes(tmp_path, fields) == []


def test_question_in_20_bundle_gets_the_same_checks(tmp_path):
    assert _qcodes(tmp_path, _BAD_QUESTION, PROFILE_20, "questions/who-approves-refunds.md") == [
        ("ERROR", "BAD_QUESTION_STATUS"), ("WARN", "BAD_ACTOR"), ("WARN", "BAD_ISO"), ("WARN", "QUESTION_NO_FIELD")]


def test_question_codes_in_json(tmp_path, capsys):
    assert _json_codes(capsys, _question_bundle(tmp_path / "a", _BAD_QUESTION), 1) == {
        ("ERROR", "BAD_QUESTION_STATUS"), ("WARN", "BAD_ACTOR"), ("WARN", "BAD_ISO"), ("WARN", "QUESTION_NO_FIELD")}
    answered = _QUESTION_FIELDS.replace("question_status: open", "question_status: answered")
    assert _json_codes(capsys, _question_bundle(tmp_path / "b", answered), 0) == {("WARN", "QUESTION_NO_ANSWER")}
    due = _QUESTION_FIELDS + "review_on: 2020-01-01\n"
    assert _json_codes(capsys, _question_bundle(tmp_path / "c", due), 0) == {("WARN", "QUESTION_REVIEW_DUE")}


def test_no_profile_skips_question_checks(tmp_path):
    rep, _, _ = lint(_question_bundle(tmp_path, _BAD_QUESTION), profile=False)
    assert rep.items == []


def test_value_ok_for_each_field_type():
    from datetime import date as _date

    cases = {
        "string": (["x"], [1, None]), "integer": ([3], [True, "3"]), "boolean": ([False], ["no"]),
        "date": ([_date(2026, 11, 2), "2026-11-02"], ["2026-02-30", "2026-11-02T10:00:00Z", datetime(2026, 11, 2)]),
        "datetime": (["2026-11-02T10:00:00+01:00"], ["2026-11-02", "2026-11-02T10:00:00"]),
        "date_or_datetime": (["2026-11-02", "2026-11-02T10:00:00Z"], ["2026-11-02T10:00:00", "next week"]),
        "actor": (["human:a", "process:b", "okf-builder/x"], ["Alice", "a/b/c"]),
        "path": (["/base/x.md"], ["base/x.md", 1]),
    }
    for ftype, (good, bad) in cases.items():
        assert all(value_ok(ftype, v) for v in good), ftype
        assert not any(value_ok(ftype, v) for v in bad), ftype
    assert value_ok("enum", "open", ["open", "answered"]) and not value_ok("enum", "closed", ["open"])


def _with_own_profile(k: Path, keys: str) -> Path:
    (k / "base" / "profile.md").write_text(_domain_profile(keys), encoding="utf-8")
    (k / "base" / "index.md").write_text("# base\n\n* [Profile](profile.md) - The taxonomy.\n", encoding="utf-8")
    return k


def test_a_local_type_gets_the_checks_of_the_standard_type_it_extends(tmp_path):
    k = _with_own_profile(_bundle_30(tmp_path), "types:\n  Client Meeting:\n    extends: Knowledge Fragment\n")
    frag = k / _FRAGMENT
    frag.write_text(frag.read_text(encoding="utf-8").replace("type: Knowledge Fragment", "type: Client Meeting")
                    .replace("origin: Weekly meeting\n", "").replace("distillation_status: pending", "distillation_status: done"),
                    encoding="utf-8")
    rep, _, _ = lint(k)
    assert [(i["level"], i["code"], i["message"]) for i in rep.items] == [
        ("WARN", "FRAGMENT_NO_FIELD", "Knowledge Fragment has no 'origin' (§4)"),
        ("ERROR", "BAD_DISTILLATION_STATUS", "distillation_status 'done' is not pending|distilled|conflict (§7)")]


def test_enum_values_a_bundle_adds_are_accepted_and_named(tmp_path):
    k = _with_own_profile(_bundle_30(tmp_path), "by_type:\n  Knowledge Fragment: { values: { distillation_status: [archived] } }\n")
    frag = k / _FRAGMENT
    text = frag.read_text(encoding="utf-8")
    frag.write_text(text.replace("distillation_status: pending", "distillation_status: archived"), encoding="utf-8")
    assert lint(k)[0].items == []
    frag.write_text(text.replace("distillation_status: pending", "distillation_status: done"), encoding="utf-8")
    [msg] = [i["message"] for i in lint(k)[0].items]
    assert msg == "distillation_status 'done' is not pending|distilled|conflict|archived (§7)"


def test_profiles_lists_the_builtin_layer_with_its_codes(tmp_path, capsys):
    import json as _json

    k = _bundle_30(tmp_path)
    capsys.readouterr()
    assert main([str(k), "--profiles", "/fragments/"]) == 0
    out = capsys.readouterr().out
    assert "sources: built-in" in out and "type Knowledge Fragment  [built-in]" in out
    assert "  required participants (warn, code FRAGMENT_NO_FIELD)  [built-in]" in out
    assert "  field distillation_status: enum [pending, distilled, conflict], level error  [built-in]" in out
    assert "rule answered-question-names-its-answer" in out
    assert main([str(k), "--profiles", "--json"]) == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["types"]["Open Question"]["fields"]["owner"]["code"] == "BAD_ACTOR"
    assert {t["source"] for t in data["types"].values()} == {"built-in"}


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
