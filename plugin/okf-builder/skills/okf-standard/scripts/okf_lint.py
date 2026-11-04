#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_lint.py — Validate an OKF v0.2 bundle and its knowledge profile (3.0, or the outdated 2.0).

Usage:
    uv run okf_lint.py [path/to/bundle] [--json] [--strict] [--no-profile] [--run-validators]
    uv run okf_lint.py <bundle> --profiles [<path>] [--json]

Output: a list of findings with level ERROR / WARN and a code. Exit 1 if there
are errors (or warnings with --strict). Notices are neither and never fail.

In a knowledge/3.0 bundle the Domain Profile (built-in layer, extends,
base/profile.md) must be well formed (okf_profile.py); --profiles lists what is
in force at a path and which source declared each item, the questions the
profile maps included (every one, at any path). Each concept is checked,
aliases resolved first, against what is in force for its type and its directory:
a requirement with its own code under that code (the built-in profile keeps the
per-field checks of a Knowledge Fragment and an Open Question that way), one
without a code under PROFILE_REQUIRED, PROFILE_ENUM, PROFILE_FORBIDDEN,
PROFILE_FIXED, PROFILE_RULE, PROFILE_TYPE_NOT_ALLOWED or PROFILE_FIELD_TYPE, and,
with a base/profile.md, each undeclared key as PROFILE_UNKNOWN_KEY; --json names
the source of each. In a bundle without a base/profile.md, the built-in profile's
items without a code are not reported. A validator's command runs
only with --run-validators (PROFILE_VALIDATOR when it fails, its output masked);
without it each one is a notice. --no-profile applies no Domain Profile.

The profile is the okf_profile of the root index.md; a bundle without one is
treated as knowledge/2.0. A knowledge/2.0 bundle stays valid, and lint prints a
notice (neither a warning nor an error) before the summary line; --json carries
it as "profile_outdated". projections/ at the root is not OKF and is skipped.

Each finding names its rule layer (--json "layer"): spec (OKF v0.1/v0.2, all that
runs under --no-profile), okf-profile (knowledge/3.0 or 2.0) or domain-profile
(the Domain Profile in force); the summary counts errors/warnings per rule layer.
An okf_profile okf-builder does not ship gets the spec checks only: what the other
two rule layers find is one notice and is listed under "skipped". Lint does not
read what .okfignore at the root matches ("ignored"), a nested bundle (a
subdirectory whose index.md declares okf_version) or a non-OKF directory (no
index.md, no Markdown file with a type or a title); each of the last two is a notice.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shlex
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    ACTOR_RE,
    BASE_DIR,
    CITATIONS_RE,
    FRAGMENTS_DIR,
    RESERVED_PATHS,
    DATE_RE,
    SUPPORTED_VERSIONS,
    V02_KEYS,
    declared_version,
    detect_version,
    KEBAB_RE,
    LAYER_DIRS,
    PROFILE_20,
    PROFILE_30,
    VALID_STATUS,
    Doc,
    as_list,
    body_sections,
    content_lines,
    declared_profile,
    extract_links,
    find_bundle,
    is_iso,
    is_iso_date_or_datetime,
    resolve_link,
    scan_bundle,
    to_dt,
    walk_bundle,
)
from okf_profile import (BUILTIN, DOMAIN_PROFILE, IGNORED_20_NOTICE, OWN_REL, PROFILE_KEYS, SPEC_KEYS,  # noqa: E402
                         Resolved, _lvl, alias_keys, ancestors, bundle_path, canonical_type, concept_force, families_at,
                         format_in_force, ignored_in_20, in_force, is_a, load_profile, misplaced, resolve_aliases)


OUTDATED_NOTICE = f"profile {PROFILE_20} is outdated: run okf_migrate.py --profile {PROFILE_30}"


SPEC, OKF_PROFILE, DOMAIN = "spec", "okf-profile", "domain-profile"
RULE_LAYERS = (SPEC, OKF_PROFILE, DOMAIN)
# The codes of the knowledge profile itself (knowledge/3.0 or 2.0): lint reports them only with a profile, and no
# Domain Profile declares them. A finding of the Domain Profile in force (built-in, extends, base/profile.md) gets
# its rule layer where it is raised (Report.scope), since BAD_ISO or BAD_ACTOR may be the spec's or a Domain Profile's.
OKF_PROFILE_CODES = frozenset({
    "NAME_KEBAB", "NO_OKF_VERSION", "PROFILE_OKF_VERSION", "PROFILE_NO_INDEX", "PROFILE_NO_LOG", "PROFILE_NO_PROJECT",
    "PROFILE_PROJECT_TYPE", "PROFILE_NO_GENERATED", "PROFILE_NO_TIMESTAMP", "PROFILE_OUTSIDE_LAYER",
    "PROFILE_MANY_PROJECTS", "PROFILE_MANY_CONFLICT_LOGS",
    "FRAGMENT_UNCITED", "SECTION_EMPTY", "VERIFIED_STALE"})  # the mechanical audit checks (check_audit)
SHIPPED_PROFILES = (PROFILE_20, PROFILE_30)


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.notices: list[str] = []  # neither warnings nor errors; they never fail --strict
        self.profile_outdated = False
        self.skipped: list[dict] = []  # what a foreign profile's okf-profile and domain-profile rules found
        self.ignored: list[str] = []  # paths .okfignore excludes
        self.concepts = 0
        self.scope: str | None = None  # the rule layer of the checks running, when the call site fixes it
        self.metrics: dict = {}  # the --json metrics (audit_metrics)

    def add(self, level: str, code: str, path: str, msg: str, source: str | None = None,
            layer: str | None = None, line: int | None = None) -> None:
        """source: the Domain Profile layer that declared the broken item; the PROFILE_* codes of a concept carry it.
        layer: the rule layer the finding comes from (spec, okf-profile or domain-profile); by default the scope
        the caller set, else okf-profile for OKF_PROFILE_CODES and spec for every other code.
        line: the line in the raw file (frontmatter included) the finding points at, when it points at one."""
        layer = layer or self.scope or (OKF_PROFILE if code in OKF_PROFILE_CODES else SPEC)
        self.items.append({"level": level, "code": code, "path": path, "message": msg, "layer": layer,
                           **({"source": source} if source is not None else {}),
                           **({"line": line} if line is not None else {})})

    def by_layer(self) -> dict:
        return {x: {"errors": sum(i["layer"] == x for i in self.errors),
                    "warnings": sum(i["layer"] == x for i in self.warns)} for x in RULE_LAYERS}

    def skip_profile_layers(self, name: str) -> None:
        """A foreign okf_profile: what the okf-profile and domain-profile rules found moves to skipped, as one notice."""
        self.skipped = [i for i in self.items if i["layer"] != SPEC]
        self.items = [i for i in self.items if i["layer"] == SPEC]
        codes = ", ".join(sorted({i["code"] for i in self.skipped}))
        self.notices.append(f"profile {name} is not one okf-builder ships ({', '.join(SHIPPED_PROFILES)}): spec "
                            f"checks only, {len(self.skipped)} okf-profile and domain-profile findings skipped"
                            + (f" ({codes})" if codes else ""))

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


def check_index(doc: Doc, bundle: Path, rep: Report, docs_by_path: dict, profile: bool = True,
                excluded: set | None = None) -> None:
    """excluded: the resolved paths scan_bundle leaves out (ignored, nested bundles, non-OKF directories); an index
    need not list them."""
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
        if p.name.startswith(".") or p.resolve() in (excluded or ()):
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
    and its directory (forces caches it per type and covering families). With prof, aliases are resolved
    first, so every check reads the type, field or value a local name stands for."""
    if not doc.has_fm_block:
        rep.error("NO_FRONTMATTER", doc.rel, "concept has no YAML frontmatter block (§11.1)")
        return
    if doc.fm_error:
        rep.error("BAD_YAML", doc.rel, f"YAML frontmatter cannot be parsed: {doc.fm_error}")
        return
    raw = doc.frontmatter or {}
    fm = resolve_aliases(prof, raw) if prof is not None else raw
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

    if prof is not None and t is not None and str(t).strip():
        key = (str(t), tuple(f["dir"] for f in families_at(prof, "/" + doc.rel)))
        force = forces.get(key) if forces is not None else None
        if force is None:
            force = concept_force(prof, str(t), "/" + doc.rel)
            if forces is not None:
                forces[key] = force
        rep.scope = DOMAIN
        try:
            check_profile_fields(doc, fm, str(t), prof, force, rep)
            if is_a(prof, str(t), "Open Question"):
                check_review_due(doc, fm, rep, now)
        finally:
            rep.scope = None

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
    """A value of one of the field types of §4.1 other than list (a list is checked item by item). A string is
    any scalar: YAML reads `3`, `no` or `2026-01-01` as a number, a boolean or a date, and what the author
    wrote is still text."""
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
    return isinstance(v, (str, int, float, date))


ITEM_LABELS = {"participants": "participant"}  # what one item of a list field is called in a message


def _breach(fid: str, ftype: str, v, values: list, item: bool) -> str:
    label = ITEM_LABELS.get(fid, fid) if item else fid
    if ftype == "actor":
        return f"{label} '{v}' does not follow the actor convention (§7)"
    if ftype == "enum":
        return f"{label} '{v}' is not {'|'.join(str(x) for x in values)} (§7)"
    if ftype == "date_or_datetime":
        return f"{label} '{v}' is neither YYYY-MM-DD nor ISO 8601 with an offset"
    return f"{label} '{v}' is not a {ftype} (§4.1)"


def _rule_applies(prof: Resolved, t: str, fm: dict, when: dict) -> bool:
    return all(is_a(prof, t, str(v)) if k == "type" else str(fm.get(k)) == str(v) for k, v in when.items())


def _checked(item: dict, own: bool) -> bool:
    """An item lint reports: in a bundle with a base/profile.md (own), every item in force; without one, the
    items with their own code and those a layer other than the built-in declares, so a bundle without a
    profile of its own gets no PROFILE_* finding for a concept."""
    return own or bool(item.get("code")) or item.get("source") != BUILTIN


def _generic_breach(fid: str, ftype: str, v, values: list, item: bool) -> str:
    label = f"an item of {fid}" if item else fid
    if ftype == "enum":
        return f"{label} '{v}' is not one of {'|'.join(str(x) for x in values)} (§4.1)"
    return f"{label} '{v}' is not a{'n' if ftype[0] in 'aeiou' else ''} {ftype} (§4.1)"


def check_profile_fields(doc: Doc, fm: dict, t: str, prof: Resolved, force: dict, rep: Report) -> None:
    """The Domain Profile in force for the concept's type and directory (§4.1, §7 rule 15).

    A requirement with its own code is reported under it with the message it always had; one without a code
    under the generic PROFILE_* code with the source that declared it, the built-in layer included. Order: each required field that is missing, a blank value included, in declaration order; then each
    field's value in declaration order, each field followed by the rules whose first required field it is,
    and the rules that require no declared field; then fixed and forbidden keys, the types the covering
    families allow, and, in a bundle with a base/profile.md, the keys no layer declares. A blank value of a
    scalar field reported as missing is not checked again. A list is checked item by item, a single value as
    a one-item list. A type no layer declares gets only fixed, forbidden, rules and the families' types. In a
    bundle without a base/profile.md the built-in profile's items without a code are not reported."""
    fields, required, own = force["fields"], force["required"], prof.has_own
    for fid, req in required.items():
        if not _blank(fm.get(fid)) or not _checked(req, own):
            continue
        owner = fields[fid]["declared_by"] if fid in fields else t
        if req.get("code"):
            rep.add(req["level"].upper(), req["code"], doc.rel, f"{owner} has no '{fid}' (§4)")
        else:
            rep.add(req["level"].upper(), "PROFILE_REQUIRED", doc.rel,
                    f"{owner} has no '{fid}', required by {req['source']} (§4.1)", req["source"])
    rules = [r for r in prof.rules if _checked(r, own) and _rule_applies(prof, t, fm, r["when"])]

    def check_rules(at: str | None) -> None:
        for r in rules:
            if next((f for f in r["require"] if f in fields), None) != at:
                continue
            cond = " and ".join(f"{k} is {v}" for k, v in r["when"].items() if k != "type")
            for f in r["require"]:
                if not _blank(fm.get(f)):
                    continue
                if r.get("code"):
                    rep.add(_lvl(r).upper(), r["code"], doc.rel, f"{cond} but '{f}' is missing (§4)")
                else:
                    when = f"{cond} but " if cond else ""
                    rep.add(_lvl(r).upper(), "PROFILE_RULE", doc.rel,
                            f"rule '{r['name']}': {when}'{f}' is missing (§4.1)", r["source"])

    for fid, d in fields.items():
        v = fm.get(fid)
        item = d.get("type") == "list"
        reported_missing = fid in required and _checked(required[fid], own) and _blank(v)
        if _checked(d, own) and v is not None and (item or not reported_missing):
            ftype = d.get("of") if item else d.get("type")
            values = [x["value"] for x in d.get("values") or []]
            for x in (as_list(v) if item else [v]):
                if value_ok(ftype, x, values):
                    continue
                if d.get("code"):
                    rep.add(_lvl(d).upper(), d["code"], doc.rel, _breach(fid, ftype, x, values, item))
                else:
                    rep.add(_lvl(d).upper(), "PROFILE_ENUM" if ftype == "enum" else "PROFILE_FIELD_TYPE", doc.rel,
                            _generic_breach(fid, ftype, x, values, item), d["source"])
        check_rules(fid)
    check_rules(None)

    for k, e in force["fixed"].items():
        if k in fm and _checked(e, own) and not (fm[k] == e.get("value") or str(fm[k]) == str(e.get("value"))):
            rep.add(_lvl(e).upper(), e.get("code") or "PROFILE_FIXED", doc.rel,
                    f"'{k}' is {fm[k]!r}, fixed to {e.get('value')!r} by {e['source']} (§4.1)", e["source"])
    for k, e in force["forbidden"].items():
        if k in fm and _checked(e, own):
            reason = f": {e['reason']}" if e.get("reason") else ""
            rep.add(_lvl(e).upper(), e.get("code") or "PROFILE_FORBIDDEN", doc.rel,
                    f"'{k}' is forbidden by {e['source']}{reason} (§4.1)", e["source"])
    for f in force["families"]:
        if f["types"] and not any(is_a(prof, t, x) for x in f["types"]):
            rep.add("ERROR", "PROFILE_TYPE_NOT_ALLOWED", doc.rel,
                    f"type '{t}' is not allowed in family {f['dir']}, which allows {', '.join(f['types'])} (§4.1)",
                    f["source"])
    if prof.has_own and t in prof.types:
        known = (SPEC_KEYS | set(fields) | set(required) | set(force["fixed"]) | set(force["forbidden"])
                 | alias_keys(prof))
        if is_a(prof, t, DOMAIN_PROFILE):
            known |= set(PROFILE_KEYS)
        for k in fm:
            if k not in known:
                rep.add("WARN", "PROFILE_UNKNOWN_KEY", doc.rel, f"key '{k}' is declared by no layer for {t} (§4.1)",
                        OWN_REL)


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


def outside_layers(not_okf: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """The non-OKF directories outside fragments/, base/ and projections/: knowledge/3.0 still applies rule 12 to
    them (ADR-0018 decision 3), one PROFILE_OUTSIDE_LAYER per directory."""
    return [(rel, n) for rel, n in not_okf if rel.split("/")[0] not in LAYER_DIRS]


def check_layers(docs: list[Doc], rep: Report, prof: Resolved | None = None,
                 not_okf: list[tuple[str, int]] = ()) -> None:
    """knowledge/3.0: concepts live in base/ or fragments/; the root holds project.md and the Conflict Log.
    not_okf: the non-OKF directories of the scan; each one outside the layers is one error for all its files."""
    for rel, n in outside_layers(list(not_okf)):
        rep.error("PROFILE_OUTSIDE_LAYER", rel,
                  f"profile {PROFILE_30}: {rel} is not a layer and holds {n} Markdown file{'s' if n != 1 else ''} "
                  "without OKF frontmatter; move them under base/ or list the directory in .okfignore")
    for d in docs:
        parts = d.rel.split("/")
        if len(parts) == 1:
            t = canonical_type(prof, (d.frontmatter or {}).get("type"))
            if d.is_reserved or (d.rel == "project.md" and t == "Project") or t == "Conflict Log":
                continue
            rep.error("PROFILE_OUTSIDE_LAYER", d.rel,
                      f"profile {PROFILE_30}: a concept at the root must live in base/ or fragments/")
        elif parts[0] not in LAYER_DIRS:
            rep.error("PROFILE_OUTSIDE_LAYER", d.rel,
                      f"profile {PROFILE_30}: {parts[0]}/ is not a layer; move it under base/")


# --------------------------------------------------------------------------
# The mechanical audit checks (okf-flz.2): FRAGMENT_UNCITED, SECTION_EMPTY, VERIFIED_STALE, SECRET_IN_BUNDLE
# --------------------------------------------------------------------------
# The body headings of each shipped template, by the type it writes (okf-standard/templates/); a test keeps them in
# step with the templates, so lint needs no template beside it (the M365 okf-lint skill carries none).
TEMPLATE_SECTIONS = {
    "Project": ("project.md", ("# Purpose", "# Scope", "# Team and ownership", "# Key links", "# Knowledge map")),
    "Architecture Decision": ("adr.md", ("# Context", "# Decision", "# Alternatives considered", "# Consequences",
                                         "# Related")),
    "API": ("api.md", ("# Contract", "# Main operations", "# Authentication and authorization", "# Examples",
                       "# Exposed by")),
    "Architecture View": ("architecture-view.md", ("# View", "# Elements", "# Principles and constraints",
                                                   "# Related decisions")),
    "Attested Computation": ("computation.md", ("# Computation",)),
    "Conflict Log": ("conflict-log.md", ("# How it is used", "# Conflicts")),
    "Domain Profile": ("domain-profile.md", ("# What this bundle holds", "# Types", "## Client Meeting", "# Families",
                                             "## /base/clients/", "# Questions")),
    "Knowledge Fragment": ("fragment.md", ("# Record", "# Distillation")),
    "Metric": ("metric.md", ("# Definition", "# Dimensions", "# Known pitfalls")),
    "Open Question": ("open-question.md", ("# Question", "# Why it matters", "# What is known", "# Answer")),
    "Playbook": ("playbook.md", ("# When to apply", "# Prerequisites", "# Steps", "# Expected result", "# Related")),
    "Policy": ("policy.md", ("# Scope", "# Rule", "# Exceptions and exception process", "# Verification / controls",
                             "# Related")),
    "Reference": ("reference.md", ("# Summary", "# Key points for this project")),
    "Runbook": ("runbook.md", ("# Trigger", "# Impact", "# Diagnosis", "# Resolution steps", "# Rollback",
                               "# Escalation", "# Post-incident")),
    "System": ("system.md", ("# Responsibility", "# Interfaces", "# Dependencies", "# Operation",
                             "# Relevant configuration")),
    "Table": ("table.md", ("# Schema", "# Joins", "# Partitioning and freshness", "# Examples")),
    "Term": ("term.md", ("# Definition", "# Synonyms and related terms", "# Where it appears")),
}

def template_type(prof: Resolved | None, t: str) -> str:
    """The type whose template a concept of type t is made from: t itself when a shipped template writes it, else the
    nearest type t extends that one does (a local type of the Domain Profile), else t."""
    if t in TEMPLATE_SECTIONS or prof is None:
        return t
    return next((a for a in ancestors(prof, t) if a in TEMPLATE_SECTIONS), t)


def body_offset(path: Path) -> int:
    """How many lines of the raw file come before its body (the frontmatter block and its two '---' lines)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        return next((i + 1 for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
    return 0


def check_section_empty(doc: Doc, t: str, rep: Report) -> None:
    """A body section whose heading is also one of its type's template (TEMPLATE_SECTIONS) and that holds no content
    (content_lines: only blank lines, headings and placeholder text), up to the next heading of its level or higher."""
    spec = TEMPLATE_SECTIONS.get(t)
    if spec is None:
        return
    tpl, heads = spec
    want = {h.lower() for h in heads}
    lines = doc.body.split("\n")
    offset = None
    for s in body_sections(lines):
        if s.heading.lower() in want and not content_lines(lines[s.line + 1:s.end]):
            offset = body_offset(doc.path) if offset is None else offset
            n = offset + s.line + 1
            rep.add("WARN", "SECTION_EMPTY", doc.rel, f"section '{s.heading}' (line {n}) of the {tpl} template is empty "
                    "or holds only placeholder text: fill it, or remove it until its content is known", line=n)


def check_verified_stale(doc: Doc, fm: dict, rep: Report) -> None:
    """generated.at later than the last (latest) verification by a human: actor. Machine and process verifications,
    and a v0.1 concept (timestamp, no generated), are not read."""
    gen = fm.get("generated")
    at = to_dt(gen.get("at")) if isinstance(gen, dict) else None
    humans = [to_dt(v.get("at")) for v in as_list(fm.get("verified"))
              if isinstance(v, dict) and str(v.get("by") or "").startswith("human:")]
    humans = [h for h in humans if h is not None]
    if at is None or not humans:
        return
    last = max(humans)
    if at > last:
        rep.add("WARN", "VERIFIED_STALE", doc.rel, f"edited after a person verified it: generated.at {at.isoformat()} "
                f"is later than the last human verification, {last.isoformat()}; ask for a new verification (okf-review)")


def _citing(d: Doc, layered: bool, prof: Resolved | None) -> bool:
    """A file whose citations count for FRAGMENT_UNCITED: in knowledge/3.0 each file under base/ (base/profile.md
    included) and the Conflict Log; in knowledge/2.0 each concept outside fragments/ but project.md. Never an index.md,
    a log.md or a fragment."""
    if d.is_reserved or d.rel.startswith(FRAGMENTS_DIR + "/"):
        return False
    if canonical_type(prof, (d.frontmatter or {}).get("type")) == "Conflict Log":
        return True
    return d.rel.startswith(BASE_DIR + "/") if layered else d.rel != "project.md"


def check_fragments_cited(docs: list[Doc], bundle: Path, prof: Resolved | None, rep: Report, layered: bool) -> None:
    """A distilled Knowledge Fragment (aliases resolved) that no concept cites: a body link, a sources entry or an
    Open Question's asked_in pointing at it, from a file _citing reads."""
    cited: set[Path] = set()
    for d in docs:
        if not _citing(d, layered, prof):
            continue
        fm = resolve_aliases(prof, d.frontmatter or {}) if prof is not None else (d.frontmatter or {})
        targets = list(extract_links(d.body))
        targets += [str(s["resource"]) if isinstance(s, dict) else str(s) for s in as_list(fm.get("sources"))
                    if (isinstance(s, dict) and s.get("resource")) or isinstance(s, str)]
        if prof is not None and is_a(prof, str(fm.get("type")), "Open Question") and fm.get("asked_in"):
            targets += [str(x) for x in as_list(fm.get("asked_in"))]
        for x in targets:
            p = resolve_link(bundle, d, x)
            if p is not None:
                cited.add(p)
    for d in docs:
        if not d.rel.startswith(FRAGMENTS_DIR + "/") or d.is_reserved or not d.frontmatter:
            continue
        fm = resolve_aliases(prof, d.frontmatter) if prof is not None else d.frontmatter
        t = str(fm.get("type"))
        is_fragment = is_a(prof, t, "Knowledge Fragment") if prof is not None else t == "Knowledge Fragment"
        if is_fragment and str(fm.get("distillation_status")) == "distilled" and d.path.resolve() not in cited:
            rep.add("WARN", "FRAGMENT_UNCITED", d.rel, "distilled, but no concept cites it: no file under base/ nor the "
                    "Conflict Log links to it, lists it in sources or names it in asked_in; cite it where its "
                    "knowledge went")


def check_audit(docs: list[Doc], bundle: Path, prof: Resolved | None, rep: Report, layered: bool) -> None:
    """The okf-profile audit checks: SECTION_EMPTY and VERIFIED_STALE per file, FRAGMENT_UNCITED across the bundle."""
    for d in docs:
        if d.is_reserved or not d.frontmatter:
            continue
        fm = resolve_aliases(prof, d.frontmatter) if prof is not None else d.frontmatter
        check_section_empty(d, template_type(prof, str(fm.get("type"))), rep)
        check_verified_stale(d, fm, rep)
    check_fragments_cited(docs, bundle, prof, rep, layered)


# SECRET_IN_BUNDLE: lint's own detector of a credential committed in a bundle file. It shares nothing with
# _SECRET_RES/mask_secrets, which mask a validator's output; gitleaks is the thorough scanner (make secrets).
_LEAK_PATTERNS = (
    ("a JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("a GitHub token", re.compile(r"\b(?:ghp|gho|ghs)_[A-Za-z0-9]{36}\b")),
    ("a GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("a GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("an AWS access key id", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    ("an API key (sk-)", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("a Bearer token", re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{12,})")),
    ("an Authorization header value", re.compile(r"(?i)\bauthorization\s*:\s*(?:(?:basic|token)\s+)?([A-Za-z0-9._~+/=-]{12,})")),
)
_LEAK_KEY = re.compile(r"(?i)(?<![\w.-])([\w.-]*(?:token|key|password|passwd|secret)[\w.-]*)[\"']?\s*[:=]\s*(\S.*)")
_SLUG = re.compile(r"(?:[A-Za-z]+|[0-9]+)(?:[-_.,:](?:[A-Za-z]+|[0-9]+))*")  # words and numbers: a name, not a secret
_HASH = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")  # a git commit or a SHA-256 digest


def _mixed(v: str) -> bool:
    return bool(re.search(r"[A-Za-z]", v)) and bool(re.search(r"[0-9]", v))


def _key_value(rest: str) -> str:
    """The value after 'key:' or 'key=': a quoted string without its quotes, else the run up to a space, ',' or ';'."""
    if rest[:1] in "\"'":
        end = rest.find(rest[0], 1)
        return rest[1:end] if end > 0 else rest[1:]
    return re.match(r"[^\s,;]*", rest).group(0)


def leak_kind(line: str) -> str | None:
    """What credential the line holds, or None. A value after a key naming a token, key, password or secret counts
    only when it is 16+ characters, has no space, mixes letters and digits, and is none of: a path (holds '/'), a
    backtick span, a brace or bracket value, a {{...}} placeholder, a $VARIABLE, words and numbers joined by - _ . , :
    (a slug, an ADR file name) or a 40/64-hex hash."""
    for kind, rx in _LEAK_PATTERNS:
        for m in rx.finditer(line):
            v = m.group(m.lastindex or 0)
            if _mixed(v) or kind in ("a JSON Web Token", "an AWS access key id", "a Google API key", "a GitHub token"):
                return kind
    for m in _LEAK_KEY.finditer(line):
        rest = m.group(2)
        if rest[:1] in "`{[$" or "{{" in rest:
            continue
        v = _key_value(rest)
        if (len(v) >= 16 and " " not in v and _mixed(v) and "/" not in v and not v.startswith(("`", "{", "[", "$"))
                and "{{" not in v and not _SLUG.fullmatch(v) and not _HASH.fullmatch(v)):
            key = m.group(1)
            return f"a value of '{key}'" if len(key) <= 32 else "a value of a key naming a token, key, password or secret"
    return None


def check_secrets(docs: list[Doc], rep: Report) -> None:
    """SECRET_IN_BUNDLE (error, spec): one per line of a bundle file, frontmatter included, that holds a credential
    (leak_kind). The message names the line and what was found, never the value."""
    for d in docs:
        for n, line in enumerate(d.path.read_text(encoding="utf-8").splitlines(), 1):
            kind = leak_kind(line)
            if kind:
                rep.add("ERROR", "SECRET_IN_BUNDLE", d.rel, f"line {n}: {kind} is committed in the bundle (value not "
                        "shown); remove it, rotate it, and scan the history with gitleaks", layer=SPEC, line=n)


def _is_concept(d: Doc, layered: bool) -> bool:
    """A concept for the metrics: a file under base/ (in knowledge/2.0 and spec only, outside fragments/), not a
    reserved file, an index.md nor base/profile.md."""
    if d.is_reserved or d.rel in RESERVED_PATHS or d.rel.startswith(FRAGMENTS_DIR + "/"):
        return False
    return d.rel.startswith(BASE_DIR + "/") if layered else True


def audit_metrics(docs: list[Doc], rep: Report, prof: Resolved | None, now: datetime, layered: bool) -> dict:
    """The --json metrics: findings per code, concepts per trust level, fragments per distillation_status with the
    age in days of the oldest pending one (occurred_at, else generated.at), and stale_after_cluster when at least 4
    concepts have stale_after and more than a quarter of them fall in one ISO week (every such week)."""
    trust = {"unverified": 0, "machine-confirmed": 0, "human-reviewed": 0}
    weeks: Counter = Counter()
    by_status: Counter = Counter()
    ages = []
    for d in docs:
        if not d.frontmatter:
            continue
        fm = resolve_aliases(prof, d.frontmatter) if prof is not None else d.frontmatter
        if _is_concept(d, layered):
            by = [str(v.get("by") or "") for v in as_list(fm.get("verified")) if isinstance(v, dict) and v.get("by")]
            trust["human-reviewed" if any(b.startswith("human:") for b in by)
                  else "machine-confirmed" if by else "unverified"] += 1
            sa = to_dt(fm.get("stale_after"))
            if sa is not None:
                y, w, _ = sa.isocalendar()
                weeks[f"{y}-W{w:02d}"] += 1
        elif d.rel.startswith(FRAGMENTS_DIR + "/") and not d.is_reserved:
            st = fm.get("distillation_status")
            by_status[str(st) if st is not None else "missing"] += 1
            if str(st) == "pending":
                gen = fm.get("generated")
                when = utc_date(fm.get("occurred_at")) if fm.get("occurred_at") is not None else None
                when = when or (utc_date(gen.get("at")) if isinstance(gen, dict) and gen.get("at") is not None else None)
                if when is not None:
                    ages.append((now.date() - when).days)
    out = {"count_per_code": dict(sorted(Counter(i["code"] for i in rep.items).items())),
           "concepts_by_trust": trust,
           "fragments": {"by_status": dict(sorted(by_status.items())), "oldest_pending_days": max(ages) if ages else None}}
    n = sum(weeks.values())
    cluster = [{"week": w, "count": c} for w, c in sorted(weeks.items()) if n >= 4 and c * 4 > n]
    if cluster:
        out["stale_after_cluster"] = cluster
    return out


def foreign_profile_notice(name: str, unread: list[str]) -> str:
    """--profiles under a foreign okf_profile: lint runs spec checks only, so no Domain Profile file is read or checked."""
    files = f"{', '.join(unread)} not read: " if unread else ""
    return (f"{files}profile {name} is not one okf-builder ships ({', '.join(SHIPPED_PROFILES)}): lint runs spec "
            "checks only, so the Domain Profile's checks (structural ones included) do not run")


def profile_structure(bundle: Path, docs: list[Doc]) -> tuple[Resolved, list[dict], list[str]]:
    """The Domain Profile in force, its structural findings (§7 rule 14) and its notices; lint and --profiles share it."""
    declared = declared_profile(bundle)
    if declared == PROFILE_30:
        prof = load_profile(bundle, read_own=True)
        return prof, prof.findings + misplaced(docs, prof), []
    if declared not in (None, PROFILE_20):  # a foreign profile: lint skips what it finds beyond the spec
        return load_profile(bundle, read_own=False), [], [foreign_profile_notice(declared, ignored_in_20(docs))]
    return load_profile(bundle, read_own=False), [], [IGNORED_20_NOTICE.format(rel=rel) for rel in ignored_in_20(docs)]


VALIDATOR_TIMEOUT = 300  # seconds
VALIDATOR_OUTPUT_MAX = 2000  # characters of a failing validator's output kept in its finding
_SECRET_RES = (
    # a key naming a token, key, password or secret, quoted or not, then = or :, then its value, quoted or not
    (re.compile(r"""(?i)(["']?[\w.-]*(?:token|key|password|secret)[\w.-]*["']?\s*[:=]\s*)"""
                r"""(?!\[masked\])("[^"\n]*"|'[^'\n]*'|[^\s,;}\]]+)"""), r"\1[masked]"),
    (re.compile(r"(?i)(authorization:\s*)\S+(?:\s+(?!\[masked\])\S+)?"), r"\1[masked]"),
    (re.compile(r"(?i)\b(bearer\s+)(?!\[masked\])\S+"), r"\1[masked]"),
    # a JWT: three base64url parts joined by '.', the first one a JSON object ("eyJ")
    (re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]*"), "[masked]"),
)
# a run of 32 or more base64, base64url or hex characters, '/' included
_CANDIDATE = re.compile(r"[A-Za-z0-9+/_-]{32,}={0,2}")
# the same without '/': the pieces of a path that are masked on their own
_LONG_RUN = re.compile(r"[A-Za-z0-9+_-]{32,}={0,2}")
# lowercase words or numbers joined by - or _ (a kebab-case slug, a dated file name, a snake_case test name)
_WORDS = re.compile(r"(?:[a-z]+|[0-9]+)(?:[_-](?:[a-z]+|[0-9]+))+")
# a path segment shaped like a name: a word, CamelCase words, an acronym, lowercase letters and digits, a number,
# any of them joined by - or _
_NAME = re.compile(r"(?:[A-Z]?[a-z]+(?:[A-Z][a-z]+)*[0-9]*|[a-z0-9]+|[A-Z]{2,6}[a-z]*|[0-9]+)"
                   r"(?:[-_](?:[A-Za-z]?[a-z]+|[A-Za-z0-9]+))*")
SECRET_ENTROPY = 4.0  # bits per character; see _slashed_secret
SECRET_UNNAMED = 0.5  # share of the characters in segments not shaped like a name; see _slashed_secret


def _entropy(s: str) -> float:
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def _slashed_secret(run: str, before: str) -> bool:
    """A run with '/' is a standard-base64 secret, not a path, when it does not follow '~' or '.' (~/, ./, ../),
    at least half of its characters lie in segments not shaped like a name (_NAME), and it carries at least 4.0
    bits of entropy per character.

    The thresholds come from data. Random base64 strings of 40-88 characters that hold a '/' measured at least
    4.4 bits per character; about 2 in 60,000 had under 50% of their characters in unnamed segments and are
    read as paths (their pieces of 32 or more characters are still masked). The path runs of the
    test table (absolute macOS and Linux paths, Java, Kotlin, Android and TypeScript paths, URL path parts, of
    33-88 characters, mixed case and digits) measured 3.82-4.34 bits, with 0-12% in unnamed segments; the
    relative paths of okf-builder, a dated fragment and a Docker overlay directory stay at or under 32%. The
    name-shape share separates them by itself; entropy is a second condition, so a run of few distinct
    characters is never masked whole. A leading '/' is not taken as a path: a base64 secret starts with one once
    in 64, and an absolute path's segments are names, so the share keeps it."""
    segs = [s for s in run.rstrip("=").split("/") if s]
    if before in ("~", "."):
        return False
    unnamed = sum(len(s) for s in segs if not _NAME.fullmatch(s)) / max(1, sum(len(s) for s in segs))
    return unnamed >= SECRET_UNNAMED and _entropy(run) >= SECRET_ENTROPY


def _mask_run(m: re.Match) -> str:
    run = m.group(0)
    if "/" in run and _slashed_secret(run, m.string[m.start() - 1:m.start()]):
        return "[masked]"
    return _LONG_RUN.sub(lambda p: p.group(0) if _WORDS.fullmatch(p.group(0)) else "[masked]", run)


def mask_secrets(text: str) -> str:
    """The value after a key that names a token, key, password or secret (token=, "token": "...",
    password: "a b"), after Authorization: and after Bearer, a JWT, and every run of 32 or more base64,
    base64url or hex characters, become [masked]. A run of lowercase words or numbers joined by - or _ (a slug,
    a test name) is not a secret. A run with '/' is masked whole when it reads as a standard-base64 secret
    (_slashed_secret); otherwise it is a path, kept but for its pieces of 32 or more characters without '/'."""
    for rx, sub in _SECRET_RES:
        text = rx.sub(sub, text)
    return _CANDIDATE.sub(_mask_run, text)


def _validator_paths(v: dict, docs: list[Doc], prof: Resolved) -> list[str]:
    """The concepts a validator covers, as paths from the bundle root: those whose type (an alias resolved) is
    or extends one of its types, or that a family it names covers; every concept when it names neither."""
    out = []
    for d in docs:
        if d.is_reserved or not d.frontmatter:
            continue
        t = str(canonical_type(prof, d.frontmatter.get("type")))
        by_type = any(is_a(prof, t, x) for x in v.get("types") or [])
        by_family = any(("/" + d.rel).startswith(f if f.endswith("/") else f + "/") for f in v.get("families") or [])
        if by_type or by_family or not (v.get("types") or v.get("families")):
            out.append(d.rel)
    return out


def run_validators(bundle: Path, docs: list[Doc], prof: Resolved, rep: Report, run: bool) -> None:
    """Each validator of the Domain Profile (§4.1): a notice unless run is set; with it, its command (split like
    a shell would, never run through one) from the bundle root with the matching paths as arguments, and a
    failure as PROFILE_VALIDATOR with its output masked and truncated. One that matches no concept is not run."""
    for v in prof.validators:
        if not run:
            rep.notices.append(f"validator {v['name']} not run (use --run-validators)")
            continue
        paths = _validator_paths(v, docs, prof)
        if not paths:
            continue
        try:
            p = subprocess.run([*shlex.split(v["command"]), *paths], cwd=bundle, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=VALIDATOR_TIMEOUT)
            if p.returncode == 0:
                continue
            why, out = f"exit {p.returncode}", (p.stdout + p.stderr).strip()
        except subprocess.TimeoutExpired:
            why, out = f"timed out after {VALIDATOR_TIMEOUT}s", ""
        except (OSError, ValueError) as e:
            why, out = "could not start", str(e)
        out = mask_secrets(out)
        if len(out) > VALIDATOR_OUTPUT_MAX:
            out = out[:VALIDATOR_OUTPUT_MAX] + " [truncated]"
        rep.add("ERROR", "PROFILE_VALIDATOR", v["source"],
                f"validator {v['name']} failed ({why})" + (f": {out}" if out else ""), v["source"], DOMAIN)


def scan_notices(scan, reported: list[tuple[str, int]] = ()) -> list[str]:
    """One notice for what .okfignore excludes, one per reserved path it cannot exclude, one per nested bundle and
    one per non-OKF directory but those in reported (lint gives them an error instead); lint and --profiles both
    print them, so a check on a file the scan left out is never skipped in silence."""
    out = []
    if scan.ignored:
        n = len(scan.ignored)
        out.append(f".okfignore excludes {n} path{'s' if n != 1 else ''}, not read: {', '.join(scan.ignored)}")
    for rel in scan.reserved:
        out.append(f"cannot ignore {rel}: reserved" + (f", it holds {OWN_REL}" if rel.endswith("/") else ""))
    for rel in scan.nested:
        out.append(f"nested bundle {rel} skipped: its index.md declares its own okf_version; lint it on its own")
    for rel, n in scan.not_okf:
        if (rel, n) in reported:
            continue
        out.append(f"{rel} is not OKF: {n} Markdown file{'s' if n != 1 else ''} without OKF frontmatter and no "
                   "index.md, skipped")
    return out


def lint(bundle: Path, profile: bool = True, version: str = "auto",
         validators: bool = False) -> tuple[Report, str, str]:
    """validators: run the Domain Profile's validator commands (--run-validators); otherwise each one is a notice."""
    rep = Report()
    now = datetime.now(timezone.utc)
    scan = scan_bundle(bundle)
    docs = scan.docs
    excluded = scan.excluded(bundle)
    rep.ignored, rep.concepts = scan.ignored, len([d for d in docs if not d.is_reserved])
    by_path = {d.path.resolve(): d for d in docs}
    declared = declared_profile(bundle)
    foreign = declared not in (None, *SHIPPED_PROFILES)
    layered = profile and declared == PROFILE_30
    rep.notices += scan_notices(scan, outside_layers(scan.not_okf) if layered else [])
    pname = declared or PROFILE_20
    prof = None  # --no-profile: no Domain Profile, the built-in one included
    if profile:
        rep.profile_outdated = pname == PROFILE_20
        prof, findings, notices = profile_structure(bundle, docs)
        if layered:
            check_layers(docs, rep, prof, scan.not_okf)
        for i in findings:
            rep.add(i["level"], i["code"], i["path"], i["message"], layer=DOMAIN)
        if not foreign:  # skip_profile_layers gives a foreign profile its one notice
            rep.notices += notices

    detected, origin = detect_version(bundle, docs)
    forced = version != "auto"
    if not forced:
        version = detected
    unsupported = declared_version(bundle) if origin != "declared" else None
    if origin == "mixed":
        why = "okf_version is missing" if unsupported is None else f"okf_version '{unsupported}' is not supported"
        rep.warn("MIXED_VERSIONS", "index.md", f"concepts mix 0.1 and 0.2 forms and {why}: bundle half migrated (okf-migrate)")
    if origin == "declared" and detected != version:
        rep.warn("VERSION_MISMATCH", "index.md", f"index.md declares okf_version {detected} but is validated as {version}")
    if unsupported is not None:
        how = f"forced version: {version} (--okf-version)" if forced else f"inferred version: {version} ({origin})"
        rep.warn("UNSUPPORTED_OKF_VERSION", "index.md", f"root index.md declares okf_version '{unsupported}', which is "
                 f"not {' or '.join(SUPPORTED_VERSIONS)}; {how}")
    elif origin != "declared" and profile:
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
            if d and d.frontmatter and canonical_type(prof, d.frontmatter.get("type")) != "Project":
                rep.error("PROFILE_PROJECT_TYPE", "project.md", "project.md must have type: Project")
        typed = [(d, canonical_type(prof, d.frontmatter.get("type"))) for d in docs if d.frontmatter and not d.is_reserved]
        types = [t for _, t in typed]
        if types.count("Project") > 1:
            rep.error("PROFILE_MANY_PROJECTS", "project.md", "more than one concept has type: Project")
        if types.count("Conflict Log") > 1:
            logs = ", ".join(d.rel for d, t in typed if t == "Conflict Log")
            rep.error("PROFILE_MANY_CONFLICT_LOGS", "conflict-log.md", f"more than one concept has type: Conflict Log ({logs})")

    forces: dict = {}
    for d in docs:
        if d.path.name == "index.md":
            check_index(d, bundle, rep, by_path, profile, excluded)
        elif d.path.name == "log.md":
            if d.has_fm_block and d.frontmatter and d.frontmatter.get("type") not in (None, "Log"):
                rep.warn("LOG_TYPE", d.rel, "log.md with frontmatter should be type: Log, or have no frontmatter")
            check_log(d, rep)
        else:
            check_concept(d, bundle, rep, profile, now, version, pname, prof, forces)
    if profile:
        check_audit(docs, bundle, prof, rep, layered)
    check_secrets(docs, rep)
    if prof is not None:
        run_validators(bundle, docs, prof, rep, validators)
    if profile and foreign:
        rep.skip_profile_layers(declared)
    rep.metrics = audit_metrics(docs, rep, prof, now, declared == PROFILE_30)
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
    ap.add_argument("--run-validators", action="store_true",
                    help="run the commands the Domain Profile's validator entries declare (never run without it)")
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
        scan = scan_bundle(bundle)
        prof, findings, notices = profile_structure(bundle, scan.docs)
        info = {**in_force(prof, bundle_path(bundle, args.profiles)), "findings": findings,
                "notices": scan_notices(scan) + notices}
        print(json.dumps(info, ensure_ascii=False, indent=2, default=str) if args.json else format_in_force(info))
        return 1 if findings else 0

    rep, version, origin = lint(bundle, profile=not args.no_profile, version=args.okf_version,
                                validators=args.run_validators)
    n_docs = rep.concepts
    by_layer = rep.by_layer()
    if args.json:
        print(json.dumps({"bundle": str(bundle), "okf_version": version, "version_origin": origin, "concepts": n_docs, "errors": len(rep.errors),
                          "warnings": len(rep.warns), "by_layer": by_layer, "profile_outdated": rep.profile_outdated,
                          "notices": rep.notices, "findings": rep.items, "skipped": rep.skipped, "ignored": rep.ignored,
                          "metrics": rep.metrics},
                         ensure_ascii=False, indent=2))
    else:
        for i in rep.items:
            print(f"{i['level']:5} {i['code']:22} {i['path']}: {i['message']}")
        for n in rep.notices:
            print(f"NOTICE {n}")
        if rep.profile_outdated:
            print(f"NOTICE {OUTDATED_NOTICE}")
        verdict = "CONFORMANT" if not rep.errors else "NOT CONFORMANT"
        layers = " · ".join(f"{x} {c['errors']}/{c['warnings']}" for x, c in by_layer.items())
        print(f"\n{bundle}: OKF {version} ({origin}) · {n_docs} concepts · {len(rep.errors)} errors · "
              f"{len(rep.warns)} warnings ({layers}) → {verdict}")
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
    # distilled, and no concept of this bundle cites it: FRAGMENT_UNCITED as well
    assert [(i["level"], i["code"], i["path"]) for i in rep.items] == [("WARN", "FRAGMENT_NO_FIELD", _FRAGMENT),
                                                                     ("WARN", "FRAGMENT_UNCITED", _FRAGMENT)]
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
        # a string is any scalar YAML may have read as a number, a boolean or a date
        "string": (["x", 3, 2.5, False, _date(2026, 1, 1)], [None, ["x"], {"a": 1}]), "integer": ([3], [True, "3"]), "boolean": ([False], ["no"]),
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


def test_profiles_lists_the_questions_in_force_with_their_source_in_text_and_json(tmp_path, capsys):
    import json as _json

    k = _bundle_30(tmp_path)
    (k / "base" / "profile.md").write_text(_domain_profile(
        "questions:\n  - { question: \"Who owns each runbook?\", field: Runbook.owner }\n"
        "  - { question: \"How is it deployed?\", concept: /base/architecture/deployment.md }\n"), encoding="utf-8")
    capsys.readouterr()
    assert main([str(k), "--profiles", "/fragments/"]) == 0
    out = capsys.readouterr().out
    assert "question Who owns each runbook? → field Runbook.owner  [base/profile.md]" in out
    assert "question How is it deployed? → concept /base/architecture/deployment.md  [base/profile.md]" in out
    assert main([str(k), "--profiles", "--json"]) == 0
    assert _json.loads(capsys.readouterr().out)["questions"] == [
        {"question": "Who owns each runbook?", "field": "Runbook.owner", "source": "base/profile.md"},
        {"question": "How is it deployed?", "concept": "/base/architecture/deployment.md", "source": "base/profile.md"}]


def test_a_blank_field_required_through_by_type_is_reported_once_as_missing(tmp_path):
    k = _question_bundle(tmp_path, _QUESTION_FIELDS + 'review_on: ""\n')
    (k / "base" / "profile.md").write_text(_domain_profile(
        "by_type:\n  Open Question: { required: { review_on: { level: warn, code: MY_REVIEW } } }\n"), encoding="utf-8")
    (k / "base" / "index.md").write_text("# base\n\n* [Profile](profile.md) - The taxonomy.\n\n# Subdirectories\n\n"
                                         "* [questions](questions/index.md) - Questions.\n", encoding="utf-8")
    rep, _, _ = lint(k)
    assert [(i["level"], i["code"], i["path"], i["message"]) for i in rep.items] == [
        ("WARN", "MY_REVIEW", _QUESTION, "Open Question has no 'review_on' (§4)")]


# Every per-field breach of a fragment and of two questions. The expected findings are the --json output, in
# order, of okf_lint.py as it was before the built-in profile (origin/main at 659f872) on the same bundles.
_EVERY_FRAGMENT_BREACH = ("occurred_at: last tuesday\nparticipants: [human:alice, Bob, okf-builder/x, Carol]\n"
                          "distillation_status: done\n")
_EVERY_QUESTION_BREACH = "owner: Alice\nquestion_status: answered\nreview_on: next week\n"
_BAD_STATUS_QUESTION = "owner: human:alice\nquestion_status: closed\nasked_in: /fragments/2026-10-31-meeting.md\n"
_EVERY_BREACH_FINDINGS = [
    ('WARN', 'QUESTION_NO_FIELD', 'base/questions/who-approves-refunds.md', "Open Question has no 'asked_in' (§4)"),
    ('WARN', 'BAD_ACTOR', 'base/questions/who-approves-refunds.md',
     "owner 'Alice' does not follow the actor convention (§7)"),
    ('WARN', 'QUESTION_NO_ANSWER', 'base/questions/who-approves-refunds.md',
     "question_status is answered but 'answered_by' is missing (§4)"),
    ('WARN', 'BAD_ISO', 'base/questions/who-approves-refunds.md',
     "review_on 'next week' is neither YYYY-MM-DD nor ISO 8601 with an offset"),
    ('WARN', 'FRAGMENT_NO_FIELD', 'fragments/2026-10-31-meeting.md', "Knowledge Fragment has no 'origin' (§4)"),
    ('WARN', 'BAD_ISO', 'fragments/2026-10-31-meeting.md',
     "occurred_at 'last tuesday' is neither YYYY-MM-DD nor ISO 8601 with an offset"),
    ('WARN', 'BAD_ACTOR', 'fragments/2026-10-31-meeting.md',
     "participant 'Bob' does not follow the actor convention (§7)"),
    ('WARN', 'BAD_ACTOR', 'fragments/2026-10-31-meeting.md',
     "participant 'Carol' does not follow the actor convention (§7)"),
    ('ERROR', 'BAD_DISTILLATION_STATUS', 'fragments/2026-10-31-meeting.md',
     "distillation_status 'done' is not pending|distilled|conflict (§7)"),
]
_BAD_STATUS_FINDINGS = [
    ('ERROR', 'BAD_QUESTION_STATUS', 'base/questions/who-approves-refunds.md',
     "question_status 'closed' is not open|answered|dropped (§7)"),
]


def _every_breach_bundles(tmp_path) -> tuple[Path, Path]:
    k = _question_bundle(tmp_path / "a", _EVERY_QUESTION_BREACH)
    frag = k / _FRAGMENT
    frag.write_text(frag.read_text(encoding="utf-8").replace(_FRAGMENT_FIELDS, _EVERY_FRAGMENT_BREACH),
                    encoding="utf-8")
    return k, _question_bundle(tmp_path / "b", _BAD_STATUS_QUESTION)


def test_every_per_field_breach_keeps_its_level_code_message_and_order(tmp_path, capsys):
    import json as _json

    for k, want in zip(_every_breach_bundles(tmp_path), (_EVERY_BREACH_FINDINGS, _BAD_STATUS_FINDINGS)):
        capsys.readouterr()
        assert main([str(k), "--json"]) == 1
        got = [(i["level"], i["code"], i["path"], i["message"])
               for i in _json.loads(capsys.readouterr().out)["findings"]]
        assert got == want


# --------------------------------------------------------------------------
# Concepts against the Domain Profile (ticket D4): one test per row
# --------------------------------------------------------------------------
_CONCEPT_CODES = ("PROFILE_REQUIRED", "PROFILE_ENUM", "PROFILE_FORBIDDEN", "PROFILE_FIXED", "PROFILE_RULE",
                  "PROFILE_TYPE_NOT_ALLOWED", "PROFILE_FIELD_TYPE", "PROFILE_UNKNOWN_KEY", "PROFILE_VALIDATOR")
_MEETING = ("types:\n  Client Meeting:\n    extends: Knowledge Fragment\n    fields:\n"
            "      client: { type: string, required: true }\n"
            "      kind: { type: enum, values: [call, visit] }\n"
            "      attendees: { type: integer, level: warn }\n"
            "      billable: { type: boolean }\n"
            "      signed_on: { type: date }\n"
            "      contacts: { type: list, of: actor }\n"
            "      contract: { type: path }\n")
_MEETING_FIELDS = _FRAGMENT_FIELDS + "client: Acme\n"


def _concept(t: str, fields: str = "") -> str:
    return f"---\ntype: {t}\ntitle: C\ndescription: C.\nstatus: draft\n" + fields + _GEN + "---\n\nText.\n"


def _list_in_indexes(k: Path, rel: str) -> None:
    """List a concept in its directory's index.md, and each new directory in its parent's."""
    parts = rel.split("/")
    for i, name in enumerate(parts):
        idx = k.joinpath(*parts[:i], "index.md")
        text = idx.read_text(encoding="utf-8") if idx.exists() else f"# {parts[i - 1]}\n\n"
        target = name if i == len(parts) - 1 else f"{name}/index.md"
        if f"]({target})" not in text:
            idx.write_text(text.rstrip("\n") + f"\n* [{name}]({target}) - X.\n", encoding="utf-8")


def _profiled(tmp_path, keys: str, fragment: str | None = None, extra: dict | None = None) -> Path:
    """A clean 3.0 bundle with base/profile.md; fragment replaces the fragment's frontmatter fields and type line."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    k = _with_own_profile(_bundle_30(tmp_path), keys)
    if fragment is not None:
        (k / _FRAGMENT).write_text(fragment, encoding="utf-8")
    for rel, text in (extra or {}).items():
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
        _list_in_indexes(k, rel)
    return k


def _profile_items(rep: Report) -> list[tuple]:
    return [(i["level"], i["code"], i["path"], i["message"]) for i in rep.items if i["code"] in _CONCEPT_CODES]


def _meeting(fields: str) -> str:
    return _concept("Client Meeting", fields)


def test_a_concept_of_a_local_type_missing_a_required_field_is_profile_required(tmp_path):
    rep, _, _ = lint(_profiled(tmp_path, _MEETING, _meeting(_FRAGMENT_FIELDS)))
    assert _profile_items(rep) == [("ERROR", "PROFILE_REQUIRED", _FRAGMENT,
                                    "Client Meeting has no 'client', required by base/profile.md (§4.1)")]
    assert [i["code"] for i in rep.items] == ["PROFILE_REQUIRED"]
    warn = _MEETING.replace("client: { type: string, required: true }", "client: { type: string, required: { level: warn } }")
    rep, _, _ = lint(_profiled(tmp_path / "w", warn, _meeting(_FRAGMENT_FIELDS + 'client: ""\n')))
    assert [(i["level"], i["code"]) for i in rep.items] == [("WARN", "PROFILE_REQUIRED")]  # blank is missing, once


def test_a_value_outside_a_declared_enum_is_profile_enum(tmp_path):
    rep, _, _ = lint(_profiled(tmp_path, _MEETING, _meeting(_MEETING_FIELDS + "kind: lunch\n")))
    assert _profile_items(rep) == [("ERROR", "PROFILE_ENUM", _FRAGMENT, "kind 'lunch' is not one of call|visit (§4.1)")]
    assert lint(_profiled(tmp_path / "ok", _MEETING, _meeting(_MEETING_FIELDS + "kind: visit\n")))[0].items == []


def test_a_forbidden_key_global_per_family_or_per_type_names_its_reason(tmp_path):
    cases = {
        "global": "forbidden:\n  internal_notes: { reason: Internal notes stay out }\n",
        "family": "families:\n  /base/questions/: { forbidden: { internal_notes: { reason: Internal notes stay out } } }\n",
        "type": "by_type:\n  Open Question: { forbidden: { internal_notes: { reason: Internal notes stay out, level: warn } } }\n",
    }
    for case, keys in cases.items():
        k = _question_bundle(tmp_path / case, _QUESTION_FIELDS + "internal_notes: ask Bob\n")
        _with_own_profile(k, keys)
        (k / "base" / "index.md").write_text("# base\n\n* [Profile](profile.md) - P.\n\n# Subdirectories\n\n"
                                             "* [questions](questions/index.md) - Q.\n", encoding="utf-8")
        level = "WARN" if case == "type" else "ERROR"
        assert _profile_items(lint(k)[0]) == [(level, "PROFILE_FORBIDDEN", _QUESTION,
                                               "'internal_notes' is forbidden by base/profile.md: Internal notes stay out (§4.1)")], case
    # a family's forbidden key applies only under its directory
    k = _profiled(tmp_path / "elsewhere", cases["family"], _concept("Knowledge Fragment", _FRAGMENT_FIELDS + "internal_notes: x\n"))
    assert [i for i in lint(k)[0].items if i["code"] == "PROFILE_FORBIDDEN"] == []


def test_a_fixed_key_with_another_value_is_profile_fixed(tmp_path):
    keys = "fixed:\n  okf_lang: { value: en, level: warn }\n"
    k = _profiled(tmp_path, keys, _concept("Knowledge Fragment", _FRAGMENT_FIELDS + "okf_lang: es\n"))
    assert _profile_items(lint(k)[0]) == [("WARN", "PROFILE_FIXED", _FRAGMENT,
                                           "'okf_lang' is 'es', fixed to 'en' by base/profile.md (§4.1)")]
    # where the key is absent, or holds the value, nothing is reported
    assert lint(_profiled(tmp_path / "ok", keys, _concept("Knowledge Fragment", _FRAGMENT_FIELDS + "okf_lang: en\n")))[0].items == []


def test_a_rule_whose_when_holds_and_a_required_field_is_missing_names_the_rule(tmp_path):
    keys = _MEETING + ("rules:\n  - { name: distilled-names-contract, when: { type: Client Meeting, "
                       "distillation_status: distilled }, require: [contract] }\n")
    fields = _MEETING_FIELDS.replace("distillation_status: pending", "distillation_status: distilled")
    assert _profile_items(lint(_profiled(tmp_path, keys, _meeting(fields)))[0]) == [
        ("ERROR", "PROFILE_RULE", _FRAGMENT,
         "rule 'distilled-names-contract': distillation_status is distilled but 'contract' is missing (§4.1)")]
    assert lint(_profiled(tmp_path / "pending", keys, _meeting(_MEETING_FIELDS)))[0].items == []
    # a rule applies to a type no layer declares as well
    loose = "rules:\n  - { name: memos-name-an-author, when: { type: Memo }, require: [author], level: warn }\n"
    k = _profiled(tmp_path / "memo", loose, extra={"fragments/2026-10-31-memo.md": _concept("Memo")})
    assert _profile_items(lint(k)[0]) == [("WARN", "PROFILE_RULE", "fragments/2026-10-31-memo.md",
                                           "rule 'memos-name-an-author': 'author' is missing (§4.1)")]


def test_a_type_its_directory_family_does_not_allow_is_profile_type_not_allowed(tmp_path):
    keys = _MEETING + "families:\n  /base/questions/: { types: [Open Question] }\n  /base/clients/: { types: [Knowledge Fragment] }\n"
    extra = {"base/questions/refund.md": _concept("Term"), "base/questions/deep/memo.md": _concept("Memo"),
             "base/questions/ok.md": _concept("Open Question", _QUESTION_FIELDS),
             "base/clients/acme.md": _meeting(_MEETING_FIELDS)}  # a local type extending an allowed one is allowed
    found = sorted(_profile_items(lint(_profiled(tmp_path, keys, extra=extra))[0]))
    msg = "type '{}' is not allowed in family /base/questions/, which allows Open Question (§4.1)"
    assert found == [("ERROR", "PROFILE_TYPE_NOT_ALLOWED", "base/questions/deep/memo.md", msg.format("Memo")),
                     ("ERROR", "PROFILE_TYPE_NOT_ALLOWED", "base/questions/refund.md", msg.format("Term"))]


def test_a_value_of_the_wrong_declared_field_type_is_profile_field_type(tmp_path):
    cases = {
        "attendees: three\n": ("WARN", "attendees 'three' is not an integer (§4.1)"),
        "billable: maybe\n": ("ERROR", "billable 'maybe' is not a boolean (§4.1)"),
        'signed_on: "2026-02-30"\n': ("ERROR", "signed_on '2026-02-30' is not a date (§4.1)"),
        "contacts: [human:ann, Bob]\n": ("ERROR", "an item of contacts 'Bob' is not an actor (§4.1)"),
        "contract: base/contracts/acme.md\n": ("ERROR", "contract 'base/contracts/acme.md' is not a path (§4.1)"),
    }
    for n, (line, (level, msg)) in enumerate(cases.items()):
        k = _profiled(tmp_path / str(n), _MEETING, _meeting(_MEETING_FIELDS + line))
        assert _profile_items(lint(k)[0]) == [(level, "PROFILE_FIELD_TYPE", _FRAGMENT, msg)], line
    good = "attendees: 3\nbillable: false\nsigned_on: 2026-02-28\ncontacts: [human:ann]\ncontract: /base/c.md\nclient: 42\n"
    k = _profiled(tmp_path / "good", _MEETING, _meeting(_FRAGMENT_FIELDS + good))  # client: 42 is still text
    assert lint(k)[0].items == []


def test_a_key_no_source_declares_warns_only_in_a_bundle_with_a_profile(tmp_path):
    fields = _MEETING_FIELDS + "mood: calm\n"
    k = _profiled(tmp_path, _MEETING, _meeting(fields))
    assert _profile_items(lint(k)[0]) == [("WARN", "PROFILE_UNKNOWN_KEY", _FRAGMENT,
                                           "key 'mood' is declared by no layer for Client Meeting (§4.1)")]
    # keys a required, fixed or forbidden names, and the profile's own keys, are declared; a type no layer
    # declares is tolerated, so its keys are not reported
    keys = _MEETING + "by_type:\n  Knowledge Fragment: { required: [mood] }\nfixed:\n  okf_lang: { value: en }\n"
    k = _profiled(tmp_path / "declared", keys, _meeting(fields + "okf_lang: en\n"),
                  extra={"fragments/2026-10-31-memo.md": _concept("Memo", "anything: 1\n")})
    assert lint(k)[0].items == []
    # without a base/profile.md, no key is unknown
    (tmp_path / "none").mkdir()
    k = _bundle_30(tmp_path / "none")
    (k / _FRAGMENT).write_text(_concept("Knowledge Fragment", _FRAGMENT_FIELDS + "mood: calm\n"), encoding="utf-8")
    assert lint(k)[0].items == []


def _builtin_uncoded_bundle(tmp_path, own: str | None) -> Path:
    """A 3.0 bundle whose ADR, System and Open Question break the built-in profile's fields without a code;
    own, when given, is written as its base/profile.md."""
    adr = _concept("Architecture Decision", "decision_status: deprecated\nsupersedes: ADR-0001\nadr_id: 7\n")
    system = _concept("System", "owner: [payments]\nruntime: 3\n")
    question = _QUESTION_FIELDS.replace("/fragments/2026-10-31-meeting.md", "fragments/x.md") + "blocks: nothing\n"
    k = _question_bundle(tmp_path, question)
    for rel, text in {"base/decisions/ADR-0002-x.md": adr, "base/systems/pay.md": system}.items():
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
    if own is not None:
        (k / "base" / "profile.md").write_text(_domain_profile(own), encoding="utf-8")
    return k


def test_the_builtin_profile_items_without_a_code_are_checked_in_a_bundle_with_a_profile(tmp_path, capsys):
    """With a base/profile.md, decision_status, supersedes, owner, asked_in, blocks and the like are checked at
    their declared level under the generic codes, their source the built-in layer."""
    k = _builtin_uncoded_bundle(tmp_path, "fixed: {}\n")
    assert sorted(_profile_items(lint(k)[0])) == [
        ("ERROR", "PROFILE_ENUM", "base/decisions/ADR-0002-x.md",
         "decision_status 'deprecated' is not one of proposed|accepted|superseded|rejected (§4.1)"),
        ("ERROR", "PROFILE_FIELD_TYPE", "base/decisions/ADR-0002-x.md", "supersedes 'ADR-0001' is not a path (§4.1)"),
        ("ERROR", "PROFILE_FIELD_TYPE", "base/systems/pay.md", "owner '['payments']' is not a string (§4.1)"),
        ("WARN", "PROFILE_FIELD_TYPE", _QUESTION, "an item of blocks 'nothing' is not a path (§4.1)"),
        ("WARN", "PROFILE_FIELD_TYPE", _QUESTION, "asked_in 'fragments/x.md' is not a path (§4.1)"),
    ]  # adr_id: 7 and runtime: 3 are still text
    capsys.readouterr()
    main([str(k), "--json"])
    found = [i for i in json.loads(capsys.readouterr().out)["findings"] if i["code"] in _CONCEPT_CODES]
    assert {i["source"] for i in found} == {BUILTIN} and len(found) == 5


def test_the_builtin_profile_items_without_a_code_add_no_finding_without_a_profile(tmp_path):
    k = _builtin_uncoded_bundle(tmp_path, None)
    assert not [i for i in lint(k)[0].items if i["code"].startswith("PROFILE_")]
    assert _profile_items(lint(k)[0]) == []


def test_a_type_alias_is_treated_as_the_type_it_stands_for_by_every_check(tmp_path):
    keys = "aliases:\n  types: { Fragmento: Knowledge Fragment, Registro de conflictos: Conflict Log }\n"
    frag = _concept("Fragmento", "occurred_at: 2026-10-31\ndistillation_status: done\nmood: calm\n")
    k = _profiled(tmp_path, keys, frag)
    found = [(i["level"], i["code"], i["path"]) for i in lint(k)[0].items]
    assert found == [("WARN", "FRAGMENT_NO_FIELD", _FRAGMENT)] * 2 + [
        ("ERROR", "BAD_DISTILLATION_STATUS", _FRAGMENT), ("WARN", "PROFILE_UNKNOWN_KEY", _FRAGMENT)]
    # a second Conflict Log under its local name: the cross-concept count and the layer rule see the alias
    k = _profiled(tmp_path / "logs", keys)
    (k / "conflicts-2.md").write_text(_CONFLICT_LOG.replace("type: Conflict Log", "type: Registro de conflictos"),
                                      encoding="utf-8")
    (k / "index.md").write_text((k / "index.md").read_text(encoding="utf-8")
                                .replace("* [base]", "* [C2](conflicts-2.md) - C.\n* [base]"), encoding="utf-8")
    assert [(i["code"], i["path"]) for i in lint(k)[0].items] == [("PROFILE_MANY_CONFLICT_LOGS", "conflict-log.md")]
    # an open question under a local name gets its review check
    keys_q = "aliases:\n  types: { Pregunta: Open Question }\n"
    k = _question_bundle(tmp_path / "q", _QUESTION_FIELDS + "review_on: 2020-01-01\n")
    (k / _QUESTION).write_text((k / _QUESTION).read_text(encoding="utf-8").replace("type: Open Question", "type: Pregunta"),
                               encoding="utf-8")
    (k / "base" / "profile.md").write_text(_domain_profile(keys_q), encoding="utf-8")
    assert ("WARN", "QUESTION_REVIEW_DUE") in _codes(lint(k)[0], _QUESTION)
    # --no-profile applies no alias
    k = _profiled(tmp_path / "np", keys, frag)
    assert lint(k, profile=False)[0].items == []


def test_a_value_alias_is_read_as_the_value_it_stands_for(tmp_path):
    keys = (_MEETING + "aliases:\n  fields: { cliente: client }\n"
            "  values: [{ from: { ingerido: true }, to: { distillation_status: distilled } }]\n"
            "rules:\n  - { name: distilled-names-contract, when: { distillation_status: distilled }, require: [contract] }\n")
    fields = _FRAGMENT_FIELDS.replace("distillation_status: pending\n", "ingerido: true\n") + "cliente: Acme\n"
    rep, _, _ = lint(_profiled(tmp_path, keys, _meeting(fields)))
    # distillation_status is present (no FRAGMENT_NO_FIELD) and distilled (the rule holds); neither the
    # local field name nor the alias's key is unknown, and client is not missing
    assert [(i["code"], i["message"]) for i in rep.items if i["code"] != "FRAGMENT_UNCITED"] == [
        ("PROFILE_RULE", "rule 'distilled-names-contract': distillation_status is distilled but 'contract' is missing (§4.1)")]
    assert [i["code"] for i in rep.items].count("FRAGMENT_UNCITED") == 1  # the alias reads it as distilled there too
    # the concept's own value under the declared name wins
    own = fields + "distillation_status: pending\n"
    assert lint(_profiled(tmp_path / "own", keys, _meeting(own)))[0].items == []
    # an alias whose from does not hold reads nothing, and its key is still a declared local name
    no = fields.replace("ingerido: true", "ingerido: false")
    assert [i["code"] for i in lint(_profiled(tmp_path / "no", keys, _meeting(no)))[0].items] == ["FRAGMENT_NO_FIELD"]


_VALIDATOR_SCRIPT = ('printf "%s\\n" "$PWD" "$@" > ran.txt\n'
                     'echo "token=FAKE-TOKEN-0001 password=hunter2-FAKE secret=FAKE-SECRET-0002 api_key=FAKE-KEY-0003"\n'
                     'echo "Authorization: Bearer FAKE-AUTH-0004" >&2\necho "Bearer FAKE-BEARER-0005"\n'
                     'echo "blob 0123456789abcdef0123456789abcdef01234567 and QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo0NTY3ODk="\n'
                     'exit 3\n')
_FAKE_SECRETS = ("FAKE-TOKEN-0001", "hunter2-FAKE", "FAKE-SECRET-0002", "FAKE-KEY-0003", "FAKE-AUTH-0004",
                 "FAKE-BEARER-0005", "0123456789abcdef0123456789abcdef01234567",
                 "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo0NTY3ODk=", "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo0NTY3ODk")


def _validator_bundle(tmp_path, families: str = "") -> Path:
    keys = (_MEETING + "validator:\n  - { name: meetings-check, types: [Knowledge Fragment], " + families
            + "command: \"sh check.sh --strict\" }\n")
    k = _profiled(tmp_path, keys, _meeting(_MEETING_FIELDS), extra={
        "base/questions/q.md": _concept("Open Question", _QUESTION_FIELDS)})
    (k / "check.sh").write_text(_VALIDATOR_SCRIPT, encoding="utf-8")
    return k


def test_a_validator_without_the_flag_is_a_notice_and_never_runs(tmp_path, capsys):
    k = _validator_bundle(tmp_path)
    rep, _, _ = lint(k)
    assert rep.notices == ["validator meetings-check not run (use --run-validators)"]
    assert not [i for i in rep.items if i["code"] in _CONCEPT_CODES]
    assert rep.items == []
    capsys.readouterr()
    assert main([str(k), "--strict"]) == 0  # a notice never changes the exit code
    assert "NOTICE validator meetings-check not run (use --run-validators)" in capsys.readouterr().out
    assert main([str(k), "--json"]) == 0 and not (k / "ran.txt").exists()
    assert json.loads(capsys.readouterr().out)["notices"] == rep.notices


def test_run_validators_runs_from_the_bundle_root_and_masks_its_failure(tmp_path, capsys):
    k = _validator_bundle(tmp_path, "families: [/base/questions/], ")
    capsys.readouterr()
    assert main([str(k), "--run-validators"]) == 1
    text = capsys.readouterr().out
    ran = (k / "ran.txt").read_text(encoding="utf-8").splitlines()
    assert Path(ran[0]).resolve() == k.resolve()
    assert ran[1:] == ["--strict", "base/questions/q.md", _FRAGMENT]  # its types (subtypes too) and its families
    assert main([str(k), "--run-validators", "--json"]) == 1
    out = capsys.readouterr().out
    [f] = [i for i in json.loads(out)["findings"] if i["code"] == "PROFILE_VALIDATOR"]
    assert (f["level"], f["path"], f["source"]) == ("ERROR", OWN_REL, OWN_REL)
    assert f["message"].startswith("validator meetings-check failed (exit 3): token=[masked] password=[masked]")
    assert "Authorization: [masked]" in f["message"] and "Bearer [masked]" in f["message"]
    for s in _FAKE_SECRETS:
        assert s not in text and s not in out, s
    assert "NOTICE" not in text


def test_validator_output_is_truncated_and_a_command_that_cannot_start_fails(tmp_path):
    long = "x" * 5000
    assert mask_secrets(long) == "[masked]"
    k = _validator_bundle(tmp_path)
    (k / "check.sh").write_text("for i in $(seq 1 600); do printf 'line %s. ' $i; done\nexit 1\n", encoding="utf-8")
    [f] = [i for i in lint(k, validators=True)[0].items if i["code"] == "PROFILE_VALIDATOR"]
    assert f["message"].endswith(" [truncated]") and len(f["message"]) < VALIDATOR_OUTPUT_MAX + 100
    (k / "base" / "profile.md").write_text((k / "base" / "profile.md").read_text(encoding="utf-8")
                                           .replace("sh check.sh", "no-such-validator-binary"), encoding="utf-8")
    [f] = [i for i in lint(k, validators=True)[0].items if i["code"] == "PROFILE_VALIDATOR"]
    assert "failed (could not start)" in f["message"]
    # a validator that passes, or that matches no concept, adds nothing
    (k / "base" / "profile.md").write_text((k / "base" / "profile.md").read_text(encoding="utf-8")
                                           .replace("no-such-validator-binary", "true"), encoding="utf-8")
    assert not [i for i in lint(k, validators=True)[0].items if i["code"] == "PROFILE_VALIDATOR"]


def _every_violation_bundle(tmp_path) -> Path:
    keys = (_MEETING + "families:\n  /base/questions/: { types: [Open Question], required: [tags] }\n"
            "forbidden:\n  internal_notes: { reason: Internal notes stay out }\nfixed:\n  okf_lang: { value: en }\n"
            "rules:\n  - { name: distilled-names-contract, when: { distillation_status: distilled }, require: [contract] }\n"
            "validator:\n  - { name: meetings-check, types: [Client Meeting], command: \"sh check.sh\" }\n")
    fields = (_FRAGMENT_FIELDS.replace("pending", "distilled") + "kind: lunch\nattendees: many\nmood: calm\n"
              "internal_notes: x\nokf_lang: es\n")
    k = _profiled(tmp_path, keys, _meeting(fields), extra={"base/questions/t.md": _concept("Term")})
    (k / "check.sh").write_text(_VALIDATOR_SCRIPT, encoding="utf-8")
    return k


def test_no_profile_reports_no_profile_check_at_all(tmp_path, capsys):
    k = _every_violation_bundle(tmp_path)
    rep, _, _ = lint(k, profile=False, validators=True)
    assert rep.items == [] and rep.notices == [] and not (k / "ran.txt").exists()
    capsys.readouterr()
    main([str(k), "--no-profile", "--run-validators", "--json"])
    assert json.loads(capsys.readouterr().out)["findings"] == []


def test_json_gives_every_new_code_its_level_and_the_source_that_declared_it(tmp_path, capsys):
    k = _every_violation_bundle(tmp_path)
    capsys.readouterr()
    assert main([str(k), "--json", "--run-validators"]) == 1
    found = {(i["code"], i["level"], i.get("source")) for i in json.loads(capsys.readouterr().out)["findings"]
             if i["code"] in _CONCEPT_CODES}
    assert found == {(c, "WARN" if c in ("PROFILE_FIELD_TYPE", "PROFILE_UNKNOWN_KEY") else "ERROR", OWN_REL)
                     for c in _CONCEPT_CODES}


def test_family_requirements_with_their_own_code_apply_under_the_family_only(tmp_path):
    keys = ("families:\n  /base/questions/:\n    required: { review_on: { level: warn, code: MY_REVIEW } }\n"
            "    fixed: { okf_lang: { value: en, code: MY_LANG } }\n"
            "    forbidden: { draft_notes: { reason: no drafts, level: warn, code: MY_DRAFTS } }\n"
            "  /base/questions/legal/: { required: [tags] }\n")
    k = _profiled(tmp_path, keys, _concept("Knowledge Fragment", _FRAGMENT_FIELDS + "okf_lang: es\ndraft_notes: x\n"),
                  extra={"base/questions/a.md": _concept("Open Question", _QUESTION_FIELDS + "okf_lang: es\ndraft_notes: x\n"),
                         "base/questions/legal/b.md": _concept("Open Question", _QUESTION_FIELDS + "review_on: 2999-01-01\n")})
    found = sorted((i["path"], i["level"], i["code"]) for i in lint(k)[0].items if i["path"].startswith("base/"))
    assert found == [("base/questions/a.md", "ERROR", "MY_LANG"), ("base/questions/a.md", "WARN", "MY_DRAFTS"),
                     ("base/questions/a.md", "WARN", "MY_REVIEW"),
                     ("base/questions/legal/b.md", "ERROR", "PROFILE_REQUIRED")]  # nested families: both apply


def test_examples_knowledge_lints_with_its_profile_and_its_four_known_warnings():
    import pytest

    bundle = next((p / "examples" / "knowledge" for p in Path(__file__).resolve().parents
                   if (p / "examples" / "knowledge" / "base" / "profile.md").is_file()), None)
    if bundle is None:
        pytest.skip("examples/knowledge with its base/profile.md not beside this script")
    rep, _, _ = lint(bundle)
    assert [(i["level"], i["code"], i["path"]) for i in rep.items] == [
        ("WARN", "BROKEN_LINK", "base/decisions/ADR-0001-adopt-kafka.md"),
        ("WARN", "STALE", "base/runbooks/consumer-lag-alert.md"),
        ("WARN", "VERIFIED_STALE", "base/decisions/ADR-0001-adopt-kafka.md"),  # rewritten by the 3.0 migration
        ("WARN", "FRAGMENT_UNCITED", "fragments/2026-10-28-finance-dispute-window-ask.md")]  # its only output: a ticket
    prof = load_profile(bundle)
    assert prof.has_own and any(t.get("extends") for t in prof.types.values() if t["source"] == OWN_REL)
    assert prof.families and prof.rules[-1]["source"] == OWN_REL and prof.aliases["types"]
    local = {t for t, d in prof.types.items() if d["source"] == OWN_REL}
    assert any(str(d.frontmatter.get("type")) in local for d in walk_bundle(bundle) if d.frontmatter)


def test_mask_secrets():
    assert mask_secrets("token=abc key=def password=p secret=s") == "token=[masked] key=[masked] password=[masked] secret=[masked]"
    assert mask_secrets("Authorization: Bearer xyz rest") == "Authorization: [masked] rest"
    assert mask_secrets("Bearer abc.def") == "Bearer [masked]"
    assert mask_secrets("id " + "a1" * 16 + " end") == "id [masked] end"
    assert mask_secrets("short abcdef0123 ok") == "short abcdef0123 ok"


_TEMPLATE_FILL = {"actor": "okf-builder/test", "now": "2026-11-02T12:00:00Z", "iso_date": "2999-01-01",
                  "YYYY-MM-DD": "2999-01-01", "date": "2026-11-02", "occurred_at": "2026-11-02",
                  "participants": "human:ann", "owner": "ann", "team": "payments", "nnnn": "0002",
                  "fragment_file": "2026-11-02-demo.md"}
_TEMPLATE_FILE = {"Project": "project.md", "Conflict Log": "conflict-log.md",
                  "Architecture Decision": "ADR-0002-demo.md", "Knowledge Fragment": "2026-11-02-demo.md"}


def _fill_template(text: str) -> str:
    """A template with each {{placeholder}} filled minimally: a known name its value, a choice its first option,
    a URL a URL, anything else a word."""
    def one(m) -> str:
        inner = m.group(1).strip()
        if inner in _TEMPLATE_FILL:
            return _TEMPLATE_FILL[inner]
        if ":" in inner and "|" in inner:
            inner = inner.split(":", 1)[1].strip()
        if "|" in inner:
            return inner.split("|")[0]
        return "https://example.com/demo" if inner.endswith(("_url", "_uri")) else "demo"
    return re.sub(r"\{\{(.*?)\}\}", one, text)


def _template_sweep(tmp_path) -> list[tuple] | None:
    """Each concept template filled minimally, in its type's usual directory, in a 3.0 bundle with an empty
    base/profile.md, and the Domain Profile template filled as the base/profile.md of another: every PROFILE_*
    finding as (template, level, code, message). None when the templates are not beside this script."""
    templates = Path(__file__).resolve().parent.parent / "templates"
    if not templates.is_dir():
        return None
    k = _profiled(tmp_path / "concepts", "")
    types = load_profile(k).types
    where = {}
    for tpl in sorted(templates.glob("*.md")):
        if tpl.name in ("log.md", "root-index.md", "domain-profile.md"):
            continue
        text = _fill_template(tpl.read_text(encoding="utf-8"))
        t = re.search(r"^type: (.+)$", text, re.M).group(1).strip()
        d = (types[t].get("directory") or "/").strip("/")
        rel = "/".join(x for x in (d, _TEMPLATE_FILE.get(t, "demo.md")) if x)
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
        if rel not in ("project.md", "conflict-log.md"):
            _list_in_indexes(k, rel)
        where[rel] = tpl.name
    out = [(where.get(i["path"], i["path"]), i["level"], i["code"], i["message"])
           for i in lint(k)[0].items if i["code"].startswith("PROFILE_")]
    p = _profiled(tmp_path / "profile", "")
    (p / "base" / "profile.md").write_text(_fill_template((templates / "domain-profile.md").read_text(encoding="utf-8")),
                                           encoding="utf-8")
    out += [("domain-profile.md", i["level"], i["code"], i["message"])
            for i in lint(p)[0].items if i["code"].startswith("PROFILE_")]
    return sorted(out)


def test_every_template_lints_against_the_builtin_profile_with_no_profile_finding(tmp_path):
    """Each template's keys are declared for its type (no PROFILE_UNKNOWN_KEY) and its values have their declared
    types, in a bundle with a base/profile.md: owner: team:<team> is a string owner (ADR-0027)."""
    import pytest

    found = _template_sweep(tmp_path)
    if found is None:
        pytest.skip("templates/ not beside this script")
    assert found == []


def test_json_names_the_layer_each_broken_item_comes_from(tmp_path, capsys):
    """The source of a finding is the layer that declared the broken item: an extended profile (its family and
    its forbidden key), the bundle's own profile, the built-in layer."""
    shared = ("families:\n  /base/questions/: { types: [Open Question] }\n"
              "forbidden:\n  draft_notes: { reason: no drafts }\n")
    own = "extends: [/base/shared.md]\nfixed:\n  okf_lang: { value: en }\n"
    k = _profiled(tmp_path, own, _concept("Knowledge Fragment", _FRAGMENT_FIELDS + "draft_notes: x\nokf_lang: es\n"),
                  extra={"base/shared.md": _domain_profile(shared), "base/questions/t.md": _concept("Term"),
                         "base/decisions/ADR-0002-x.md": _concept("Architecture Decision", "decision_status: deprecated\n")})
    capsys.readouterr()
    main([str(k), "--json"])
    found = sorted((i["code"], i["path"], i.get("source")) for i in json.loads(capsys.readouterr().out)["findings"])
    assert found == [("PROFILE_ENUM", "base/decisions/ADR-0002-x.md", BUILTIN),
                     ("PROFILE_FIXED", _FRAGMENT, OWN_REL),
                     ("PROFILE_FORBIDDEN", _FRAGMENT, "base/shared.md"),
                     ("PROFILE_TYPE_NOT_ALLOWED", "base/questions/t.md", "base/shared.md")]


def test_project_md_typed_with_an_alias_of_project_is_the_project(tmp_path):
    k = _profiled(tmp_path, "aliases:\n  types: { Proyecto: Project }\n")
    (k / "project.md").write_text((k / "project.md").read_text(encoding="utf-8").replace("type: Project", "type: Proyecto"),
                                  encoding="utf-8")
    assert "type: Proyecto" in (k / "project.md").read_text(encoding="utf-8")
    assert lint(k)[0].items == []  # neither PROFILE_PROJECT_TYPE nor PROFILE_OUTSIDE_LAYER
    assert [i["code"] for i in lint(k, profile=False)[0].items] == []  # --no-profile reads no profile check


def test_a_type_scoped_validator_covers_a_concept_typed_with_an_alias(tmp_path):
    keys = ("aliases:\n  types: { Fragmento: Knowledge Fragment }\n"
            "validator:\n  - { name: fragments, types: [Knowledge Fragment], command: \"sh check.sh\" }\n")
    k = _profiled(tmp_path, keys, _concept("Fragmento", _FRAGMENT_FIELDS),
                  extra={"base/questions/q.md": _concept("Open Question", _QUESTION_FIELDS)})
    (k / "check.sh").write_text('printf "%s\\n" "$@" > ran.txt\n', encoding="utf-8")
    assert lint(k, validators=True)[0].items == []
    assert (k / "ran.txt").read_text(encoding="utf-8").splitlines() == [_FRAGMENT]


def test_a_family_that_lists_a_type_alias_allows_the_type_it_stands_for(tmp_path):
    keys = ("aliases:\n  types: { Pregunta: Open Question }\n"
            "families:\n  /base/questions/: { types: [Pregunta] }\n")
    k = _profiled(tmp_path, keys, extra={"base/questions/q.md": _concept("Open Question", _QUESTION_FIELDS),
                                         "base/questions/t.md": _concept("Term")})
    assert _profile_items(lint(k)[0]) == [
        ("ERROR", "PROFILE_TYPE_NOT_ALLOWED", "base/questions/t.md",
         "type 'Term' is not allowed in family /base/questions/, which allows Open Question (§4.1)")]


def test_a_validator_family_does_not_cover_a_sibling_directory_that_shares_its_prefix(tmp_path):
    keys = "validator:\n  - { name: questions, families: [/base/questions], command: \"sh check.sh\" }\n"
    k = _profiled(tmp_path, keys, extra={"base/questions/q.md": _concept("Open Question", _QUESTION_FIELDS),
                                         "base/questions-old/q.md": _concept("Open Question", _QUESTION_FIELDS)})
    (k / "check.sh").write_text('printf "%s\\n" "$@" > ran.txt\n', encoding="utf-8")
    lint(k, validators=True)
    assert (k / "ran.txt").read_text(encoding="utf-8").splitlines() == ["base/questions/q.md"]


def test_a_secret_across_the_truncation_point_is_masked_whole(tmp_path):
    """Masking runs before truncation: a secret that starts before VALIDATOR_OUTPUT_MAX and ends after it never
    shows a part of itself."""
    secret = "Zx9" * 12  # 36 characters, one run
    prefix = "validator meetings-check failed (exit 1): "
    filler = ("ab " * VALIDATOR_OUTPUT_MAX)[:VALIDATOR_OUTPUT_MAX - 10]  # the secret starts 10 characters before the cut
    k = _validator_bundle(tmp_path)
    (k / "out.txt").write_text(filler + secret + " tail\n", encoding="utf-8")
    (k / "check.sh").write_text("cat out.txt\nexit 1\n", encoding="utf-8")
    [f] = [i for i in lint(k, validators=True)[0].items if i["code"] == "PROFILE_VALIDATOR"]
    assert f["message"].startswith(prefix) and "[masked]" in f["message"]
    assert secret[:8] not in f["message"] and secret[-8:] not in f["message"]


def test_a_validator_that_times_out_fails(tmp_path, monkeypatch):
    monkeypatch.setitem(globals(), "VALIDATOR_TIMEOUT", 1)
    k = _validator_bundle(tmp_path)
    (k / "check.sh").write_text("exec sleep 10\n", encoding="utf-8")
    [f] = [i for i in lint(k, validators=True)[0].items if i["code"] == "PROFILE_VALIDATOR"]
    assert (f["level"], f["message"]) == ("ERROR", "validator meetings-check failed (timed out after 1s)")


def test_mask_secrets_reads_quoted_values_and_keeps_paths():
    for line, secret in [('password="a b c"', "a b c"), ("password='hunter 2'", "hunter 2"), ("token: abc123", "abc123"),
                         ('"token": "abc123"', "abc123"), ("token = abc123", "abc123"), ("api_key=ZZ99", "ZZ99"),
                         ('{"client_secret": "s3cr3t", "x": 1}', "s3cr3t")]:
        masked = mask_secrets(line)
        assert secret not in masked and "[masked]" in masked, line
    assert mask_secrets('{"client_secret": "s3cr3t", "x": 1}') == '{"client_secret": [masked], "x": 1}'
    b64url = "QUJD-REVG_R0hJSktMTU5PUFFSU1RVVldYWVo0NTY3ODk"
    assert mask_secrets(f"id {b64url} end") == "id [masked] end"
    path = "/Users/someone/repositories/personal/projects"  # 46 characters, a path
    assert len(path) >= 40 and mask_secrets(f"see {path}/x.md") == f"see {path}/x.md"
    for kept in ("fragments/2026-11-02-refund-topic-follow-up.md",
                 "test_a_concept_of_a_local_type_missing_a_required_field_is_profile_required"):
        assert mask_secrets(kept) == kept


def _fake_b64(seed: int, size: int) -> str:
    """A standard-base64 string from seeded random bytes: fake, never a real secret."""
    import base64
    import random
    return base64.b64encode(random.Random(seed).randbytes(size)).decode()


def _fake_secrets() -> list[str]:
    import base64
    b64url = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # noqa: E731
    with_both = [s for s in (_fake_b64(n, 30 + n % 37) for n in range(400)) if "/" in s and "+" in s]
    picked = [next(s for s in with_both if len(s) <= 48), next(s for s in with_both if 56 <= len(s) <= 64),
              next(s for s in with_both if len(s) >= 80)]
    pem = next("MII" + _fake_b64(n, 46)[:61] for n in range(100) if "/" in _fake_b64(n, 46)[:61])
    jwt = ".".join([b64url(b'{"alg":"HS256","typ":"JWT"}'), b64url(b'{"sub":"fake"}'), _fake_b64(3, 32).replace("+", "-")
                    .replace("/", "_").rstrip("=")])
    return [*picked, "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", pem, jwt]


_KEPT_PATHS = (
    "/Users/someone/Documents/Projects/iOSApp2024/Sources/ViewControllers/LoginViewController.swift",
    "/home/ubuntu/projects/MyService2024/src/main/resources/application.yml",
    "/opt/homebrew/Cellar/python@3.12/3.12.7/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/x",
    "/var/lib/docker/overlay2/volumes/postgres_data/_data/base/16384",
    "src/main/java/com/Example/Service.java",
    "src/test/kotlin/org/acme/billing/InvoiceServiceTest.kt",
    "app/src/main/res/drawable-xxhdpi/ic_launcher_foreground.png",
    "https://github.com/jisequilla/okf-builder/pull/53/files",
    "repos/jisequilla/j3r3-okf-builder/contents/plugin/okf-builder/skills",
    "~/repos/personal/j3r3-okf-builder/plugin/okf-builder/skills/okf-standard",
    "./node_modules/@types/node/README.md",
    "components/ui/DataTable/DataTableToolbar.tsx",
)


def test_mask_secrets_masks_a_standard_base64_secret_with_slashes_whole():
    secrets = _fake_secrets()
    assert len(secrets) >= 6 and all("/" in s for s in secrets[:5]) and secrets[-1].startswith("eyJ")
    assert all("+" in s for s in secrets[:3]) and 40 <= min(map(len, secrets[:3])) and max(map(len, secrets[:3])) <= 88
    assert secrets[0].startswith("/")  # once in 64 a base64 secret starts with '/'
    for s in secrets:
        for line in (s, f"out: {s} end", f'"{s}"'):
            masked = mask_secrets(line)
            assert masked == line.replace(s, "[masked]"), len(s)  # the secret is never part of a failure message


def test_mask_secrets_keeps_paths_and_urls_whatever_their_case_and_digits():
    for p in _KEPT_PATHS:
        assert len(p.split()[0]) >= 32 and mask_secrets(f"see {p} now") == f"see {p} now", p
    assert 40 <= len(_KEPT_PATHS[0]) <= 120 and 100 <= len(_KEPT_PATHS[2]) <= 120
    # a 40-hex SHA is masked on its own, in a path as well: the run without '/' rule, as before
    sha = "4abdfa0" + "1" * 33
    assert mask_secrets(f"commits/{sha}") == "commits/[masked]" and mask_secrets(sha) == "[masked]"
    assert mask_secrets(f"/repo/objects/{sha}") == "/repo/objects/[masked]"


def test_mask_secrets_masks_before_a_long_output_is_truncated(tmp_path):
    s = _fake_secrets()[0]
    k = _validator_bundle(tmp_path)
    (k / "check.sh").write_text(f"printf '%0.s.' $(seq 1 {VALIDATOR_OUTPUT_MAX - 20}); echo ' {s}'\nexit 1\n",
                                encoding="utf-8")
    [f] = [i for i in lint(k, validators=True)[0].items if i["code"] == "PROFILE_VALIDATOR"]
    assert s not in f["message"] and s[:12] not in f["message"]


def test_profile_outside_layer_comes_before_the_profile_structure_findings(tmp_path):
    """The order of origin/main: the layer rule, then the profile's structural findings."""
    k = _profiled(tmp_path, "types: [nope]\n")
    (k / "loose.md").write_text("---\ntype: Term\ntitle: L\ndescription: L.\n" + _GEN + "---\n\nText.\n",
                                encoding="utf-8")
    codes = [i["code"] for i in lint(k)[0].items]
    assert codes.index("PROFILE_OUTSIDE_LAYER") < codes.index("PROFILE_INVALID"), codes
    assert codes[:2] == ["PROFILE_OUTSIDE_LAYER", "PROFILE_INVALID"], codes


# --------------------------------------------------------------------------
# Rule layers, foreign profiles, .okfignore, nested bundles and non-OKF directories (ticket A1)
# --------------------------------------------------------------------------
def _write(k: Path, rel: str, text: str) -> None:
    (k / rel).parent.mkdir(parents=True, exist_ok=True)
    (k / rel).write_text(text, encoding="utf-8")


def _with_link(k: Path, target: str) -> None:
    """The fragment's body links to target."""
    f = k / _FRAGMENT
    f.write_text(f.read_text(encoding="utf-8") + f"\nSee [it]({target}).\n", encoding="utf-8")


def _layered_bundle(tmp_path) -> Path:
    """A 3.0 bundle with one finding of each rule layer, and BAD_ISO both from the spec and from the Domain Profile."""
    k = _bundle_30(tmp_path)
    frag = k / _FRAGMENT
    frag.write_text(frag.read_text(encoding="utf-8").replace("occurred_at: 2026-10-31", "occurred_at: 31/10/2026")
                    .replace("status: draft\n", "status: draft\nstale_after: soon\n"), encoding="utf-8")
    _with_link(k, "/base/missing.md")
    p = k / "project.md"
    p.write_text(p.read_text(encoding="utf-8").replace(_GEN, ""), encoding="utf-8")
    return k


_LAYERED = [("ERROR", "PROFILE_NO_GENERATED", "project.md", "okf-profile"),
            ("WARN", "BAD_ISO", _FRAGMENT, "domain-profile"),  # occurred_at, a field the Domain Profile declares
            ("WARN", "BAD_ISO", _FRAGMENT, "spec"),  # stale_after, a spec field
            ("WARN", "BROKEN_LINK", _FRAGMENT, "spec")]


def test_every_finding_names_its_rule_layer_and_json_counts_them_per_layer(tmp_path, capsys):
    k = _layered_bundle(tmp_path)
    assert main([str(k), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert sorted((i["level"], i["code"], i["path"], i["layer"]) for i in data["findings"]) == sorted(_LAYERED)
    assert data["by_layer"] == {"spec": {"errors": 0, "warnings": 2}, "okf-profile": {"errors": 1, "warnings": 0},
                                "domain-profile": {"errors": 0, "warnings": 1}}
    assert (data["errors"], data["warnings"]) == (1, 3)
    # spec is what still runs under --no-profile, and nothing else
    rep, _, _ = lint(k, profile=False)
    spec = sorted((i["code"], i["path"], i["message"]) for i in rep.items)
    assert all(i["layer"] == "spec" for i in rep.items)
    assert spec == sorted((i["code"], i["path"], i["message"]) for i in data["findings"] if i["layer"] == "spec")


def test_the_summary_line_adds_errors_and_warnings_per_rule_layer(tmp_path, capsys):
    assert main([str(_layered_bundle(tmp_path))]) == 1
    last = capsys.readouterr().out.splitlines()[-1]
    assert " · 1 errors · 3 warnings (spec 0/2 · okf-profile 1/0 · domain-profile 0/1) → NOT CONFORMANT" in last


_FOREIGN = "acme/handbook-1.0"


def _foreign(k: Path) -> Path:
    index = k / "index.md"
    index.write_text(index.read_text(encoding="utf-8").replace(PROFILE_30, _FOREIGN), encoding="utf-8")
    return k


def test_a_foreign_profile_gets_spec_checks_and_one_notice_for_the_rest(tmp_path, capsys):
    k = _foreign(_bundle_30(tmp_path))
    frag = k / _FRAGMENT
    frag.write_text(frag.read_text(encoding="utf-8").replace("origin: Weekly meeting\n", "")
                    .replace(_GEN, ""), encoding="utf-8")
    _write(k, "base/profile.md", _domain_profile("types: {}\n"))
    _write(k, "base/index.md", "# base\n\n* [Profile](profile.md) - P.\n")
    rep, _, _ = lint(k)
    assert rep.items == [] and not rep.profile_outdated
    skipped = sorted((i["code"], i["layer"]) for i in rep.skipped)
    assert skipped == [("FRAGMENT_NO_FIELD", "domain-profile"), ("PROFILE_NO_GENERATED", "okf-profile")]
    assert rep.notices == [f"profile {_FOREIGN} is not one okf-builder ships (knowledge/2.0, knowledge/3.0): spec "
                           "checks only, 2 okf-profile and domain-profile findings skipped "
                           "(FRAGMENT_NO_FIELD, PROFILE_NO_GENERATED)"]
    assert main([str(k), "--strict"]) == 0
    capsys.readouterr()
    assert main([str(k), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert sorted(i["code"] for i in data["skipped"]) == ["FRAGMENT_NO_FIELD", "PROFILE_NO_GENERATED"]
    assert data["findings"] == [] and data["errors"] == 0
    _with_link(k, "/base/missing.md")  # a spec finding is still reported
    assert [(i["code"], i["layer"]) for i in lint(k)[0].items] == [("BROKEN_LINK", "spec")]


def test_okfignore_reads_gitignore_style_globs():
    from okf_common import OkfIgnore

    ign = OkfIgnore.parse("# comment\n\ndrafts/\n*.tmp.md\n!keep.tmp.md\n/top.md\ndocs/**/old.md\n\\#hash.md\n")
    assert ign.match("drafts", True) and ign.match("base/drafts", True) and not ign.match("drafts", False)
    assert ign.match("a.tmp.md", False) and ign.match("base/x/a.tmp.md", False)
    assert not ign.match("keep.tmp.md", False) and not ign.match("base/keep.tmp.md", False)
    assert ign.match("top.md", False) and not ign.match("base/top.md", False)
    assert ign.match("docs/old.md", False) and ign.match("docs/a/b/old.md", False) and not ign.match("x/docs/old.md", False)
    assert ign.match("#hash.md", False) and not ign.match("comment", False)
    assert not OkfIgnore.parse("").match("a.md", False)


def test_okfignore_paths_are_not_read_counted_or_link_checked_and_json_lists_them(tmp_path, capsys):
    k = _bundle_30(tmp_path)
    _write(k, ".okfignore", "# work in progress\ndrafts/\n*.tmp.md\n")
    _write(k, "drafts/a.md", "no frontmatter\n")
    _write(k, "drafts/deep/b.md", "---\nbad: [\n---\n")
    _write(k, "base/scratch.tmp.md", "no frontmatter, [broken](/nowhere.md)\n")
    _with_link(k, "/drafts/a.md")
    rep, _, _ = lint(k)
    assert rep.items == [] and rep.notices == [".okfignore excludes 2 paths, not read: drafts/, base/scratch.tmp.md"]
    assert sorted(rep.ignored) == ["base/scratch.tmp.md", "drafts/"]
    assert main([str(k), "--strict"]) == 0
    assert " 3 concepts " in capsys.readouterr().out
    assert main([str(k), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert sorted(data["ignored"]) == ["base/scratch.tmp.md", "drafts/"] and data["concepts"] == 3


def test_a_nested_bundle_is_skipped_as_one_notice_and_lints_on_its_own(tmp_path):
    k = _bundle_30(tmp_path)
    nested = k / "base" / "vendor"
    _write(nested, "index.md", '---\nokf_version: "0.2"\n---\n\n# Vendor\n\n* [X](x.md) - X.\n')
    _write(nested, "x.md", "---\ntitle: X\ndescription: X.\n---\n\nText.\n")
    _with_link(k, "/base/vendor/x.md")
    rep, _, _ = lint(k)
    assert rep.items == []
    assert rep.notices == ["nested bundle base/vendor/ skipped: its index.md declares its own okf_version; "
                           "lint it on its own"]
    own, _, _ = lint(nested, profile=False)
    assert [i["code"] for i in own.errors] == ["NO_TYPE"]


def test_a_directory_without_okf_frontmatter_is_one_notice_and_a_mixed_one_keeps_its_findings(tmp_path):
    k = _bundle_30(tmp_path)
    _write(k, "base/notes/a.md", "Plain notes.\n")
    _write(k, "base/notes/b.md", "---\nlayout: post\n---\n\nA Jekyll page.\n")
    _write(k, "base/mixed/a.md", "---\ntype: Term\ntitle: A\ndescription: A.\n" + _GEN + "---\n\nText.\n")
    _write(k, "base/mixed/b.md", "Plain.\n")
    rep, _, _ = lint(k)
    assert rep.notices == ["base/notes/ is not OKF: 2 Markdown files without OKF frontmatter and no index.md, skipped"]
    assert not [i for i in rep.items if i["path"].startswith("base/notes/")]
    assert ("ERROR", "NO_FRONTMATTER") in _codes(rep, "base/mixed/b.md")


_NOT_A_LAYER = ("ERROR", "PROFILE_OUTSIDE_LAYER", "notes/", "okf-profile",
                "profile knowledge/3.0: notes/ is not a layer and holds 2 Markdown files without OKF frontmatter; "
                "move them under base/ or list the directory in .okfignore")


def test_a_non_okf_directory_at_the_root_of_a_30_bundle_is_one_outside_layer_error(tmp_path):
    """ADR-0018 decision 3: rule 12 still applies at the root, once for the directory, not once per file."""
    k = _bundle_30(tmp_path)
    _write(k, "notes/a.md", "Plain notes.\n")
    _write(k, "notes/b.md", "---\nlayout: post\n---\n\nA Jekyll page.\n")
    _write(k, "base/notes/c.md", "Plain notes.\n")
    rep, _, _ = lint(k)
    assert [(i["level"], i["code"], i["path"], i["layer"], i["message"]) for i in rep.items] == [_NOT_A_LAYER]
    assert rep.notices == ["base/notes/ is not OKF: 1 Markdown file without OKF frontmatter and no index.md, skipped"]
    # spec only, a knowledge/2.0 bundle and a foreign profile have no layer rule: the root directory is a notice
    notice = "notes/ is not OKF: 2 Markdown files without OKF frontmatter and no index.md, skipped"
    assert lint(k, profile=False)[0].items == [] and notice in lint(k, profile=False)[0].notices
    index = k / "index.md"
    for other in (PROFILE_20, _FOREIGN):
        index.write_text(re.sub(r'okf_profile: "[^"]*"', f'okf_profile: "{other}"', index.read_text(encoding="utf-8")),
                         encoding="utf-8")
        rep, _, _ = lint(k)
        assert not [i for i in rep.items + rep.skipped if i["path"].startswith("notes/")], other
        assert notice in rep.notices, other


def test_a_declared_okf_version_lint_does_not_support_is_named_not_reported_missing(tmp_path):
    k = _bundle_30(tmp_path)
    index = k / "index.md"
    index.write_text(index.read_text(encoding="utf-8").replace('okf_version: "0.2"', 'okf_version: "0.3"'),
                     encoding="utf-8")
    for profile in (True, False):
        rep, version, origin = lint(k, profile=profile)
        assert [(i["code"], i["layer"]) for i in rep.items] == [("UNSUPPORTED_OKF_VERSION", "spec")], profile
        assert "'0.3'" in rep.items[0]["message"] and (version, origin) == ("0.2", "heuristic")
    index.write_text(index.read_text(encoding="utf-8").replace('okf_version: "0.3"\n', ""), encoding="utf-8")
    assert sorted(i["code"] for i in lint(k)[0].items) == ["NO_OKF_VERSION", "PROFILE_OKF_VERSION"]


def test_profiles_under_a_foreign_profile_gives_a_notice_for_the_unread_domain_profile(tmp_path, capsys):
    k = _foreign(_bundle_30(tmp_path))
    _write(k, "base/profile.md", _domain_profile("types:\n  T:\n    fields: {}\n    bogus: 1\n"))
    _write(k, "base/index.md", "# base\n\n* [Profile](profile.md) - P.\n")
    capsys.readouterr()
    assert main([str(k), "--profiles", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["findings"] == []
    assert data["notices"] == [f"base/profile.md not read: profile {_FOREIGN} is not one okf-builder ships "
                               "(knowledge/2.0, knowledge/3.0): lint runs spec checks only, so the Domain Profile's "
                               "checks (structural ones included) do not run"]
    assert main([str(k), "--profiles"]) == 0
    assert f"NOTICE base/profile.md not read: profile {_FOREIGN}" in capsys.readouterr().out
    # with no Domain Profile file the notice still names the profile; lint keeps its one notice
    (k / "base" / "profile.md").unlink()
    _write(k, "base/index.md", "# base\n\n_(empty)_\n")
    assert main([str(k), "--profiles", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["notices"] == [
        f"profile {_FOREIGN} is not one okf-builder ships (knowledge/2.0, knowledge/3.0): lint runs spec checks "
        "only, so the Domain Profile's checks (structural ones included) do not run"]
    assert len(lint(k)[0].notices) == 1


def test_no_profile_stays_spec_only_with_a_foreign_profile(tmp_path):
    k = _foreign(_layered_bundle(tmp_path))
    rep, _, _ = lint(k, profile=False)
    assert rep.skipped == [] and rep.notices == []
    assert sorted((i["code"], i["layer"]) for i in rep.items) == [("BAD_ISO", "spec"), ("BROKEN_LINK", "spec")]
    assert sorted((i["code"], i["layer"]) for i in lint(k)[0].items) == [("BAD_ISO", "spec"), ("BROKEN_LINK", "spec")]


def _noise_bundle(tmp_path) -> Path:
    """Each source of noise at once: a foreign okf_profile, an ignored directory, a nested bundle, a non-OKF directory."""
    k = _foreign(_bundle_30(tmp_path))
    frag = k / _FRAGMENT
    frag.write_text(frag.read_text(encoding="utf-8").replace("origin: Weekly meeting\n", ""), encoding="utf-8")
    _write(k, ".okfignore", "drafts/\n")
    _write(k, "drafts/a.md", "no frontmatter, [broken](/nowhere.md)\n")
    _write(k, "drafts/b.md", "---\ntitle: B\n---\n\nText.\n")
    _write(k, "base/vendor/index.md", '---\nokf_version: "0.2"\n---\n\n# Vendor\n\n* [X](x.md) - X.\n')
    _write(k, "base/vendor/x.md", "---\ntitle: X\n---\n\nText.\n")
    _write(k, "notes/a.md", "Plain notes.\n")
    _write(k, "notes/b.md", "More notes.\n")
    _with_link(k, "/drafts/a.md")
    return k


def test_a_bundle_with_every_source_of_noise_reports_only_the_expected_notices(tmp_path):
    rep, _, _ = lint(_noise_bundle(tmp_path))
    assert rep.items == [] and rep.ignored == ["drafts/"]
    assert rep.notices == [
        ".okfignore excludes 1 path, not read: drafts/",
        "nested bundle base/vendor/ skipped: its index.md declares its own okf_version; lint it on its own",
        "notes/ is not OKF: 2 Markdown files without OKF frontmatter and no index.md, skipped",
        f"profile {_FOREIGN} is not one okf-builder ships (knowledge/2.0, knowledge/3.0): spec checks only, "
        "1 okf-profile and domain-profile findings skipped (FRAGMENT_NO_FIELD)"]


def test_domain_profile_structural_and_validator_findings_name_the_domain_profile_layer(tmp_path):
    for code, (keys, extra) in _BROKEN_PROFILES.items():
        (tmp_path / code).mkdir()
        k = _bundle_30(tmp_path / code)
        for rel, text in {"base/profile.md": keys, **extra}.items():
            _write(k, rel, _domain_profile(text))
        rep, _, _ = lint(k)
        found = [i for i in rep.items if i["code"] == code]
        assert found and all(i["layer"] == "domain-profile" for i in found), (code, found)
        assert rep.by_layer()["domain-profile"]["errors"] >= len(found) and rep.by_layer()["spec"]["errors"] == 0, code
    [f] = [i for i in lint(_validator_bundle(tmp_path / "v"), validators=True)[0].items
           if i["code"] == "PROFILE_VALIDATOR"]
    assert f["layer"] == "domain-profile"


def test_profiles_gives_a_notice_for_each_path_the_scan_leaves_out(tmp_path, capsys):
    k = _bundle_30(tmp_path)
    _write(k, "base/profile.md", _domain_profile("types: {}\n"))
    _write(k, "base/index.md", "# base\n\n* [Profile](profile.md) - P.\n")
    _write(k, ".okfignore", "drafts/\n")
    _write(k, "drafts/p.md", _domain_profile("types: {}\n"))  # PROFILE_MISPLACED were it read
    _write(k, "base/vendor/index.md", '---\nokf_version: "0.2"\n---\n\n# Vendor\n\n* [X](x.md) - X.\n')
    _write(k, "base/vendor/x.md", "---\ntitle: X\n---\n\nText.\n")
    _write(k, "base/notes/a.md", "Plain notes.\n")
    expected = [".okfignore excludes 1 path, not read: drafts/",
                "nested bundle base/vendor/ skipped: its index.md declares its own okf_version; lint it on its own",
                "base/notes/ is not OKF: 1 Markdown file without OKF frontmatter and no index.md, skipped"]
    capsys.readouterr()
    assert main([str(k), "--profiles", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["findings"] == [] and data["notices"][:3] == expected
    assert data["notices"] == lint(k)[0].notices
    assert main([str(k), "--profiles"]) == 0
    text = capsys.readouterr().out
    assert all(f"NOTICE {n}" in text for n in expected)


def test_a_root_layer_directory_whose_index_declares_okf_version_is_no_nested_bundle(tmp_path):
    for layer in ("base", "fragments"):
        (tmp_path / layer).mkdir()
        k = _bundle_30(tmp_path / layer)
        index = k / layer / "index.md"
        clean = lint(k)[0]
        index.write_text('---\nokf_version: "0.2"\n---\n\n' + index.read_text(encoding="utf-8"), encoding="utf-8")
        rep, _, _ = lint(k)
        assert [(i["code"], i["path"]) for i in rep.items] == [("INDEX_FM", f"{layer}/index.md")], layer
        assert (rep.notices, rep.concepts) == (clean.notices, clean.concepts), layer


def test_a_concept_that_lost_its_type_and_title_keeps_no_type_in_a_directory_of_its_own(tmp_path):
    """Any key of the spec makes a file OKF-shaped (okf_shaped), so its directory is not skipped as non-OKF."""
    keys = ("title: C\n", "description: C.\n", _GEN, "verified: [{ by: process:ci, at: 2026-10-31T18:00:00Z }]\n",
            "sources: [{ resource: https://example.com }]\n", "status: draft\n", "tags: [a]\n",
            "stale_after: 2999-01-01T00:00:00Z\n", "resource: https://example.com\n",
            "timestamp: 2026-10-31T18:00:00Z\n")
    for n, key in enumerate(keys):
        (tmp_path / str(n)).mkdir()
        k = _bundle_30(tmp_path / str(n))
        _write(k, "base/loose/c.md", "---\n" + key + "---\n\nText.\n")
        rep, _, _ = lint(k)
        assert ("ERROR", "NO_TYPE") in _codes(rep, "base/loose/c.md"), key
        assert not [x for x in rep.notices if "is not OKF" in x], key


def test_okfignore_cannot_exclude_a_reserved_file_and_says_so(tmp_path):
    k = _bundle_30(tmp_path)
    _write(k, "base/profile.md", _domain_profile("types: {}\n"))
    _write(k, "base/index.md", "# base\n\n* [Profile](profile.md) - P.\n")
    clean = lint(k)[0]
    _write(k, ".okfignore", "/index.md\nlog.md\nproject.md\nconflict-log.md\nfragments/index.md\nprofile.md\n")
    rep, _, _ = lint(k)
    assert (rep.items, rep.concepts, rep.ignored) == (clean.items, clean.concepts, [])
    reserved = ["conflict-log.md", "index.md", "log.md", "project.md", "base/profile.md", "fragments/index.md"]
    assert rep.notices == [f"cannot ignore {p}: reserved" for p in reserved] + clean.notices
    # base/ as a whole would take base/profile.md with it
    _write(k, ".okfignore", "base/\n")
    rep, _, _ = lint(k)
    assert (rep.items, rep.concepts, rep.ignored) == (clean.items, clean.concepts, [])
    assert rep.notices == ["cannot ignore base/: reserved, it holds base/profile.md"] + clean.notices


def test_a_directory_with_an_index_keeps_the_findings_of_its_plain_files(tmp_path):
    k = _bundle_30(tmp_path)
    _write(k, "base/notes/index.md", "# notes\n\n* [A](a.md) - A.\n")
    _write(k, "base/notes/a.md", "Plain notes.\n")
    rep, _, _ = lint(k)
    assert ("ERROR", "NO_FRONTMATTER") in _codes(rep, "base/notes/a.md") and rep.notices == []


def test_a_root_layer_directory_of_plain_files_keeps_their_findings(tmp_path):
    k = _bundle_30(tmp_path)
    (k / "fragments" / "index.md").unlink()
    (k / _FRAGMENT).write_text("Plain notes.\n", encoding="utf-8")
    rep, _, _ = lint(k)
    assert ("ERROR", "NO_FRONTMATTER") in _codes(rep) and rep.notices == []


def test_unparsable_frontmatter_counts_as_okf_and_keeps_bad_yaml(tmp_path):
    k = _bundle_30(tmp_path)
    _write(k, "base/notes/a.md", "---\nbad: [\n---\n\nText.\n")
    rep, _, _ = lint(k)
    assert ("ERROR", "BAD_YAML") in _codes(rep, "base/notes/a.md") and rep.notices == []


def test_okfignore_comment_lines_are_not_patterns():
    from okf_common import OkfIgnore

    ign = OkfIgnore.parse("#drafts.md\n# notes/\n\\#kept.md\n")
    assert len(ign.rules) == 1
    assert not ign.match("#drafts.md", False) and not ign.match("notes", True)
    assert ign.match("#kept.md", False)


def test_every_okf_profile_code_names_the_okf_profile_layer(tmp_path):
    """Two bundles that raise every code of OKF_PROFILE_CODES: each one, and only those, is layer okf-profile."""
    (tmp_path / "a").mkdir()
    a = _bundle_30(tmp_path / "a")
    index = a / "index.md"
    index.write_text(index.read_text(encoding="utf-8").replace('okf_version: "0.2"\n', ""), encoding="utf-8")
    (a / "log.md").unlink()
    (a / "project.md").write_text("---\ntype: Term\ntitle: P\ndescription: P.\n" + _GEN + "---\n\nText.\n",
                                  encoding="utf-8")
    for rel in ("base/Bad_Name.md", "base/p2.md"):
        _write(a, rel, "---\ntype: Project\ntitle: P\ndescription: P.\n" + _GEN + "---\n\nText.\n")
    _write(a, "base/c2.md", _CONFLICT_LOG)
    _write(a, "loose.md", "---\ntype: Term\ntitle: L\ndescription: L.\n" + _GEN + "---\n\nText.\n")
    _write(a, "base/nogen.md", "---\ntype: Term\ntitle: N\ndescription: N.\n---\n\nText.\n")
    (tmp_path / "b").mkdir()
    b = _bundle_30(tmp_path / "b")
    (b / "index.md").unlink()
    (b / "project.md").unlink()
    (tmp_path / "c").mkdir()
    c = _audit_bundle(tmp_path / "c")
    items = lint(a)[0].items + lint(b, version="0.1")[0].items + lint(c)[0].items
    emitted = {"NAME_KEBAB", "NO_OKF_VERSION", "PROFILE_OKF_VERSION", "PROFILE_NO_INDEX", "PROFILE_NO_LOG",
               "PROFILE_NO_PROJECT", "PROFILE_PROJECT_TYPE", "PROFILE_NO_GENERATED", "PROFILE_NO_TIMESTAMP",
               "PROFILE_OUTSIDE_LAYER", "PROFILE_MANY_PROJECTS", "PROFILE_MANY_CONFLICT_LOGS",
               "FRAGMENT_UNCITED", "SECTION_EMPTY", "VERIFIED_STALE"}
    assert emitted <= {i["code"] for i in items} and OKF_PROFILE_CODES == emitted
    assert {i["code"] for i in items if i["layer"] == "okf-profile"} == emitted
    assert all(i["layer"] == "okf-profile" for i in items if i["code"] in emitted)


def test_an_unsupported_okf_version_says_when_the_version_is_forced_and_mixed_versions_names_it(tmp_path):
    k = _bundle_30(tmp_path)
    index = k / "index.md"
    index.write_text(index.read_text(encoding="utf-8").replace('okf_version: "0.2"', 'okf_version: "0.3"'),
                     encoding="utf-8")
    [f] = lint(k, version="0.2")[0].items
    assert f["message"].endswith("; forced version: 0.2 (--okf-version)") and "inferred" not in f["message"]
    _write(k, "base/t.md", "---\ntype: Term\ntitle: T\ndescription: T.\ntimestamp: 2026-10-31T18:00:00Z\n---\n\nT.\n")
    [m] = [i["message"] for i in lint(k)[0].items if i["code"] == "MIXED_VERSIONS"]
    assert m == "concepts mix 0.1 and 0.2 forms and okf_version '0.3' is not supported: bundle half migrated (okf-migrate)"
    index.write_text(index.read_text(encoding="utf-8").replace('okf_version: "0.3"\n', ""), encoding="utf-8")
    [m] = [i["message"] for i in lint(k)[0].items if i["code"] == "MIXED_VERSIONS"]
    assert m == "concepts mix 0.1 and 0.2 forms and okf_version is missing: bundle half migrated (okf-migrate)"


# --------------------------------------------------------------------------
# The mechanical audit checks and the --json metrics (ticket A2)
# --------------------------------------------------------------------------
_TERM = "base/domain/refund.md"
_MEETING_LINK = "/fragments/2026-10-31-meeting.md"


def _term(body: str = "# Definition\n\nA refund.\n", fields: str = "", gen: str = _GEN, t: str = "Term") -> str:
    return f"---\ntype: {t}\ntitle: Refund\ndescription: A refund.\nstatus: draft\n" + fields + gen + "---\n\n" + body


def _with_term(k: Path, text: str, rel: str = _TERM) -> Path:
    _write(k, rel, text)
    _list_in_indexes(k, rel)
    return k


def _distill(k: Path) -> Path:
    f = k / _FRAGMENT
    f.write_text(f.read_text(encoding="utf-8").replace("distillation_status: pending", "distillation_status: distilled"),
                 encoding="utf-8")
    return k


def _distilled_bundle(tmp_path) -> Path:
    """A 3.0 bundle whose fragment is distilled, with one Term under base/."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    return _with_term(_distill(_bundle_30(tmp_path)), _term())


def _audit_bundle(tmp_path) -> Path:
    """A 3.0 bundle raising each okf-profile audit code once: an empty template section and a stale human
    verification on a Term, and a distilled fragment no concept cites."""
    k = _distilled_bundle(tmp_path)
    _write(k, _TERM, _term("# Definition\n\n{{One unambiguous sentence.}}\n",
                           "verified: { by: human:alice, at: 2026-10-30T18:00:00Z }\n"))
    return k


def _audit(rep: Report, code: str) -> list[tuple[str, str]]:
    return [(i["path"], i["message"]) for i in rep.items if i["code"] == code]


def test_the_audit_bundle_raises_each_audit_code_once_and_its_clean_twin_none(tmp_path):
    rep = lint(_audit_bundle(tmp_path / "a"))[0]
    assert sorted((i["level"], i["code"], i["path"], i["layer"]) for i in rep.items) == [
        ("WARN", "FRAGMENT_UNCITED", _FRAGMENT, "okf-profile"), ("WARN", "SECTION_EMPTY", _TERM, "okf-profile"),
        ("WARN", "VERIFIED_STALE", _TERM, "okf-profile")]
    k = _distilled_bundle(tmp_path / "b")
    _write(k, _TERM, _term(f"# Definition\n\nA refund, see [the meeting]({_MEETING_LINK}).\n",
                           "verified: { by: human:alice, at: 2026-10-31T18:00:00Z }\n"))
    assert lint(k)[0].items == []
    assert lint(_audit_bundle(tmp_path / "c"), profile=False)[0].items == []  # okf-profile codes need the profile


# FRAGMENT_UNCITED ---------------------------------------------------------------------------------------------------
def test_fragment_uncited_fires_on_a_distilled_fragment_no_concept_cites(tmp_path):
    [(path, msg)] = _audit(lint(_distilled_bundle(tmp_path))[0], "FRAGMENT_UNCITED")
    assert path == _FRAGMENT and "no concept cites it" in msg


def test_fragment_uncited_does_not_fire_on_a_pending_fragment(tmp_path):
    assert lint(_with_term(_bundle_30(tmp_path), _term()))[0].items == []


def test_fragment_uncited_counts_links_sources_asked_in_the_domain_profile_and_the_conflict_log(tmp_path):
    question = ("---\ntype: Open Question\ntitle: Q\ndescription: Q.\nstatus: draft\n" + _QUESTION_FIELDS + _GEN
                + "---\n\n# Question\n\nWho?\n")
    cases = {
        "body link": (_TERM, _term(f"# Definition\n\nSee [it]({_MEETING_LINK}).\n")),
        "relative link": (_TERM, _term("# Definition\n\nSee [it](../../fragments/2026-10-31-meeting.md).\n")),
        "sources entry": (_TERM, _term(fields=f"sources: [{{ resource: {_MEETING_LINK} }}]\n")),
        "asked_in": (_QUESTION, question),
        "base/profile.md": ("base/profile.md", _domain_profile("types: {}\n").replace(
            "Text.\n", f"Text, from [the meeting]({_MEETING_LINK}).\n")),
        "Conflict Log": ("conflict-log.md", _CONFLICT_LOG + f"| C-1 | [M]({_MEETING_LINK}) | D | fact | | open | |\n"),
    }
    for n, (name, (rel, text)) in enumerate(cases.items()):
        k = _distilled_bundle(tmp_path / str(n))
        _write(k, rel, text)
        if rel.startswith("base/"):
            _list_in_indexes(k, rel)
        rep = lint(k)[0]
        assert _audit(rep, "FRAGMENT_UNCITED") == [], name
        assert rep.items == [], (name, rep.items)


def test_fragment_uncited_ignores_links_from_the_log_the_indexes_and_other_fragments(tmp_path):
    k = _distilled_bundle(tmp_path)
    _write(k, "log.md", f"# Bundle history\n\n## 2026-10-31\n* **Creation**: [M]({_MEETING_LINK}).\n")
    other = "fragments/2026-11-01-other.md"
    _write(k, other, "---\ntype: Knowledge Fragment\ntitle: O\ndescription: O.\nstatus: draft\n" + _FRAGMENT_FIELDS
           + _GEN + f"---\n\n# Record\n\nAfter [the meeting]({_MEETING_LINK}).\n")
    _list_in_indexes(k, other)
    assert [p for p, _ in _audit(lint(k)[0], "FRAGMENT_UNCITED")] == [_FRAGMENT]  # fragments/index.md links it too


def test_fragment_uncited_reads_the_type_and_value_aliases_of_the_domain_profile(tmp_path):
    keys = ("aliases:\n  types: { Fragmento: Knowledge Fragment }\n"
            "  values: [{ from: { ingerido: true }, to: { distillation_status: distilled } },\n"
            "           { from: { ingerido: false }, to: { distillation_status: pending } }]\n")
    fields = _FRAGMENT_FIELDS.replace("distillation_status: pending\n", "ingerido: true\n")
    rep = lint(_profiled(tmp_path / "d", keys, _concept("Fragmento", fields)))[0]
    assert [(i["code"], i["layer"]) for i in rep.items] == [("FRAGMENT_UNCITED", "okf-profile")]
    pending = fields.replace("ingerido: true", "ingerido: false")
    assert lint(_profiled(tmp_path / "p", keys, _concept("Fragmento", pending)))[0].items == []


# SECTION_EMPTY ------------------------------------------------------------------------------------------------------
def _templates_dir() -> Path:
    import pytest

    tdir = Path(__file__).resolve().parent.parent / "templates"
    if not tdir.is_dir():
        pytest.skip("okf-standard/templates not beside this script")
    return tdir


def test_template_sections_name_the_headings_of_each_shipped_template():
    from okf_common import body_sections, parse_yaml, split_frontmatter

    tdir = _templates_dir()
    for t, (name, heads) in TEMPLATE_SECTIONS.items():
        fm, body = split_frontmatter((tdir / name).read_text(encoding="utf-8"))
        assert str(parse_yaml(fm.replace("{{", "").replace("}}", "")).get("type")) == t, name
        assert tuple(s.heading for s in body_sections(body.split("\n"))) == heads, name


def test_section_empty_fires_on_each_kind_of_placeholder_and_names_the_line(tmp_path):
    bodies = {
        "nothing": "# Definition\n\n",
        "a {{...}} line": "# Definition\n\n{{One unambiguous sentence.}}\n",
        "an HTML comment": "# Definition\n\n<!-- what it means\n     here -->\n",
        "a ... item": "# Definition\n\n- ...\n2. ...\n",
        "a ': ...' item": "# Definition\n\n- Meaning: ...\n1. Check: ...\n",
        "the next heading at once": "# Definition\n# Synonyms and related terms\n\n- Synonyms: none.\n",
        "an empty subsection": "# Definition\n\n## In payments\n\n- ...\n",
    }
    for n, (name, body) in enumerate(bodies.items()):
        k = _with_term(_bundle_30(_mkdir(tmp_path / str(n))), _term(body))
        found = [i for i in lint(k)[0].items if i["code"] == "SECTION_EMPTY"]
        assert [(i["path"], i["level"], i["layer"], i["line"]) for i in found] == [(_TERM, "WARN", "okf-profile", 9)], name
        assert "'# Definition'" in found[0]["message"] and "term.md" in found[0]["message"], name


def test_section_empty_does_not_fire_on_content_links_header_rows_filled_subsections_or_other_headings(tmp_path):
    bodies = {
        "text": "# Definition\n\nA refund.\n",
        "a link": "# Definition\n\n* [Refund policy](/base/domain/refund.md)\n",
        "a table header": "# Definition\n\n| Field | Value |\n|---|---|\n",
        "a table header and empty rows": "# Definition\n\n| Field | Value |\n|---|---|\n| Owner | |\n",
        "a filled row": "# Definition\n\n| Field | Value |\n|---|---|\n| Owner | human:alice |\n",
        "a filled subsection": "# Definition\n\n## In payments\n\nA refund.\n",
        "code": "# Definition\n\n```text\n...\n```\n",
        "a heading no template has": "# Definition\n\nA refund.\n\n# Notes\n\n{{later}}\n",
    }
    for n, (name, body) in enumerate(bodies.items()):
        k = _with_term(_bundle_30(_mkdir(tmp_path / str(n))), _term(body))
        assert lint(k)[0].items == [], name


def test_section_empty_reads_project_md_and_a_local_type_as_the_type_it_extends(tmp_path):
    k = _bundle_30(_mkdir(tmp_path / "p"))
    _write(k, "project.md", "---\ntype: Project\ntitle: P\ndescription: P.\n" + _GEN
           + "---\n\n# Purpose\n\nP.\n\n# Scope\n\n- In scope: ...\n- Out of scope: ...\n")
    assert [(i["code"], i["path"], i["line"]) for i in lint(k)[0].items] == [("SECTION_EMPTY", "project.md", 12)]
    keys = ("types:\n  Payment Term:\n    extends: Term\n  Pago:\n    extends: Payment Term\n"
            "aliases:\n  types: { Glosa: Pago }\n")
    for n, t in enumerate(("Payment Term", "Pago", "Glosa")):
        k = _profiled(tmp_path / str(n), keys, extra={_TERM: _term("# Definition\n\n{{later}}\n", t=t)})
        assert [(i["code"], i["path"]) for i in lint(k)[0].items] == [("SECTION_EMPTY", _TERM)], t
        k = _profiled(tmp_path / f"{n}-filled", keys, extra={_TERM: _term(t=t)})
        assert lint(k)[0].items == [], t


def test_each_concept_template_left_unfilled_fires_section_empty(tmp_path):
    """Each template's sections, as okf-capture copies them before filling them in, hold only placeholder text but
    for the tables, code and fixed text the template writes as content (listed here)."""
    from okf_common import split_frontmatter

    content = {"adr.md": {"# Alternatives considered"}, "api.md": {"# Main operations", "# Examples"},
               "architecture-view.md": {"# View", "# Elements"}, "computation.md": {"# Computation"},
               "conflict-log.md": {"# How it is used", "# Conflicts"}, "fragment.md": {"# Distillation"},
               "project.md": {"# Team and ownership", "# Key links", "# Knowledge map"},
               "runbook.md": {"# Escalation", "# Post-incident"},
               "system.md": {"# Interfaces", "# Relevant configuration"}, "table.md": {"# Schema", "# Examples"}}
    tdir = _templates_dir()
    for t, (name, heads) in TEMPLATE_SECTIONS.items():
        text = (tdir / name).read_text(encoding="utf-8")
        (tmp_path / name).write_text(text, encoding="utf-8")
        doc = Doc(tmp_path / name, name, {"type": t}, split_frontmatter(text)[1])
        rep = Report()
        check_section_empty(doc, t, rep)
        fired = {i["message"].split("'")[1] for i in rep.items}
        assert fired == set(heads) - content.get(name, set()), name


def _mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# VERIFIED_STALE -----------------------------------------------------------------------------------------------------
def _verified(tmp_path, verified: str, gen: str = _GEN) -> list[tuple[str, str]]:
    k = _with_term(_bundle_30(_mkdir(tmp_path)), _term(fields=verified, gen=gen))
    return _audit(lint(k)[0], "VERIFIED_STALE")


def test_verified_stale_fires_when_generated_at_is_later_than_the_human_verification(tmp_path):
    [(path, msg)] = _verified(tmp_path, "verified: { by: human:alice, at: 2026-10-30T18:00:00Z }\n")
    assert path == _TERM and "2026-10-31T18:00:00+00:00" in msg and "2026-10-30T18:00:00+00:00" in msg


def test_verified_stale_does_not_fire_when_verified_at_or_after_the_edit(tmp_path):
    for n, at in enumerate(("2026-10-31T18:00:00Z", "2026-11-01T09:00:00Z")):
        assert _verified(tmp_path / str(n), f"verified: {{ by: human:alice, at: {at} }}\n") == [], at


def test_verified_stale_takes_the_latest_human_entry_of_a_list_and_ignores_machines_and_processes(tmp_path):
    latest_last = ("verified:\n  - { by: human:alice, at: 2026-10-01T00:00:00Z }\n"
                   "  - { by: human:bob, at: 2026-11-01T00:00:00Z }\n")
    latest_first = ("verified:\n  - { by: human:bob, at: 2026-11-01T00:00:00Z }\n"
                    "  - { by: human:alice, at: 2026-10-01T00:00:00Z }\n")
    machines = ("verified:\n  - { by: process:ci, at: 2026-10-01T00:00:00Z }\n"
                "  - { by: okf-builder/claude-opus-5-5, at: 2026-10-01T00:00:00Z }\n")
    mixed = machines + "  - { by: human:alice, at: 2026-10-30T00:00:00Z }\n  - { by: process:ci, at: 2026-11-02T00:00:00Z }\n"
    assert _verified(tmp_path / "a", latest_last) == []
    assert _verified(tmp_path / "b", latest_first) == []
    assert _verified(tmp_path / "c", machines) == []
    assert len(_verified(tmp_path / "d", mixed)) == 1  # the later process entry does not count


def test_verified_stale_skips_a_v01_concept(tmp_path):
    k = _with_term(_bundle_30(_mkdir(tmp_path)), _term(fields="timestamp: 2026-10-31T18:00:00Z\n"
                   "verified: { by: human:alice, at: 2026-10-30T18:00:00Z }\n", gen=""))
    assert _audit(lint(k, version="0.1")[0], "VERIFIED_STALE") == []


# SECRET_IN_BUNDLE ---------------------------------------------------------------------------------------------------
# Every fake value is assembled at run time, so no scanner reads a credential in this file.
_FAKE_SK = "sk" + "-" + "FAKEfake0123456789abcdEF"
_FAKES = {
    "JWT": "eyJ" + "hbGciOiJIUzI1NiJ9" + ".eyJ" + "zdWIiOiJmYWtlIn0" + "." + "c2lnbmF0dXJlZmFrZQ123",
    "Bearer": "Authorization: Bearer " + "abcDEF0123456789" + "xyz",
    "Authorization": "Authorization: " + "Zm9vOmJhcjEyMzQ1Njc4" + "OQ",
    "ghp": "gh" + "p_" + "A1b2C3d4" * 4 + "E5f6",
    "gho": "gh" + "o_" + "A1b2C3d4" * 4 + "E5f6",
    "ghs": "gh" + "s_" + "A1b2C3d4" * 4 + "E5f6",
    "github_pat": "github" + "_pat_" + "11ABCDEFG0" + "abcdefghijklmnopqrstuv",
    "glpat": "gl" + "pat-" + "Ab12Cd34Ef56Gh78Ij90",
    "AKIA": "AK" + "IA" + "ABCDEFGH12345678",
    "sk-": _FAKE_SK,
    "xox": "xo" + "xb-" + "1234567890-abcdefABCDEF",
    "AIza": "AI" + "za" + "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q",
    "key=": "api_key=" + "Q9x7Lm2Pz4Rt8Wv6" + "Yb",
    "key: quoted": 'client_secret: "' + "q9X7lm2PZ4rt8WV6" + 'yb"',
    "password:": "password: " + "Tr0ub4dor" + "Xyz9876543",
}
_NOT_SECRETS = (
    "* [ADR-0012](/base/decisions/ADR-0012-adopt-kafka-for-payment-events-2026.md) - The decision.",
    "decision_key: ADR-0012-adopt-kafka-for-payment-events-2026",
    "commit: " + "4f3c2b1a0e9d8c7b6a5f" * 2,  # a 40-hex hash
    "resolved_key: " + "4f3c2b1a0e9d8c7b6a5f" * 2,
    "Keys: `types`",
    "primary_key: id",
    "# key: { reason, level }",
    "api_key: {{api_key}}",
    "token: `$GITHUB_TOKEN`",
    "secret_path: /etc/okf/secrets/payments-2026.json",
    "password: [redacted, ask the team]",
    "access_token: $ACCESS_TOKEN_2026_Q4",
    'curl -H "Authorization: Bearer $TOKEN" https://.../v1/...',
    "The bearer of this note owns it.",
    "key: payments refund window 2026",
)


def test_secret_in_bundle_matches_each_pattern_and_names_no_value():
    for name, value in _FAKES.items():
        assert leak_kind(f"Some text {value} here") or leak_kind(value), name


def test_secret_in_bundle_does_not_fire_on_names_hashes_paths_and_placeholders(tmp_path):
    for line in _NOT_SECRETS:
        assert leak_kind(line) is None, line
    k = _with_term(_bundle_30(_mkdir(tmp_path)), _term("# Definition\n\n" + "\n".join(_NOT_SECRETS) + "\n"))
    assert _audit(lint(k)[0], "SECRET_IN_BUNDLE") == []


def test_a_fake_secret_fails_lint_with_its_file_and_line_and_is_never_printed(tmp_path, capsys):
    k = _with_term(_bundle_30(_mkdir(tmp_path)), _term(fields=f"api_token: {_FAKE_SK}\n",
                                                       body=f"# Definition\n\nA refund.\n\nCall it with {_FAKE_SK}.\n"))
    rep = lint(k)[0]
    found = [i for i in rep.items if i["code"] == "SECRET_IN_BUNDLE"]
    assert [(i["level"], i["path"], i["layer"], i["line"]) for i in found] == [
        ("ERROR", _TERM, "spec", 6), ("ERROR", _TERM, "spec", 14)]
    assert main([str(k)]) == 1
    text = capsys.readouterr().out
    assert main([str(k), "--json"]) == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "SECRET_IN_BUNDLE" in text and {i["code"] for i in data["findings"]} == {"SECRET_IN_BUNDLE"}
    assert _FAKE_SK not in text and _FAKE_SK not in out and "FAKEfake0123456789" not in text + out
    assert lint(k, profile=False)[0].errors == found  # a spec check: it runs without the profile too


def test_secret_in_bundle_reads_fragments_and_frontmatter_and_okfignore_excludes_a_file(tmp_path):
    k = _bundle_30(_mkdir(tmp_path))
    f = k / _FRAGMENT
    f.write_text(f.read_text(encoding="utf-8") + f"\nThey pasted {_FAKES['ghp']} in the chat.\n", encoding="utf-8")
    assert [(i["code"], i["path"]) for i in lint(k)[0].items] == [("SECRET_IN_BUNDLE", _FRAGMENT)]
    _write(k, ".okfignore", "fragments/2026-10-31-meeting.md\n")
    assert [i for i in lint(k)[0].items if i["code"] == "SECRET_IN_BUNDLE"] == []


# --json metrics -----------------------------------------------------------------------------------------------------
def _metrics(capsys, k: Path) -> dict:
    main([str(k), "--json"])
    return json.loads(capsys.readouterr().out)["metrics"]


def test_json_metrics_are_always_present_and_count_findings_trust_and_fragments(tmp_path, capsys):
    k = _bundle_30(_mkdir(tmp_path / "clean"))
    m = _metrics(capsys, k)
    assert m == {"count_per_code": {}, "concepts_by_trust": {"unverified": 0, "machine-confirmed": 0, "human-reviewed": 0},
                 "fragments": {"by_status": {"pending": 1}, "oldest_pending_days": m["fragments"]["oldest_pending_days"]}}
    assert m["fragments"]["oldest_pending_days"] == (datetime.now(timezone.utc).date() - date(2026, 10, 31)).days
    k = _audit_bundle(tmp_path / "audit")
    _with_term(k, _term(fields="verified: { by: process:ci, at: 2026-11-01T00:00:00Z }\n"), "base/domain/b.md")
    _with_term(k, _term(), "base/domain/c.md")
    m = _metrics(capsys, k)
    assert m["count_per_code"] == {"FRAGMENT_UNCITED": 1, "SECTION_EMPTY": 1, "VERIFIED_STALE": 1}
    assert m["concepts_by_trust"] == {"unverified": 1, "machine-confirmed": 1, "human-reviewed": 1}
    assert m["fragments"] == {"by_status": {"distilled": 1}, "oldest_pending_days": None}
    assert "stale_after_cluster" not in m


def test_json_metrics_oldest_pending_counts_from_occurred_at_else_generated_at(tmp_path, capsys):
    k = _bundle_30(_mkdir(tmp_path))
    f = k / _FRAGMENT
    today = datetime.now(timezone.utc).date()
    f.write_text(f.read_text(encoding="utf-8").replace("occurred_at: 2026-10-31\n", ""), encoding="utf-8")
    assert _metrics(capsys, k)["fragments"]["oldest_pending_days"] == (today - date(2026, 10, 31)).days  # generated.at
    f.write_text(f.read_text(encoding="utf-8").replace(_GEN, ""), encoding="utf-8")
    assert _metrics(capsys, k)["fragments"]["oldest_pending_days"] is None  # neither: left out of the age
    f.write_text(f.read_text(encoding="utf-8").replace("status: draft\n", "status: draft\noccurred_at: 2026-09-30\n"),
                 encoding="utf-8")
    assert _metrics(capsys, k)["fragments"]["oldest_pending_days"] == (today - date(2026, 9, 30)).days


def test_json_metrics_stale_after_cluster_lists_each_week_holding_more_than_a_quarter(tmp_path, capsys):
    dates = ["2027-01-04", "2027-01-05", "2027-03-01", "2027-03-02", "2027-06-01", "2027-09-01", "2027-12-01"]
    k = _bundle_30(_mkdir(tmp_path / "a"))
    for n, d in enumerate(dates):
        _with_term(k, _term(fields=f"stale_after: {d}T00:00:00Z\n"), f"base/domain/t{n}.md")
    assert _metrics(capsys, k)["stale_after_cluster"] == [{"week": "2027-W01", "count": 2},
                                                           {"week": "2027-W09", "count": 2}]
    k = _bundle_30(_mkdir(tmp_path / "c"))
    for n, d in enumerate(dates[:3]):  # fewer than 4 concepts with stale_after
        _with_term(k, _term(fields=f"stale_after: {d}T00:00:00Z\n"), f"base/domain/t{n}.md")
    assert "stale_after_cluster" not in _metrics(capsys, k)
    k = _bundle_30(_mkdir(tmp_path / "d"))  # 1 of 4 in each week: none holds more than a quarter
    for n, d in enumerate(("2027-01-04", "2027-03-01", "2027-06-01", "2027-09-01")):
        _with_term(k, _term(fields=f"stale_after: {d}T00:00:00Z\n"), f"base/domain/t{n}.md")
    assert "stale_after_cluster" not in _metrics(capsys, k)


def test_json_metrics_count_reported_findings_only_not_skipped_ones(tmp_path, capsys):
    k = _audit_bundle(tmp_path)
    index = k / "index.md"
    index.write_text(index.read_text(encoding="utf-8").replace(PROFILE_30, "acme/knowledge-1.0"), encoding="utf-8")
    main([str(k), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert {i["code"] for i in data["skipped"]} >= {"FRAGMENT_UNCITED", "SECTION_EMPTY", "VERIFIED_STALE"}
    assert data["metrics"]["count_per_code"] == dict(Counter(i["code"] for i in data["findings"]))
    assert not set(data["metrics"]["count_per_code"]) & {"FRAGMENT_UNCITED", "SECTION_EMPTY", "VERIFIED_STALE"}


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
