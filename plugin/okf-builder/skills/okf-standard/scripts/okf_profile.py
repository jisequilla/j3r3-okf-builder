#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_profile.py — Load and compose the Domain Profile of a knowledge/3.0 bundle (standard §4.1, ADR-0026).

Usage:
    uv run okf_profile.py [path/to/bundle] [--json]      # the structural findings and the sources in force
    uv run okf_lint.py <bundle> --profiles [<path>]      # what is in force at a path, and which source declared it
    uv run okf_profile.py --check-builtin <OKF-STANDARD.md>   # the built-in profile against the §4 type table

Layers merge from general to specific: the built-in Domain Profile
(<skills>/okf-standard/profiles/knowledge-3.0.md, or the copy an exported
package inlines in BUILTIN_TEXT), each profile `extends` names
in order (depth first), the bundle's own base/profile.md, then `families`, then
`by_type`. References are read locally only: a bundle path (`/base/...`) from
the bundle's working tree, `<repo-path>@<commit>` with `git show` from the
repository that holds the bundle. A URL is never read. Validator commands are
never run here.

Structural findings: PROFILE_INVALID, PROFILE_DUPLICATE_ID, PROFILE_REDEFINED,
PROFILE_UNREADABLE, PROFILE_MISPLACED. Concepts are not validated here.
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import PROFILE_30, Doc, declared_profile, find_bundle, parse_yaml, split_frontmatter  # noqa: E402

FIELD_TYPES = ("string", "integer", "boolean", "date", "datetime", "date_or_datetime", "actor", "list", "enum", "path")
LEVELS = ("error", "warn")
RANK = {"warn": 0, "error": 1}
PROFILE_KEYS = ("extends", "types", "families", "forbidden", "fixed", "by_type", "rules", "validator", "questions",
                "aliases")
TYPE_KEYS = {"extends", "description", "fields", "directory", "note"}
FIELD_KEYS = {"type", "of", "values", "required", "level", "code", "note"}
FAMILY_KEYS = {"types", "required", "fixed", "forbidden", "fields", "description", "note"}
BY_TYPE_KEYS = {"required", "fixed", "forbidden", "values", "fields"}
DOMAIN_PROFILE = "Domain Profile"
OWN_REL = "base/profile.md"
BUILTIN_LABEL = "<skills>/okf-standard/profiles/knowledge-3.0.md"
# scripts/ sits beside profiles/ in okf-standard. A copy without profiles/ reads BUILTIN_TEXT, the copy of that
# file an exported package inlines here (tools/export_m365.py), and without either falls back to the names of §4
BUILTIN_PATH = Path(__file__).resolve().parent.parent / "profiles" / "knowledge-3.0.md"
BUILTIN_TEXT: str | None = None
STANDARD_TYPE_NAMES = ("Project", "Architecture View", "Architecture Decision", "Term", "Glossary", "System", "API",
                       "Dataset", "Table", "Metric", "Attested Computation", "Runbook", "Playbook", "Policy",
                       "Reference", "Knowledge Fragment", "Open Question", "Conflict Log", DOMAIN_PROFILE, "Log")
URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")
FAMILY_RE = re.compile(r"^/base/(?:[^/\s]+/)+$")
IGNORED_20_NOTICE = ("Domain Profile {rel} ignored: profile knowledge/2.0 reads no Domain Profile; "
                     "run okf_migrate.py --profile knowledge/3.0")


# --------------------------------------------------------------------------
# Schema (§4.1 Keys): PROFILE_INVALID
# --------------------------------------------------------------------------
def _is_map(v: Any) -> bool:
    return isinstance(v, dict)


def _str_list(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def _level_ok(entry: dict, where: str, errs: list[str]) -> None:
    if "level" in entry and entry["level"] not in LEVELS:
        errs.append(f"{where}: level '{entry['level']}' is not error|warn")
    if "code" in entry and not (isinstance(entry["code"], str) and entry["code"].strip()):
        errs.append(f"{where}: code must be a non-empty string")


def _check_field(fid: str, d: Any, where: str, errs: list[str]) -> None:
    w = f"{where}.{fid}"
    if not _is_map(d):
        errs.append(f"{w}: a field is a map with 'type'")
        return
    extra = sorted(set(d) - FIELD_KEYS)
    if extra:
        errs.append(f"{w}: unknown key(s) {', '.join(extra)}")
    ft = d.get("type")
    if ft not in FIELD_TYPES:
        errs.append(f"{w}: field type '{ft}' is not one of {', '.join(FIELD_TYPES)}")
    if ft == "list" and d.get("of") not in tuple(t for t in FIELD_TYPES if t != "list"):
        errs.append(f"{w}: a list needs 'of', the field type of each item")
    if ft != "list" and "of" in d:
        errs.append(f"{w}: 'of' applies to a list only")
    if ft == "enum" and not (isinstance(d.get("values"), list) and d["values"]):
        errs.append(f"{w}: an enum needs a non-empty 'values'")
    if ft != "enum" and "values" in d:
        errs.append(f"{w}: 'values' applies to an enum only")
    req = d.get("required", False)
    if not (isinstance(req, bool) or _is_map(req)):
        errs.append(f"{w}: required is true, false or {{ level, code }}")
    if _is_map(req):
        extra = sorted(set(req) - {"level", "code"})
        if extra:
            errs.append(f"{w}.required: unknown key(s) {', '.join(extra)}")
        _level_ok(req, f"{w}.required", errs)
    _level_ok(d, w, errs)


def _check_required(v: Any, where: str, errs: list[str]) -> None:
    if v is None or _str_list(v):
        return
    if not _is_map(v):
        errs.append(f"{where}.required: a list of keys, or a map key → true | false | {{ level, code }}")
        return
    for k, r in v.items():
        if isinstance(r, bool):
            continue
        if not _is_map(r) or set(r) - {"level", "code"}:
            errs.append(f"{where}.required.{k}: true, false or {{ level, code }}")
            continue
        _level_ok(r, f"{where}.required.{k}", errs)


def _check_keyed(v: Any, where: str, need: str | None, errs: list[str]) -> None:
    """forbidden ({ reason, level, code }) or fixed ({ value, level, code })."""
    if v is None:
        return
    if not _is_map(v):
        errs.append(f"{where}: a map key → {{ {'value' if need else 'reason'}, level }}")
        return
    allowed = {"value", "level", "code", "reason", "note"} if need else {"reason", "level", "code", "note"}
    for k, e in v.items():
        if not _is_map(e):
            errs.append(f"{where}.{k}: a map {{ {'value' if need else 'reason'}, level }}")
            continue
        extra = sorted(set(e) - allowed)
        if extra:
            errs.append(f"{where}.{k}: unknown key(s) {', '.join(extra)}")
        if need and need not in e:
            errs.append(f"{where}.{k}: a fixed key needs its 'value'")
        _level_ok(e, f"{where}.{k}", errs)


def _check_fields_map(v: Any, where: str, errs: list[str]) -> None:
    if v is None:
        return
    if not _is_map(v):
        errs.append(f"{where}: a map field id → definition")
        return
    for fid, d in v.items():
        _check_field(str(fid), d, where, errs)


def validate_schema(fm: dict) -> list[str]:
    """Messages for every breach of the §4.1 schema in a Domain Profile's frontmatter."""
    errs: list[str] = []
    ext = fm.get("extends")
    if ext is not None and not _str_list(ext):
        errs.append("extends: a list of references (/base/... or <path>@<commit>)")
    types = fm.get("types")
    if types is not None:
        if not _is_map(types):
            errs.append("types: a map type id → definition")
        else:
            for tid, t in types.items():
                if t is None:
                    continue
                if not _is_map(t):
                    errs.append(f"types.{tid}: a map {{ extends, description, fields }}")
                    continue
                extra = sorted(set(t) - TYPE_KEYS)
                if extra:
                    errs.append(f"types.{tid}: unknown key(s) {', '.join(extra)}")
                if "extends" in t and not (isinstance(t["extends"], str) and t["extends"].strip()):
                    errs.append(f"types.{tid}.extends: the id of one type")
                _check_fields_map(t.get("fields"), f"types.{tid}.fields", errs)
    fams = fm.get("families")
    if fams is not None:
        if not _is_map(fams):
            errs.append("families: a map /base/<dir>/ → schema")
        else:
            for d, f in fams.items():
                w = f"families.{d}"
                if not FAMILY_RE.match(str(d)):
                    errs.append(f"{w}: a family is a directory under base/, written /base/<dir>/")
                if f is None:
                    continue
                if not _is_map(f):
                    errs.append(f"{w}: a map {{ types, required, fixed, forbidden }}")
                    continue
                extra = sorted(set(f) - FAMILY_KEYS)
                if extra:
                    errs.append(f"{w}: unknown key(s) {', '.join(extra)}")
                if "types" in f and not _str_list(f["types"]):
                    errs.append(f"{w}.types: a list of type ids")
                _check_required(f.get("required"), w, errs)
                _check_keyed(f.get("fixed"), f"{w}.fixed", "value", errs)
                _check_keyed(f.get("forbidden"), f"{w}.forbidden", None, errs)
                _check_fields_map(f.get("fields"), f"{w}.fields", errs)
    _check_keyed(fm.get("forbidden"), "forbidden", None, errs)
    _check_keyed(fm.get("fixed"), "fixed", "value", errs)
    bt = fm.get("by_type")
    if bt is not None:
        if not _is_map(bt):
            errs.append("by_type: a map type id → { required, fixed, forbidden, values }")
        else:
            for tid, e in bt.items():
                w = f"by_type.{tid}"
                if e is None:
                    continue
                if not _is_map(e):
                    errs.append(f"{w}: a map {{ required, fixed, forbidden, values }}")
                    continue
                extra = sorted(set(e) - BY_TYPE_KEYS)
                if extra:
                    errs.append(f"{w}: unknown key(s) {', '.join(extra)}")
                _check_required(e.get("required"), w, errs)
                _check_keyed(e.get("fixed"), f"{w}.fixed", "value", errs)
                _check_keyed(e.get("forbidden"), f"{w}.forbidden", None, errs)
                _check_fields_map(e.get("fields"), f"{w}.fields", errs)
                vals = e.get("values")
                if vals is not None and not (_is_map(vals) and all(isinstance(x, list) and x for x in vals.values())):
                    errs.append(f"{w}.values: a map field → non-empty list of values to add")
    rules = fm.get("rules")
    if rules is not None:
        if not isinstance(rules, list):
            errs.append("rules: a list of { name, when, require, level }")
        else:
            for n, r in enumerate(rules):
                w = f"rules[{n}]"
                if not _is_map(r):
                    errs.append(f"{w}: a map {{ name, when, require, level }}")
                    continue
                if not (isinstance(r.get("name"), str) and r["name"].strip()):
                    errs.append(f"{w}: a rule needs a 'name'")
                if not (_is_map(r.get("when")) and r["when"]):
                    errs.append(f"{w}: a rule needs 'when', a map field → value")
                if not (_str_list(r.get("require")) and r["require"]):
                    errs.append(f"{w}: a rule needs 'require', a list of fields")
                extra = sorted(set(r) - {"name", "when", "require", "level", "code", "note"})
                if extra:
                    errs.append(f"{w}: unknown key(s) {', '.join(extra)}")
                _level_ok(r, w, errs)
    vals = fm.get("validator")
    if vals is not None:
        if not isinstance(vals, list):
            errs.append("validator: a list of { name, types, families, command }")
        else:
            for n, v in enumerate(vals):
                w = f"validator[{n}]"
                if not _is_map(v) or not (isinstance(v.get("name"), str) and v["name"].strip()):
                    errs.append(f"{w}: a validator needs a 'name'")
                    continue
                if not (isinstance(v.get("command"), str) and v["command"].strip()):
                    errs.append(f"{w}: a validator needs a 'command'")
                for k in ("types", "families"):
                    if k in v and not _str_list(v[k]):
                        errs.append(f"{w}.{k}: a list")
    qs = fm.get("questions")
    if qs is not None:
        if not isinstance(qs, list):
            errs.append("questions: a list of { question, field | concept }")
        else:
            for n, q in enumerate(qs):
                w = f"questions[{n}]"
                if not _is_map(q) or not isinstance(q.get("question"), str):
                    errs.append(f"{w}: a question needs 'question'")
                    continue
                if ("field" in q) == ("concept" in q):
                    errs.append(f"{w}: exactly one of 'field' (Type.field) or 'concept' (/base/...)")
                elif "field" in q and not re.match(r"^[^.]+\.[^.]+$", str(q["field"])):
                    errs.append(f"{w}.field: written Type.field")
                elif "concept" in q and not str(q["concept"]).startswith("/"):
                    errs.append(f"{w}.concept: a bundle path starting with /")
    al = fm.get("aliases")
    if al is not None:
        if not _is_map(al) or set(al) - {"types", "fields", "values"}:
            errs.append("aliases: a map with types, fields and values")
        else:
            for k in ("types", "fields"):
                m = al.get(k)
                if m is not None and not (_is_map(m) and all(isinstance(x, str) and x for x in m.values())):
                    errs.append(f"aliases.{k}: a map local name → declared name")
            vv = al.get("values")
            if vv is not None and not (isinstance(vv, list) and all(
                    _is_map(x) and _is_map(x.get("from")) and x["from"] and _is_map(x.get("to")) and x["to"]
                    for x in vv)):
                errs.append("aliases.values: a list of { from: { field: value }, to: { field: value } }")
    return errs


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
@dataclass
class Layer:
    source: str  # how findings and --profiles name it
    data: dict


@dataclass
class Resolved:
    """The Domain Profile of a bundle, composed from its layers."""
    sources: list[str] = field(default_factory=list)
    types: dict = field(default_factory=dict)        # id → { extends, description, fields: {f: def}, source }
    forbidden: dict = field(default_factory=dict)    # key → { reason, level, code, source }
    fixed: dict = field(default_factory=dict)        # key → { value, level, code, source }
    families: dict = field(default_factory=dict)     # /base/dir/ → { types, required, fixed, forbidden, source }
    by_type: dict = field(default_factory=dict)      # type → { required, fixed, forbidden, values }
    rules: list = field(default_factory=list)
    validators: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    aliases: dict = field(default_factory=lambda: {"types": {}, "fields": {}, "values": []})
    findings: list = field(default_factory=list)
    has_own: bool = False                            # base/profile.md is in force (3.0, not deprecated)
    builtin_file: bool = False                       # the built-in layer came from its file or its inlined copy
    extended: set = field(default_factory=set)       # bundle rels of the working-tree profiles extends reaches

    def add(self, code: str, path: str, msg: str) -> None:
        self.findings.append({"level": "ERROR", "code": code, "path": path, "message": msg})


def _fm_of(text: str) -> tuple[dict | None, str | None]:
    raw, _ = split_frontmatter(text)
    if raw is None:
        return None, "no YAML frontmatter block"
    try:
        return parse_yaml(raw), None
    except Exception as e:  # noqa: BLE001
        return None, f"frontmatter cannot be parsed: {e}"


class _Reader:
    """Follows `extends` depth first; layers come out general to specific."""

    def __init__(self, bundle: Path, r: Resolved) -> None:
        self.bundle, self.r = bundle, r
        self.layers: list[Layer] = []
        self.visited: set = set()
        self._top: str | None | bool = False  # False: not asked yet

    # git, only for <path>@<commit>; never a network operation: --no-lazy-fetch stops a partial
    # clone from fetching a missing object from its promisor remote. Git older than 2.44 rejects
    # the option and every call fails, so an old git can never fall back to fetching.
    def _git(self, *args: str) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(["git", "--no-lazy-fetch", "-C", str(self.bundle), *args], capture_output=True,
                                  text=True, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})
        except OSError:
            return None

    def toplevel(self) -> str | None:
        if self._top is False:
            p = self._git("rev-parse", "--show-toplevel")
            self._top = p.stdout.strip() if p is not None and p.returncode == 0 else None
        return self._top

    def git_read(self, path: str, commit: str, where: str, ref: str) -> tuple[tuple | None, str | None]:
        p = self._git("version")
        if p is None or p.returncode != 0:
            self.r.add("PROFILE_UNREADABLE", where, f"extends '{ref}': reading a pinned profile needs git 2.44 or "
                       "later (git --no-lazy-fetch), so that lint never fetches over the network")
            return None, None
        top = self.toplevel()
        if top is None:
            self.r.add("PROFILE_UNREADABLE", where, f"extends '{ref}': the bundle is not inside a git repository")
            return None, None
        p = self._git("rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
        if p is None or p.returncode != 0:
            self.r.add("PROFILE_UNREADABLE", where, f"extends '{ref}': git cannot resolve commit {commit}")
            return None, None
        sha = p.stdout.strip()
        p = self._git("show", f"{sha}:{path}")
        if p is None or p.returncode != 0:
            listed = self._git("ls-tree", "--full-tree", "--name-only", sha, "--", path)
            if listed is not None and listed.returncode == 0 and listed.stdout.strip():
                self.r.add("PROFILE_UNREADABLE", where, f"extends '{ref}': {path} at commit {commit} is not in the "
                           "local object store (partial clone?); lint does not fetch it")
                return None, None
            self.r.add("PROFILE_UNREADABLE", where, f"extends '{ref}': {path} does not exist at commit {commit}")
            return None, None
        return ("git", path, sha), p.stdout

    def resolve(self, ref: str, where: str, commit: str | None) -> tuple[tuple | None, str | None, str | None, str | None]:
        """(node key, label, text, commit context) of a reference, or Nones after reporting why."""
        none = (None, None, None, None)
        if URL_RE.match(ref):
            self.r.add("PROFILE_UNREADABLE", where,
                       f"extends '{ref}': URLs are not read (lint reads references locally; URL support is not implemented)")
            return none
        if ref.startswith("/"):
            rel = posixpath.normpath(ref.lstrip("/"))
            if rel.startswith(".."):
                self.r.add("PROFILE_UNREADABLE", where, f"extends '{ref}': the path leaves the bundle")
                return none
            if commit is None:
                p = self.bundle / rel
                if not p.is_file():
                    self.r.add("PROFILE_UNREADABLE", where, f"extends '{ref}': {rel} does not exist in the bundle")
                    return none
                return ("wt", rel), rel, p.read_text(encoding="utf-8"), None
            # a bundle path inside a pinned profile stays at that profile's commit
            top = self.toplevel()
            in_repo = Path(self.bundle).resolve().relative_to(Path(top).resolve()).as_posix() if top else ""
            path = posixpath.join(in_repo, rel) if in_repo not in ("", ".") else rel
            key, text = self.git_read(path, commit, where, ref)
            return (key, f"{path}@{commit}", text, commit) if key else none
        if "@" in ref:
            path, c = ref.rsplit("@", 1)
            path = posixpath.normpath(path)
            if not COMMIT_RE.match(c) or not path or path.startswith(("..", "/")):
                self.r.add("PROFILE_INVALID", where,
                           f"extends '{ref}': a pinned reference is <repo-relative path>@<commit hash>")
                return none
            key, text = self.git_read(path, c, where, ref)
            return (key, ref, text, c) if key else none
        self.r.add("PROFILE_INVALID", where,
                   f"extends '{ref}': neither a bundle path (/base/...) nor <repo-relative path>@<commit>")
        return none

    def visit(self, key: tuple, label: str, fm: dict, commit: str | None, stack: list[tuple[tuple, str]]) -> None:
        self.visited.add(key)
        if key[0] == "wt":
            self.r.extended.add(key[1])
        if fm.get("type") != DOMAIN_PROFILE:
            self.r.add("PROFILE_INVALID", label, f"a profile in extends must have type: {DOMAIN_PROFILE}")
            return
        errs = validate_schema(fm)
        for e in errs:
            self.r.add("PROFILE_INVALID", label, e)
        if errs:
            return
        here = [*stack, (key, label)]
        for ref in fm.get("extends") or []:
            k, lab, text, c = self.resolve(ref, label, commit)
            if k is None:
                continue
            on_stack = [s for s, _ in here]
            if k in on_stack:
                cycle = [lb for _, lb in here[on_stack.index(k):]] + [lab]
                self.r.add("PROFILE_INVALID", label, f"extends cycle: {' → '.join(cycle)}")
                continue
            if k in self.visited:
                continue
            sub, err = _fm_of(text)
            if sub is None:
                self.visited.add(k)
                self.r.add("PROFILE_INVALID", lab, err)
                continue
            self.visit(k, lab, sub, c, here)
        self.layers.append(Layer(label, fm))


def builtin_text(builtin: Path | None = None) -> str | None:
    """The built-in Domain Profile: the given file; by default its file, else the inlined copy."""
    path = BUILTIN_PATH if builtin is None else builtin
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return BUILTIN_TEXT if builtin is None else None


def load_profile(bundle: Path, read_own: bool | None = None, builtin: Path | None = None) -> Resolved:
    """Compose the Domain Profile of a bundle. read_own defaults to: the bundle is knowledge/3.0."""
    r = Resolved()
    if read_own is None:
        read_own = declared_profile(bundle) == PROFILE_30
    text = builtin_text(builtin)
    layers: list[Layer] = []
    if text is not None:
        fm, err = _fm_of(text)
        errs = [err] if fm is None else validate_schema(fm)
        for e in errs:
            r.add("PROFILE_INVALID", BUILTIN_LABEL, e)
        if not errs:
            layers.append(Layer("built-in", fm))
            r.builtin_file = True
    if not r.builtin_file:
        layers.append(Layer("built-in", {"types": {n: {} for n in STANDARD_TYPE_NAMES}}))
    own = bundle / OWN_REL
    if read_own and own.is_file():
        fm, err = _fm_of(own.read_text(encoding="utf-8"))
        if fm is None:
            r.add("PROFILE_INVALID", OWN_REL, err)
        elif fm.get("type") != DOMAIN_PROFILE:
            r.add("PROFILE_INVALID", OWN_REL, f"base/profile.md must have type: {DOMAIN_PROFILE}")
        elif fm.get("status") != "deprecated":  # a deprecated profile: the bundle dropped it
            r.has_own = True
            reader = _Reader(bundle, r)
            reader.visit(("wt", OWN_REL), OWN_REL, fm, None, [])
            r.extended.discard(OWN_REL)
            layers += reader.layers
    _merge(r, layers)
    return r


# --------------------------------------------------------------------------
# Composition (§4.1 Composition): PROFILE_DUPLICATE_ID, PROFILE_REDEFINED
# --------------------------------------------------------------------------
def _req_map(v: Any) -> dict:
    """required as a list or a map → { key: {level, code} | {optional: True} }."""
    if v is None:
        return {}
    if isinstance(v, list):
        return {k: {"level": "error"} for k in v}
    out = {}
    for k, e in v.items():
        if e is False:
            out[k] = {"optional": True}
        elif e is True:
            out[k] = {"level": "error"}
        else:
            out[k] = {"level": e.get("level", "error"), **({"code": e["code"]} if "code" in e else {})}
    return out


def _lvl(e: dict) -> str:
    return e.get("level", "error")


def _raise_into(dst: dict, src: dict) -> None:
    """Combine requirements, fixed or forbidden keys: the highest level wins; on a tie the first one stays.
    A raised entry without a code keeps the code it raises, so lint reports it under the same code."""
    for k, e in src.items():
        if k not in dst or RANK[_lvl(e)] > RANK[_lvl(dst[k])]:
            kept = {"code": dst[k]["code"]} if k in dst and "code" in dst[k] and "code" not in e else {}
            dst[k] = {**kept, **e}


def ancestors(r: Resolved, t: str) -> list[str]:
    """The types t extends, nearest first; stops at an unknown type or a cycle."""
    out, seen = [], {t}
    cur = (r.types.get(t) or {}).get("extends")
    while cur and cur in r.types and cur not in seen:
        out.append(cur)
        seen.add(cur)
        cur = r.types[cur].get("extends")
    return out


def is_a(r: Resolved, t: str, base: str) -> bool:
    """t is base or a type that extends it."""
    return t == base or base in ancestors(r, t)


def _subtypes(r: Resolved, t: str) -> list[str]:
    return [x for x in r.types if x != t and t in ancestors(r, x)]


def type_in_force(r: Resolved, t: str) -> dict:
    """Fields, requirements, fixed and forbidden keys in force for type t, its ancestors' included."""
    chain = [*reversed(ancestors(r, t)), t]
    fields: dict = {}
    required: dict = {}
    for x in chain:
        for fid, d in ((r.types.get(x) or {}).get("fields") or {}).items():
            fields[fid] = {**d, "declared_by": x}
            if "values" in d:
                fields[fid]["values"] = [{"value": v, "source": d["source"]} for v in d["values"]]
            req = d.get("required")
            if req:
                req = req if isinstance(req, dict) else {}
                required[fid] = {"level": req.get("level", d.get("level", "error")),
                                 **({"code": req["code"]} if "code" in req else {}), "source": d["source"]}
    fixed = {k: dict(v) for k, v in r.fixed.items()}
    forbidden = {k: dict(v) for k, v in r.forbidden.items()}
    for x in chain:
        bt = r.by_type.get(x) or {}
        _raise_into(required, bt.get("required", {}))
        _raise_into(fixed, bt.get("fixed", {}))
        _raise_into(forbidden, bt.get("forbidden", {}))
        for fid, vals in bt.get("values", {}).items():
            if fid in fields and "values" in fields[fid]:
                have = {v["value"] for v in fields[fid]["values"]}
                fields[fid]["values"] += [v for v in vals if v["value"] not in have]
    return {"fields": fields, "required": required, "fixed": fixed, "forbidden": forbidden}


def _check_lowering(r: Resolved, where: str, src: str, entry: dict, req_in: dict, fixed_in: dict,
                    forb_in: dict, fields_in: dict) -> None:
    """PROFILE_REDEFINED for a by_type or family entry that changes or lowers what is in force."""
    for k, e in _req_map(entry.get("required")).items():
        cur = req_in.get(k)
        if cur and e.get("optional"):
            r.add("PROFILE_REDEFINED", src, f"{where}: makes '{k}' optional, required by {cur['source']}")
        elif cur and RANK[_lvl(e)] < RANK[_lvl(cur)]:
            r.add("PROFILE_REDEFINED", src, f"{where}: lowers '{k}' from {_lvl(cur)} (by {cur['source']}) to {_lvl(e)}")
    for k, e in (entry.get("fixed") or {}).items():
        cur = fixed_in.get(k)
        if cur and cur.get("value") != e.get("value"):
            r.add("PROFILE_REDEFINED", src,
                  f"{where}: fixes '{k}' to {e.get('value')!r}, fixed to {cur.get('value')!r} by {cur['source']}")
        elif cur and RANK[_lvl(e)] < RANK[_lvl(cur)]:
            r.add("PROFILE_REDEFINED", src, f"{where}: lowers fixed '{k}' from {_lvl(cur)} (by {cur['source']})")
    for k, e in (entry.get("forbidden") or {}).items():
        cur = forb_in.get(k)
        if cur and RANK[_lvl(e)] < RANK[_lvl(cur)]:
            r.add("PROFILE_REDEFINED", src, f"{where}: lowers forbidden '{k}' from {_lvl(cur)} (by {cur['source']})")
    for fid, new in (entry.get("fields") or {}).items():
        if fid in fields_in:
            r.add("PROFILE_REDEFINED", src, f"{where}: declares field '{fid}' again, declared by {fields_in[fid]['source']}"
                                            f"{_field_change(fields_in[fid], new or {})} (a field changes only through a "
                                            "local type, and never its type, values or level)")
        else:
            r.add("PROFILE_INVALID", src, f"{where}: adds field '{fid}'; a field is added only by a local type that extends")


def _field_change(old: dict, new: dict) -> str:
    """What a re-declared field changes: its type, the values it drops, its level."""
    parts = []
    if new.get("type") and new["type"] != old.get("type"):
        parts.append(f"changes its type from {old.get('type')} to {new['type']}")
    if "values" in new:
        gone = [str(v["value"]) for v in old.get("values") or [] if v["value"] not in (new["values"] or [])]
        if gone:
            parts.append(f"removes value(s) {', '.join(gone)}")
    if new.get("level") in RANK and RANK[new["level"]] < RANK[old.get("level", "error")]:
        parts.append(f"lowers its level from {old.get('level', 'error')} to {new['level']}")
    return (": " + "; ".join(parts)) if parts else ""


def _stamp(m: dict | None, src: str) -> dict:
    return {k: {**(v or {}), "source": src} for k, v in (m or {}).items()}


def _merge(r: Resolved, layers: list[Layer]) -> None:
    r.sources = [lay.source for lay in layers]
    # 1. own declarations, layer by layer: types, forbidden, fixed, rules, validators, questions, aliases
    for lay in layers:
        d, src = lay.data, lay.source
        for tid, t in (d.get("types") or {}).items():
            t = t or {}
            if tid in r.types:
                r.add("PROFILE_DUPLICATE_ID", src, f"type '{tid}' declared by {r.types[tid]['source']} and by {src}")
                continue
            r.types[tid] = {**{k: v for k, v in t.items() if k != "fields"},
                            "fields": _stamp(t.get("fields"), src), "source": src}
        for key, store in (("forbidden", r.forbidden), ("fixed", r.fixed)):
            for k, e in (d.get(key) or {}).items():
                cur = store.get(k)
                if cur and key == "fixed" and cur.get("value") != e.get("value"):
                    r.add("PROFILE_REDEFINED", src, f"fixes '{k}' to {e.get('value')!r}, fixed to {cur.get('value')!r} by {cur['source']}")
                    continue
                if cur and RANK[_lvl(e)] < RANK[_lvl(cur)]:
                    r.add("PROFILE_REDEFINED", src, f"lowers {key} '{k}' from {_lvl(cur)} (by {cur['source']}) to {_lvl(e)}")
                    continue
                store[k] = {**e, "source": src}
        names = {x["name"]: x["source"] for x in r.rules}
        for rule in d.get("rules") or []:
            if rule["name"] in names:
                r.add("PROFILE_DUPLICATE_ID", src, f"rule '{rule['name']}' declared by {names[rule['name']]} and by {src}")
                continue
            names[rule["name"]] = src
            r.rules.append({**rule, "source": src})
        r.validators += [{**v, "source": src} for v in d.get("validator") or []]
        r.questions += [{**q, "source": src} for q in d.get("questions") or []]
        al = d.get("aliases") or {}
        for kind in ("types", "fields"):
            for name, target in (al.get(kind) or {}).items():
                cur = r.aliases[kind].get(name)
                if cur:
                    r.add("PROFILE_DUPLICATE_ID", src, f"alias '{name}' declared by {cur['source']} and by {src}")
                    continue
                r.aliases[kind][name] = {"to": target, "source": src}
        seen = {json.dumps(v["from"], sort_keys=True, default=str): v["source"] for v in r.aliases["values"]}
        for v in al.get("values") or []:
            k = json.dumps(v["from"], sort_keys=True, default=str)
            if k in seen:
                r.add("PROFILE_DUPLICATE_ID", src, f"value alias {k} declared by {seen[k]} and by {src}")
                continue
            seen[k] = src
            r.aliases["values"].append({**v, "source": src})
    # the types each one extends; a local type re-declaring an inherited field
    for tid, t in r.types.items():
        ext = t.get("extends")
        if ext and ext not in r.types:
            r.add("PROFILE_INVALID", t["source"], f"type '{tid}' extends '{ext}', which no layer declares")
            continue
        if ext and (ext == tid or tid in ancestors(r, ext)):
            loop = [tid, ext, *ancestors(r, ext)]
            r.add("PROFILE_INVALID", t["source"], f"type '{tid}' extends itself: {' → '.join(loop[:loop.index(tid, 1) + 1])}")
            continue
        inherited = type_in_force(r, ext)["fields"] if ext else {}
        for fid in t["fields"]:
            if fid in inherited:
                r.add("PROFILE_REDEFINED", t["source"],
                      f"type '{tid}' declares field '{fid}' again, inherited from '{inherited[fid]['declared_by']}' "
                      f"({inherited[fid]['source']})")
    all_fields = {f: t["source"] for t in r.types.values() for f in t["fields"]}
    for name, a in r.aliases["types"].items():
        if name in r.types:
            r.add("PROFILE_DUPLICATE_ID", a["source"], f"alias '{name}' is named like a type declared by {r.types[name]['source']}")
        if a["to"] not in r.types:
            r.add("PROFILE_INVALID", a["source"], f"alias '{name}' stands for '{a['to']}', which no layer declares")
    for name, a in r.aliases["fields"].items():
        if name in all_fields:
            r.add("PROFILE_DUPLICATE_ID", a["source"], f"alias '{name}' is named like a field declared by {all_fields[name]}")
    # 2. by_type, a type before its subtypes (then layer order), so the order of declaration does not matter
    entries = [(lay.source, tid, e or {}) for lay in layers for tid, e in (lay.data.get("by_type") or {}).items()]
    entries.sort(key=lambda x: len(ancestors(r, x[1])))
    for src, tid, e in entries:
        cur = type_in_force(r, tid)
        where = f"by_type.{tid}"
        _check_lowering(r, where, src, e, cur["required"], cur["fixed"], cur["forbidden"], cur["fields"])
        for fid in (e.get("values") or {}):
            fd = cur["fields"].get(fid)
            if fd is None:
                r.add("PROFILE_INVALID", src, f"{where}.values: '{tid}' has no field '{fid}'")
            elif fd.get("type") != "enum":
                r.add("PROFILE_REDEFINED", src,
                      f"{where}.values: '{fid}' is a {fd.get('type')} ({fd['source']}); values turn it into an enum")
        slot = r.by_type.setdefault(tid, {"required": {}, "fixed": {}, "forbidden": {}, "values": {}})
        _raise_into(slot["required"], {k: {**q, "source": src} for k, q in _req_map(e.get("required")).items()
                                       if not q.get("optional")})
        _raise_into(slot["fixed"], _stamp(e.get("fixed"), src))
        _raise_into(slot["forbidden"], _stamp(e.get("forbidden"), src))
        for fid, vals in (e.get("values") or {}).items():
            fd = cur["fields"].get(fid)
            if fd is not None and fd.get("type") == "enum":
                slot["values"].setdefault(fid, [])
                slot["values"][fid] += [{"value": v, "source": src} for v in vals]
    # 3. families, enclosing before nested (then layer order). A family is narrower than the types it
    # covers (all of them when it names none), so it never loosens what they, their by_type or an
    # enclosing family require.
    fams: list[tuple[str, str, dict]] = []
    declared: dict = {}
    for lay in layers:
        for dr, f in (lay.data.get("families") or {}).items():
            if dr in declared:
                r.add("PROFILE_DUPLICATE_ID", lay.source, f"family '{dr}' declared by {declared[dr]} and by {lay.source}")
                continue
            declared[dr] = lay.source
            fams.append((lay.source, dr, f or {}))
    fams.sort(key=lambda x: x[1].count("/"))
    for src, dr, f in fams:
        req_in: dict = {}
        fixed_in, forb_in = {k: dict(v) for k, v in r.fixed.items()}, {k: dict(v) for k, v in r.forbidden.items()}
        for x in r.families.values():
            if dr.startswith(x["dir"]):
                _raise_into(req_in, x["required"])
                _raise_into(fixed_in, x["fixed"])
                _raise_into(forb_in, x["forbidden"])
        covered = list(r.types)
        if f.get("types"):
            covered = [t for t in r.types if t in f["types"] or any(a in f["types"] for a in ancestors(r, t))]
        fields_in: dict = {}
        for t in covered:
            ti = type_in_force(r, t)
            fields_in.update({k: v for k, v in ti["fields"].items() if k not in fields_in})
            _raise_into(req_in, ti["required"])
            _raise_into(fixed_in, ti["fixed"])
            _raise_into(forb_in, ti["forbidden"])
        _check_lowering(r, f"family {dr}", src, f, req_in, fixed_in, forb_in, fields_in)
        r.families[dr] = {"dir": dr, "types": f.get("types"),
                          "required": {k: {**e, "source": src} for k, e in _req_map(f.get("required")).items()
                                       if not e.get("optional")},
                          "fixed": _stamp(f.get("fixed"), src), "forbidden": _stamp(f.get("forbidden"), src),
                          "source": src}


# --------------------------------------------------------------------------
# Placement (§4.1 Where a Domain Profile applies): PROFILE_MISPLACED and the 2.0 notice
# --------------------------------------------------------------------------
def misplaced(docs: list[Doc], r: Resolved) -> list[dict]:
    """In a 3.0 bundle: a concept of type Domain Profile other than base/profile.md and the profiles extends reads."""
    out = []
    for d in docs:
        if d.is_reserved or not d.frontmatter or d.frontmatter.get("type") != DOMAIN_PROFILE:
            continue
        if d.rel == OWN_REL or d.rel in r.extended:
            continue
        out.append({"level": "ERROR", "code": "PROFILE_MISPLACED", "path": d.rel,
                    "message": f"a {DOMAIN_PROFILE} lives only at base/profile.md and in the profiles it reaches "
                               "through extends by bundle paths"})
    return out


def ignored_in_20(docs: list[Doc]) -> list[str]:
    """In a 2.0 bundle: the profile.md files and Domain Profile concepts that are ignored."""
    return [d.rel for d in docs if not d.is_reserved and
            (d.path.name == "profile.md" or (d.frontmatter or {}).get("type") == DOMAIN_PROFILE)]


# --------------------------------------------------------------------------
# What is in force at a path (okf_lint --profiles)
# --------------------------------------------------------------------------
def bundle_path(bundle: Path, arg: str | None) -> str:
    """A bundle path (/base/x/) from a bundle path or a filesystem path inside the bundle."""
    if not arg or arg == "/":
        return "/"
    p = Path(arg)
    cand = p if p.is_absolute() else Path.cwd() / p
    try:
        rel = cand.resolve().relative_to(bundle.resolve()).as_posix()
    except ValueError:  # not a filesystem path inside the bundle: a bundle path
        rel = arg.strip("/")
    if rel in ("", "."):
        return "/"
    return "/" + rel + ("" if rel.endswith(".md") else "/")


def in_force(r: Resolved, path: str = "/") -> dict:
    """Types allowed at a bundle path, each one's fields and requirements, rules and aliases, with sources."""
    d = path if path.endswith("/") else posixpath.dirname(path) + "/"
    fams = sorted((f for f in r.families.values() if d.startswith(f["dir"])), key=lambda f: f["dir"].count("/"))
    allowed = list(r.types)
    for f in fams:
        if f["types"]:
            ok = set()
            for t in f["types"]:
                ok |= {t, *_subtypes(r, t)}
            allowed = [t for t in allowed if t in ok]
    types = {}
    for t in allowed:
        fi = type_in_force(r, t)
        for f in fams:
            for key in ("required", "fixed", "forbidden"):
                _raise_into(fi[key], f[key])
        types[t] = {"source": r.types[t]["source"], "extends": r.types[t].get("extends"), **fi}
    return {"path": path, "sources": r.sources, "families": [{"dir": f["dir"], "types": f["types"], "source": f["source"]}
                                                             for f in fams],
            "types_allowed": allowed, "types": types,
            "rules": r.rules, "aliases": r.aliases, "validators": r.validators, "findings": r.findings}


def format_in_force(info: dict) -> str:
    lines = [f"Domain Profile in force at {info['path']}", f"sources: {', '.join(info['sources'])}"]
    for f in info["families"]:
        lines.append(f"family {f['dir']}: types {', '.join(f['types']) if f['types'] else 'any'}  [{f['source']}]")
    lines.append(f"types allowed: {', '.join(info['types_allowed'])}")
    for t, ti in info["types"].items():
        ext = f" extends {ti['extends']}" if ti.get("extends") else ""
        lines.append(f"type {t}{ext}  [{ti['source']}]")
        for fid, fd in ti["fields"].items():
            kind = fd.get("type", "?") + (f" of {fd['of']}" if fd.get("of") else "")
            if fd.get("values"):
                kind += " [" + ", ".join(f"{v['value']}" + ("" if v["source"] == fd["source"] else f" ({v['source']})")
                                         for v in fd["values"]) + "]"
            lines.append(f"  field {fid}: {kind}, level {fd.get('level', 'error')}  [{fd['source']}]")
        for k, e in ti["required"].items():
            code = f", code {e['code']}" if e.get("code") else ""
            lines.append(f"  required {k} ({_lvl(e)}{code})  [{e['source']}]")
        for k, e in ti["fixed"].items():
            lines.append(f"  fixed {k} = {e.get('value')!r} ({_lvl(e)})  [{e['source']}]")
        for k, e in ti["forbidden"].items():
            lines.append(f"  forbidden {k} ({_lvl(e)})  [{e['source']}]")
    for rule in info["rules"]:
        lines.append(f"rule {rule['name']}: when {rule['when']} require {rule['require']} ({_lvl(rule)})  [{rule['source']}]")
    for kind in ("types", "fields"):
        for name, a in info["aliases"][kind].items():
            lines.append(f"alias ({kind[:-1]}) {name} → {a['to']}  [{a['source']}]")
    for a in info["aliases"]["values"]:
        lines.append(f"alias (value) {a['from']} → {a['to']}  [{a['source']}]")
    for v in info["validators"]:
        lines.append(f"validator {v['name']}: {v['command']} (not run here)  [{v['source']}]")
    for f in info["findings"]:
        lines.append(f"{f['level']:5} {f['code']:22} {f['path']}: {f['message']}")
    for n in info.get("notices") or []:
        lines.append(f"NOTICE {n}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# The built-in profile against the standard's §4 table (make test [7])
# --------------------------------------------------------------------------
def _section_4_rows(standard_text: str) -> list[list[str]]:
    m = re.search(r"^## 4\. .*?$(.*?)^### 4\.1 ", standard_text, re.M | re.S)
    rows, body = [], False
    for line in (m.group(1) if m else "").splitlines():
        if line.startswith("|---"):
            body = True
        elif body and line.startswith("| `"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _extra_fields(description: str) -> list[str]:
    """The field names after 'Extra fields:' or 'Requires', outside parentheses, up to the next 'Body:'."""
    flat, depth = "", 0
    for ch in description:
        depth += ch == "("
        if depth == 0:
            flat += ch
        depth -= ch == ")" and depth > 0
    out = []
    for m in re.finditer(r"(?:Extra fields:|Requires)(.*?)(?:Body:|$)", flat):
        out += re.findall(r"`([a-z][a-z0-9_]*)`", m.group(1))
    return out


def standard_types(standard_text: str) -> dict:
    """type → { directory, fields } from the §4 table: shared rows split, root as /, a file or — as no directory."""
    out = {}
    for row in _section_4_rows(standard_text):
        names = re.findall(r"`([^`]+)`", row[0])
        cell = row[1]
        path = re.fullmatch(r"`([^`]+/)`(?:\s*\(.*\))?", cell)
        directory = "/" if cell.startswith("root") else ("/" + path.group(1) if path else None)
        for n in names:
            out[n] = {"directory": directory, "fields": sorted(_extra_fields(row[2]))}
    return out


def check_builtin(standard: Path, builtin: Path | None = None) -> list[str]:
    """Every §4 type has an entry in the built-in profile, with its usual directory and extra fields, and no other."""
    text = builtin_text(builtin)
    fm, err = _fm_of(text) if text is not None else (None, "the built-in profile cannot be read")
    if fm is None:
        return [err]
    want = standard_types(standard.read_text(encoding="utf-8"))
    have = fm.get("types") or {}
    problems = [f"§4 type '{t}' has no entry in the built-in profile" for t in want if t not in have]
    problems += [f"built-in type '{t}' is not in the §4 table" for t in have if t not in want]
    for t in (x for x in want if x in have):
        d = have[t] or {}
        if d.get("directory") != want[t]["directory"]:
            problems.append(f"{t}: directory {d.get('directory')!r}, §4 says {want[t]['directory']!r}")
        fields = sorted((d.get("fields") or {}))
        if fields != want[t]["fields"]:
            problems.append(f"{t}: fields {', '.join(fields) or '-'}, §4 names {', '.join(want[t]['fields']) or '-'}")
    if not want:
        problems.append(f"{standard}: no §4 type table found")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?", help="path to the bundle (default: search upwards for knowledge/)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--check-builtin", metavar="STANDARD",
                    help="check the built-in Domain Profile against the §4 type table of STANDARD (OKF-STANDARD.md)")
    args = ap.parse_args(argv)
    if args.check_builtin:
        problems = check_builtin(Path(args.check_builtin))
        for p in problems:
            print(f"ERROR {p}")
        if not problems:
            print(f"built-in Domain Profile matches §4 of {args.check_builtin}: "
                  f"{len(standard_types(Path(args.check_builtin).read_text(encoding='utf-8')))} types")
        return 1 if problems else 0
    bundle = Path(args.bundle).resolve() if args.bundle else find_bundle()
    if bundle is None or not bundle.is_dir():
        print("ERROR: bundle not found (knowledge/index.md). Pass its path.", file=sys.stderr)
        return 2
    r = load_profile(bundle)
    info = in_force(r)
    print(json.dumps(info, ensure_ascii=False, indent=2, default=str) if args.json else format_in_force(info))
    return 1 if r.findings else 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_profile.py --test): one per row of ticket D2
# --------------------------------------------------------------------------
_STAND_IN = """---
type: Domain Profile
title: Built-in Domain Profile (test stand-in)
description: The standard's types, as the test needs them.
types:
  Knowledge Fragment:
    directory: fragments/
    fields:
      occurred_at: { type: date_or_datetime, level: warn, code: BAD_ISO, required: { level: warn, code: FRAGMENT_NO_FIELD } }
      origin: { type: string, required: { level: warn, code: FRAGMENT_NO_FIELD } }
      participants: { type: list, of: actor, level: warn, code: BAD_ACTOR, required: { level: warn, code: FRAGMENT_NO_FIELD } }
      distillation_status: { type: enum, values: [pending, distilled, conflict], code: BAD_DISTILLATION_STATUS, required: { level: warn, code: FRAGMENT_NO_FIELD } }
  Open Question:
    fields:
      owner: { type: actor, level: warn, code: BAD_ACTOR, required: { level: warn, code: QUESTION_NO_FIELD } }
      question_status: { type: enum, values: [open, answered, dropped], code: BAD_QUESTION_STATUS }
  System:
    fields:
      owner: { type: actor, required: true }
  Policy: {}
  Term: {}
  Architecture Decision: {}
  Domain Profile: {}
---

# Why

Test stand-in for the built-in Domain Profile.
"""
_GEN = "generated: { by: okf-builder/test, at: 2026-11-02T12:00:00Z }\n"


def _builtin(tmp_path: Path) -> Path:
    p = tmp_path / "builtin" / "knowledge-3.0.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_STAND_IN, encoding="utf-8")
    return p


def _bundle(tmp_path: Path, profile: str | None = None, profile_name: str = PROFILE_30, extra: dict | None = None) -> Path:
    """A clean bundle: root index, log, project, base/ with its index, and base/profile.md when given."""
    k = tmp_path / "knowledge"
    (k / "base").mkdir(parents=True)
    base_entries = "* [Profile](profile.md) - The taxonomy.\n" if profile is not None else "_(empty)_\n"
    (k / "index.md").write_text(f'---\nokf_version: "0.2"\nokf_profile: "{profile_name}"\n---\n\n# Project\n\n'
                                "* [P](project.md) - P.\n\n# Subdirectories\n\n* [base](base/index.md) - Base.\n",
                                encoding="utf-8")
    (k / "log.md").write_text("# Bundle history\n\n## 2026-11-02\n* **Creation**: test.\n", encoding="utf-8")
    (k / "project.md").write_text("---\ntype: Project\ntitle: P\ndescription: P.\n" + _GEN + "---\n\nText.\n",
                                  encoding="utf-8")
    (k / "base" / "index.md").write_text("# base\n\n" + base_entries, encoding="utf-8")
    if profile is not None:
        (k / OWN_REL).write_text(_profile_doc(profile), encoding="utf-8")
    for rel, text in (extra or {}).items():
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
    return k


def _profile_doc(keys: str, title: str = "Domain Profile") -> str:
    return (f"---\ntype: Domain Profile\ntitle: {title}\ndescription: The taxonomy.\nstatus: draft\n" + keys.rstrip("\n")
            + "\n" + _GEN + "---\n\n# What this bundle holds\n\nText.\n")


def _codes(r: Resolved) -> list[str]:
    return sorted(f["code"] for f in r.findings)


def _one(r: Resolved, code: str) -> dict:
    found = [f for f in r.findings if f["code"] == code]
    assert len(found) == 1 and len(r.findings) == 1, r.findings
    return found[0]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                           "-c", "commit.gpgsign=false", *args], capture_output=True, text=True, check=True).stdout.strip()


def test_builtin_layer_from_file_or_names_of_section_4(tmp_path):
    r = load_profile(_bundle(tmp_path), builtin=_builtin(tmp_path))
    assert r.builtin_file and r.sources == ["built-in"] and r.findings == []
    assert type_in_force(r, "Knowledge Fragment")["fields"]["distillation_status"]["code"] == "BAD_DISTILLATION_STATUS"
    r = load_profile(_bundle(tmp_path / "b"), builtin=tmp_path / "missing.md")
    assert not r.builtin_file and r.findings == [] and set(STANDARD_TYPE_NAMES) == set(r.types)


def _standard() -> Path:
    return Path(__file__).resolve().parent.parent / "references" / "OKF-STANDARD.md"


def test_the_shipped_builtin_profile_loads_and_matches_section_4():
    import pytest

    if not BUILTIN_PATH.is_file() or not _standard().is_file():
        pytest.skip("okf-standard's profiles/ or references/ not beside this script")
    r = load_profile(Path("/nonexistent"), read_own=False)
    assert r.builtin_file and r.findings == [] and set(r.types) == set(STANDARD_TYPE_NAMES)
    assert check_builtin(_standard()) == []
    fragment = type_in_force(r, "Knowledge Fragment")
    assert {k: (e["level"], e["code"]) for k, e in fragment["required"].items()} == {
        k: ("warn", "FRAGMENT_NO_FIELD") for k in ("occurred_at", "origin", "participants", "distillation_status")}
    assert [x["code"] for x in r.rules] == ["QUESTION_NO_ANSWER"]


def test_check_builtin_names_each_type_or_field_that_differs_from_section_4(tmp_path):
    std = tmp_path / "OKF-STANDARD.md"
    std.write_text("## 4. Profile type vocabulary\n\n| `type` | Usual directory | Description |\n|---|---|---|\n"
                   "| `Term` / `Glossary` | `base/domain/` | A term. |\n"
                   "| `Knowledge Fragment` | `fragments/` | Extra fields: `occurred_at` (`YYYY-MM-DD`), `origin`, "
                   "`participants` (list), `distillation_status` (`pending` / `distilled`). Body: `# Record`. |\n"
                   "| `Conflict Log` | root (`conflict-log.md`) | The register. |\n| `Log` | — | log.md. |\n\n### 4.1 Next\n",
                   encoding="utf-8")
    assert standard_types(std.read_text(encoding="utf-8"))["Conflict Log"] == {"directory": "/", "fields": []}
    assert standard_types(std.read_text(encoding="utf-8"))["Log"] == {"directory": None, "fields": []}
    problems = check_builtin(std, _builtin(tmp_path))
    assert "§4 type 'Glossary' has no entry in the built-in profile" in problems
    assert "§4 type 'Conflict Log' has no entry in the built-in profile" in problems
    assert "built-in type 'Open Question' is not in the §4 table" in problems
    assert "Knowledge Fragment: directory 'fragments/', §4 says '/fragments/'" in problems
    assert "Term: directory None, §4 says '/base/domain/'" in problems
    assert not any(p.startswith("Knowledge Fragment: fields") for p in problems)  # parentheses are not fields
    assert main(["--check-builtin", str(std)]) == 1


def test_inlined_copy_is_read_when_the_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "BUILTIN_PATH", tmp_path / "missing.md")
    monkeypatch.setattr(sys.modules[__name__], "BUILTIN_TEXT", _STAND_IN)
    r = load_profile(_bundle(tmp_path))
    assert r.builtin_file and r.findings == [] and "Open Question" in r.types and "Glossary" not in r.types
    # a built-in file named by the caller is never replaced by the inlined copy
    assert not load_profile(_bundle(tmp_path / "b"), builtin=tmp_path / "missing.md").builtin_file


def test_the_builtin_file_wins_over_the_inlined_copy(tmp_path, monkeypatch):
    shipped = tmp_path / "profiles" / "knowledge-3.0.md"
    shipped.parent.mkdir()
    shipped.write_text("---\ntype: Domain Profile\ntitle: B\ndescription: B.\ntypes:\n  Glossary: {}\n  Domain Profile: {}\n"
                       "---\n\n# Why\n\nText.\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "BUILTIN_PATH", shipped)
    monkeypatch.setattr(sys.modules[__name__], "BUILTIN_TEXT", _STAND_IN)
    assert builtin_text() == shipped.read_text(encoding="utf-8")
    r = load_profile(_bundle(tmp_path))
    assert r.builtin_file and r.findings == [] and set(r.types) == {"Glossary", "Domain Profile"}


def test_check_builtin_names_a_type_whose_fields_differ_from_section_4(tmp_path):
    std = tmp_path / "OKF-STANDARD.md"
    std.write_text("## 4. Profile type vocabulary\n\n| `type` | Usual directory | Description |\n|---|---|---|\n"
                   "| `Open Question` | `base/questions/` | Extra fields: `owner`, `asked_in` (a path). |\n\n### 4.1 Next\n",
                   encoding="utf-8")
    problems = check_builtin(std, _builtin(tmp_path))
    assert "Open Question: fields owner, question_status, §4 names asked_in, owner" in problems


def test_raising_a_coded_requirement_keeps_its_code(tmp_path):
    k = _bundle(tmp_path, "by_type:\n  Open Question: { required: { owner: { level: error } } }\n")
    r = load_profile(k, builtin=_builtin(tmp_path))
    assert r.findings == []
    owner = type_in_force(r, "Open Question")["required"]["owner"]
    assert (owner["level"], owner["code"], owner["source"]) == ("error", "QUESTION_NO_FIELD", OWN_REL)


def test_30_bundle_without_profile_has_only_the_builtin_layer(tmp_path, capsys):
    import okf_lint

    k = _bundle(tmp_path)
    r = load_profile(k, builtin=_builtin(tmp_path))
    assert r.sources == ["built-in"] and not r.has_own
    rep, _, _ = okf_lint.lint(k)
    assert rep.items == [] and rep.notices == []
    assert okf_lint.main([str(k), "--strict"]) == 0
    assert "NOTICE" not in capsys.readouterr().out


_OWN = """types:
  Client Meeting:
    extends: Knowledge Fragment
    description: A meeting with a client
    fields:
      client: { type: string, level: warn }
families:
  /base/clients/:
    types: [Term, Knowledge Fragment]
    required: [tags]
by_type:
  Policy: { required: [stale_after] }
rules:
  - { name: distilled-names-client, when: { type: Client Meeting, distillation_status: distilled }, require: [client], level: warn }
aliases:
  types: { Reunión con cliente: Client Meeting }
  fields: { cliente: client }
  values: [{ from: { ingerido: true }, to: { distillation_status: distilled } }]
"""
_OWN_ARCHIVED = _OWN.replace("  Policy: { required: [stale_after] }\n", "  Policy: { required: [stale_after] }\n"
                             "  Knowledge Fragment: { values: { distillation_status: [archived] } }\n")


def test_own_profile_loads_into_one_resolved_structure_in_merge_order(tmp_path):
    r = load_profile(_bundle(tmp_path, _OWN), builtin=_builtin(tmp_path))
    assert r.findings == [] and r.has_own and r.sources == ["built-in", OWN_REL]
    cm = type_in_force(r, "Client Meeting")
    assert cm["fields"]["client"]["source"] == OWN_REL
    assert cm["fields"]["distillation_status"]["source"] == "built-in"  # inherited from the type it extends
    assert r.families["/base/clients/"]["required"]["tags"]["source"] == OWN_REL
    assert type_in_force(r, "Policy")["required"]["stale_after"]["source"] == OWN_REL
    assert [x["name"] for x in r.rules] == ["distilled-names-client"]
    assert r.aliases["types"]["Reunión con cliente"]["to"] == "Client Meeting"
    assert r.aliases["fields"]["cliente"]["to"] == "client" and len(r.aliases["values"]) == 1
    # a family that allows a type allows the local types that extend it
    assert in_force(r, "/base/clients/acme/")["types_allowed"] == ["Knowledge Fragment", "Term", "Client Meeting"]


def test_extends_bundle_path_is_merged_before_the_bundles_own(tmp_path):
    shared = _profile_doc("types:\n  Contract:\n    extends: Term\n    fields:\n      signed_on: { type: date }\n")
    own = "extends: [/base/shared/profile.md]\ntypes:\n  Supplier Contract:\n    extends: Contract\n"
    k = _bundle(tmp_path, own, extra={"base/shared/profile.md": shared})
    r = load_profile(k, builtin=_builtin(tmp_path))
    assert r.findings == [] and r.sources == ["built-in", "base/shared/profile.md", OWN_REL]
    assert type_in_force(r, "Supplier Contract")["fields"]["signed_on"]["source"] == "base/shared/profile.md"
    assert r.extended == {"base/shared/profile.md"}


def test_extends_pinned_reference_reads_git_show_at_the_commit(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "profiles").mkdir()
    (repo / "profiles" / "acme.md").write_text(_profile_doc("types:\n  Acme Thing:\n    extends: Term\n"), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "acme")
    sha = _git(repo, "rev-parse", "--short", "HEAD")
    # the working tree moves on: lint must read the commit, not the file on disk
    (repo / "profiles" / "acme.md").write_text(_profile_doc("types:\n  Other Thing: {}\n"), encoding="utf-8")
    k = _bundle(repo, f'extends: ["profiles/acme.md@{sha}"]\n')
    r = load_profile(k, builtin=_builtin(tmp_path))
    assert r.findings == [] and r.sources == ["built-in", f"profiles/acme.md@{sha}", OWN_REL]
    assert r.types["Acme Thing"]["source"] == f"profiles/acme.md@{sha}" and "Other Thing" not in r.types


def test_extends_url_is_unreadable_and_names_the_missing_support(tmp_path):
    k = _bundle(tmp_path, 'extends: ["https://github.com/acme/profiles/blob/3f2a9c1/acme.md"]\n')
    f = _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")
    assert "URLs are not read" in f["message"] and f["path"] == OWN_REL


def test_missing_reference_or_unresolvable_commit_is_unreadable(tmp_path):
    k = _bundle(tmp_path / "a", "extends: [/base/shared/missing.md]\n")
    assert "does not exist" in _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")["message"]
    k = _bundle(tmp_path / "out", "extends: [/../outside.md]\n")
    assert "the path leaves the bundle" in _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")["message"]
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README").write_text("x\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")
    sha = _git(repo, "rev-parse", "--short", "HEAD")
    k = _bundle(repo, 'extends: ["profiles/acme.md@abc1234"]\n')
    assert "cannot resolve commit abc1234" in _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")["message"]
    (k / OWN_REL).write_text(_profile_doc(f'extends: ["profiles/acme.md@{sha}"]\n'), encoding="utf-8")
    assert "does not exist at commit" in _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")["message"]


def test_pinned_reference_outside_a_git_repository_is_unreadable(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))  # git does not look above tmp_path
    k = _bundle(tmp_path / "nogit", 'extends: ["profiles/acme.md@abc1234"]\n')
    if _Reader(k, Resolved()).toplevel() is not None:
        pytest.skip(f"{tmp_path} is inside a git work tree even with GIT_CEILING_DIRECTORIES set")
    f = _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")
    assert "not inside a git repository" in f["message"]


def test_pinned_blob_missing_from_a_partial_clone_is_unreadable_and_never_fetched(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    _git(origin, "config", "uploadpack.allowFilter", "true")
    (origin / "profiles").mkdir()
    (origin / "profiles" / "acme.md").write_text(_profile_doc("types:\n  Acme Thing:\n    extends: Term\n"), encoding="utf-8")
    _git(origin, "add", ".")
    _git(origin, "commit", "-q", "-m", "acme")
    sha = _git(origin, "rev-parse", "HEAD")
    _git(origin, "rm", "-q", "profiles/acme.md")
    (origin / "README").write_text("x\n", encoding="utf-8")
    _git(origin, "add", ".")
    _git(origin, "commit", "-q", "-m", "drop acme")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--filter=blob:none", origin.as_uri(), str(clone))
    blob = _git(origin, "rev-parse", f"{sha}:profiles/acme.md")
    # rev-list --missing=print lists absent objects without fetching them, on any git
    missing = ["rev-list", "--objects", "--missing=print", sha]
    assert f"?{blob}" in _git(clone, *missing).split()  # the blob is not local
    k = _bundle(clone, f'extends: ["profiles/acme.md@{sha[:7]}"]\n')
    f = _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")
    no_flag = subprocess.run(["git", "--no-lazy-fetch", "version"], capture_output=True).returncode != 0
    assert ("needs git 2.44" if no_flag else "not in the local object store") in f["message"], f
    assert f"?{blob}" in _git(clone, *missing).split()  # and lint did not fetch it


def test_git_without_no_lazy_fetch_makes_a_pinned_profile_unreadable(tmp_path, monkeypatch):
    real = shutil.which("git")
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "git").write_text('#!/bin/sh\nif [ "$1" = "--no-lazy-fetch" ]; then\n'
                              '  echo "unknown option: --no-lazy-fetch" >&2; exit 129\nfi\n'
                              f'exec "{real}" "$@"\n', encoding="utf-8")
    (fake / "git").chmod(0o755)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "profiles").mkdir()
    (repo / "profiles" / "acme.md").write_text(_profile_doc("types:\n  Acme Thing:\n    extends: Term\n"), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "acme")
    sha = _git(repo, "rev-parse", "--short", "HEAD")
    k = _bundle(repo, f'extends: ["profiles/acme.md@{sha}"]\n')
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ['PATH']}")
    f = _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_UNREADABLE")
    assert "needs git 2.44 or later" in f["message"], f


def test_same_id_from_two_sources_is_a_duplicate_naming_both(tmp_path):
    shared = _profile_doc("types:\n  Contract: { extends: Term }\nfamilies:\n  /base/clients/: {}\n"
                          "rules:\n  - { name: r1, when: { type: Term }, require: [tags] }\naliases:\n  types: { Contrato: Contract }\n"
                          "  values: [{ from: { ingerido: true }, to: { distillation_status: distilled } }]\n")
    cases = {
        "type": "types:\n  Contract: { extends: Term }\n",
        "standard type declared again": "types:\n  Knowledge Fragment: {}\n",
        "family": "families:\n  /base/clients/: {}\n",
        "rule": "rules:\n  - { name: r1, when: { type: Term }, require: [title] }\n",
        "alias": "aliases:\n  types: { Contrato: Contract }\n",
        "alias named like a type": "aliases:\n  types: { Policy: Contract }\n",
        "value alias": "aliases:\n  values: [{ from: { ingerido: true }, to: { distillation_status: pending } }]\n",
        "alias named like a field": "aliases:\n  fields: { owner: client }\n",
    }
    for n, (case, own) in enumerate(cases.items()):
        k = _bundle(tmp_path / str(n), "extends: [/base/shared/profile.md]\n" + own,
                    extra={"base/shared/profile.md": shared})
        f = _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_DUPLICATE_ID")
        if case == "standard type declared again":
            assert "built-in" in f["message"] and OWN_REL in f["message"], f
        elif case in ("alias named like a type", "alias named like a field"):
            assert "built-in" in f["message"] and f["path"] == OWN_REL, f
        else:
            assert "base/shared/profile.md" in f["message"] and OWN_REL in f["message"], (case, f)


def test_changing_an_inherited_item_through_an_adding_key_is_redefined(tmp_path):
    cases = {
        "local type re-declares an inherited field":
            "types:\n  Client Meeting:\n    extends: Knowledge Fragment\n    fields:\n      origin: { type: string }\n",
        "by_type lowers a level": "by_type:\n  System: { required: { owner: { level: warn } } }\n",
        "by_type makes a field optional": "by_type:\n  System: { required: { owner: false } }\n",
        "by_type changes a field type": "by_type:\n  System: { fields: { owner: { type: string } } }\n",
        "by_type removes an enum value":
            "by_type:\n  Open Question: { fields: { question_status: { type: enum, values: [open, answered] } } }\n",
        "by_type gives values to a non-enum": "by_type:\n  System: { values: { owner: [nobody] } }\n",
        "family lowers a level": "fixed:\n  okf_lang: { value: en }\nfamilies:\n  /base/x/: { fixed: { okf_lang: { value: en, level: warn } } }\n",
        "family makes a field optional": "families:\n  /base/systems/: { types: [System], required: { owner: false } }\n",
        "by_type changes a fixed value": "fixed:\n  okf_lang: { value: en }\nby_type:\n  Term: { fixed: { okf_lang: { value: es } } }\n",
        "by_type lowers a forbidden key":
            "forbidden:\n  draft: { reason: r }\nby_type:\n  Term: { forbidden: { draft: { reason: r, level: warn } } }\n",
    }
    expected = {
        "by_type changes a field type": "by_type.System: declares field 'owner' again, declared by built-in: changes its type from actor to string",
        "by_type removes an enum value": "by_type.Open Question: declares field 'question_status' again, declared by built-in: removes value(s) dropped",
        "by_type changes a fixed value": "by_type.Term: fixes 'okf_lang' to 'es', fixed to 'en' by base/profile.md",
        "by_type lowers a forbidden key": "by_type.Term: lowers forbidden 'draft' from error (by base/profile.md)",
    }
    for n, (case, own) in enumerate(cases.items()):
        f = _one(load_profile(_bundle(tmp_path / str(n), own), builtin=_builtin(tmp_path)), "PROFILE_REDEFINED")
        assert f["path"] == OWN_REL, (case, f)
        if case in expected:
            assert expected[case] in f["message"], (case, f)
    # raising a level and adding a requirement are additions, not redefinitions
    ok = "by_type:\n  Open Question: { required: { owner: { level: error } }, forbidden: { draft_notes: {} } }\n"
    assert load_profile(_bundle(tmp_path / "ok", ok), builtin=_builtin(tmp_path)).findings == []


def _swap(a: str, b: str) -> list[str]:
    return [a + b, b + a]


def test_nested_families_and_by_type_give_the_same_result_in_either_order(tmp_path):
    inner_low = "  /base/a/b/: { forbidden: { x: { reason: r, level: warn } } }\n"
    outer_high = "  /base/a/: { forbidden: { x: { reason: r } } }\n"
    for n, fams in enumerate(_swap(inner_low, outer_high)):
        r = load_profile(_bundle(tmp_path / f"f{n}", "families:\n" + fams), builtin=_builtin(tmp_path))
        assert "lowers forbidden 'x'" in _one(r, "PROFILE_REDEFINED")["message"], fams
        assert _lvl(in_force(r, "/base/a/b/")["types"]["Term"]["forbidden"]["x"]) == "error", fams
    inner_high = "  /base/a/b/: { forbidden: { x: { reason: r } }, fixed: { okf_lang: { value: en } } }\n"
    outer_low = "  /base/a/: { forbidden: { x: { reason: r, level: warn } }, fixed: { okf_lang: { value: en, level: warn } } }\n"
    for n, fams in enumerate(_swap(inner_high, outer_low)):
        r = load_profile(_bundle(tmp_path / f"g{n}", "families:\n" + fams), builtin=_builtin(tmp_path))
        assert r.findings == [], fams
        term = in_force(r, "/base/a/b/")["types"]["Term"]
        assert _lvl(term["forbidden"]["x"]) == "error" and _lvl(term["fixed"]["okf_lang"]) == "error", fams
    req_low = "  /base/a/b/: { required: { tags: { level: warn } } }\n"
    req_high = "  /base/a/: { required: [tags] }\n"
    for n, fams in enumerate(_swap(req_low, req_high)):
        r = load_profile(_bundle(tmp_path / f"r{n}", "families:\n" + fams), builtin=_builtin(tmp_path))
        assert "lowers 'tags' from error" in _one(r, "PROFILE_REDEFINED")["message"], fams
    sub = "types:\n  Client Meeting: { extends: Knowledge Fragment }\nby_type:\n"
    sub_low = "  Client Meeting: { required: { tags: { level: warn } } }\n"
    base_high = "  Knowledge Fragment: { required: [tags] }\n"
    for n, bt in enumerate(_swap(sub_low, base_high)):
        r = load_profile(_bundle(tmp_path / f"b{n}", sub + bt), builtin=_builtin(tmp_path))
        assert "by_type.Client Meeting: lowers 'tags'" in _one(r, "PROFILE_REDEFINED")["message"], bt


def test_a_family_cannot_loosen_what_a_type_or_by_type_requires(tmp_path):
    cases = {
        "family without types makes a type requirement optional": "families:\n  /base/x/: { required: { owner: false } }\n",
        "family without types lowers a type requirement": "families:\n  /base/x/: { required: { owner: { level: warn } } }\n",
        "family lowers a by_type requirement":
            "by_type:\n  System: { required: [tags] }\nfamilies:\n  /base/x/: { types: [System], required: { tags: { level: warn } } }\n",
        "family makes a by_type requirement optional":
            "by_type:\n  System: { required: [tags] }\nfamilies:\n  /base/x/: { types: [System], required: { tags: false } }\n",
        "family lowers a by_type forbidden key":
            "by_type:\n  System: { forbidden: { x: { reason: r } } }\nfamilies:\n  /base/x/: { forbidden: { x: { reason: r, level: warn } } }\n",
    }
    for n, (case, own) in enumerate(cases.items()):
        f = _one(load_profile(_bundle(tmp_path / str(n), own), builtin=_builtin(tmp_path)), "PROFILE_REDEFINED")
        assert f["path"] == OWN_REL and "family /base/x/" in f["message"], (case, f)
    # a family that only raises, or names a field no covered type requires, adds
    ok = "families:\n  /base/x/: { required: { owner: { level: error }, tags: { level: warn } } }\n"
    assert load_profile(_bundle(tmp_path / "ok", ok), builtin=_builtin(tmp_path)).findings == []


def test_by_type_values_add_archived_for_the_type_and_its_local_subtypes(tmp_path):
    own = _OWN_ARCHIVED
    r = load_profile(_bundle(tmp_path, own), builtin=_builtin(tmp_path))
    assert r.findings == []
    for t in ("Knowledge Fragment", "Client Meeting"):
        vals = type_in_force(r, t)["fields"]["distillation_status"]["values"]
        assert [v["value"] for v in vals] == ["pending", "distilled", "conflict", "archived"], t
        assert vals[-1]["source"] == OWN_REL
    assert "archived" not in [v["value"] for v in type_in_force(r, "Open Question")["fields"]["question_status"]["values"]]


def test_local_type_extending_an_unknown_type_is_invalid(tmp_path):
    k = _bundle(tmp_path, "types:\n  Client Meeting: { extends: Knowledge Fragmnet }\n")
    assert "Knowledge Fragmnet" in _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_INVALID")["message"]
    # without the built-in file, the names of §4 still let a local type extend a standard one
    k = _bundle(tmp_path / "b", "types:\n  Client Meeting: { extends: Knowledge Fragment }\n")
    assert load_profile(k, builtin=tmp_path / "missing.md").findings == []


def test_malformed_keys_are_invalid(tmp_path):
    cases = {
        "field type": "types:\n  T:\n    fields:\n      f: { type: text }\n",
        "level": "types:\n  T:\n    fields:\n      f: { type: string, level: info }\n",
        "enum without values": "types:\n  T:\n    fields:\n      f: { type: enum }\n",
        "rule without name": "rules:\n  - { when: { type: T }, require: [f] }\n",
        "list without of": "types:\n  T:\n    fields:\n      f: { type: list }\n",
        "family outside base": "families:\n  clients/: {}\n",
        "pinned to a branch": 'extends: ["profiles/acme.md@main"]\n',
        "extends neither form": 'extends: ["profiles/acme.md"]\n',
        "by_type adds a field": "by_type:\n  Term: { fields: { newf: { type: string } } }\n",
        "by_type values for a missing field": "by_type:\n  Term: { values: { nope: [a] } }\n",
        "alias for an undeclared type": "aliases:\n  types: { X: Nope }\n",
        "type extends itself": "types:\n  A: { extends: A }\n",
    }
    for n, (case, own) in enumerate(cases.items()):
        f = _one(load_profile(_bundle(tmp_path / str(n), own), builtin=_builtin(tmp_path)), "PROFILE_INVALID")
        assert f["path"] == OWN_REL, (case, f)


def test_a_profile_that_cannot_be_read_as_one_is_invalid(tmp_path):
    term = "---\ntype: Term\ntitle: T\ndescription: T.\n" + _GEN + "---\n\nText.\n"
    ext = "extends: [/base/shared/profile.md]\n"
    cases = {
        "extends a concept of another type": (ext, {"base/shared/profile.md": term}, "base/shared/profile.md",
                                              "a profile in extends must have type: Domain Profile"),
        "extends a file without frontmatter": (ext, {"base/shared/profile.md": "no frontmatter\n"}, "base/shared/profile.md",
                                               "no YAML frontmatter block"),
        "base/profile.md without frontmatter": (None, {OWN_REL: "no frontmatter\n"}, OWN_REL, "no YAML frontmatter block"),
        "base/profile.md of another type": (None, {OWN_REL: term}, OWN_REL, "base/profile.md must have type: Domain Profile"),
    }
    for n, (case, (own, extra, path, msg)) in enumerate(cases.items()):
        f = _one(load_profile(_bundle(tmp_path / str(n), own, extra=extra), builtin=_builtin(tmp_path)), "PROFILE_INVALID")
        assert (f["path"], f["message"]) == (path, msg), (case, f)
    broken = tmp_path / "broken.md"
    broken.write_text(_profile_doc("types:\n  T:\n    fields:\n      f: { type: text }\n"), encoding="utf-8")
    r = load_profile(_bundle(tmp_path / "builtin"), builtin=broken)
    assert _one(r, "PROFILE_INVALID")["path"] == BUILTIN_LABEL and not r.builtin_file
    assert set(r.types) == set(STANDARD_TYPE_NAMES)  # the names of §4 still apply
    r = load_profile(_bundle(tmp_path / "cycle", "types:\n  A: { extends: B }\n  B: { extends: A }\n"), builtin=_builtin(tmp_path))
    assert [f["message"] for f in r.findings] == ["type 'A' extends itself: A → B → A", "type 'B' extends itself: B → A → B"]


def test_fixed_or_forbidden_redefined_across_extends(tmp_path):
    shared = _profile_doc("fixed:\n  okf_lang: { value: en }\nforbidden:\n  draft: { reason: r }\n")
    cases = {
        "fixed to another value": ("fixed:\n  okf_lang: { value: es }\n", "fixes 'okf_lang' to 'es', fixed to 'en' by base/shared/profile.md"),
        "forbidden at a lower level": ("forbidden:\n  draft: { reason: r, level: warn }\n",
                                       "lowers forbidden 'draft' from error (by base/shared/profile.md) to warn"),
        "fixed at a lower level": ("fixed:\n  okf_lang: { value: en, level: warn }\n",
                                   "lowers fixed 'okf_lang' from error (by base/shared/profile.md) to warn"),
    }
    for n, (case, (own, msg)) in enumerate(cases.items()):
        k = _bundle(tmp_path / str(n), "extends: [/base/shared/profile.md]\n" + own, extra={"base/shared/profile.md": shared})
        f = _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_REDEFINED")
        assert (f["path"], f["message"]) == (OWN_REL, msg), case
    k = _bundle(tmp_path / "same", "extends: [/base/shared/profile.md]\nfixed:\n  okf_lang: { value: en }\n",
                extra={"base/shared/profile.md": shared})
    assert load_profile(k, builtin=_builtin(tmp_path)).findings == []


def test_domain_profile_elsewhere_than_base_profile_is_misplaced(tmp_path):
    import okf_lint

    stray = _profile_doc("types: {}\n")
    k = _bundle(tmp_path, "extends: [/base/shared/profile.md]\n",
                extra={"base/shared/profile.md": stray, "base/clients/profile.md": stray})
    (k / "base" / "index.md").write_text("# base\n\n* [Profile](profile.md) - P.\n* [shared](shared/index.md) - S.\n"
                                         "* [clients](clients/index.md) - C.\n", encoding="utf-8")
    (k / "base" / "shared" / "index.md").write_text("# shared\n\n* [P](profile.md) - The taxonomy.\n", encoding="utf-8")
    (k / "base" / "clients" / "index.md").write_text("# clients\n\n* [P](profile.md) - The taxonomy.\n", encoding="utf-8")
    rep, _, _ = okf_lint.lint(k)
    assert [(i["code"], i["path"]) for i in rep.items] == [("PROFILE_MISPLACED", "base/clients/profile.md")]


def test_profile_md_in_a_20_bundle_is_ignored_with_a_notice(tmp_path, capsys):
    import okf_lint

    k = _bundle(tmp_path, "types:\n  T:\n    fields:\n      f: { type: text }\n", profile_name="knowledge/2.0")
    assert not load_profile(k, builtin=_builtin(tmp_path)).has_own
    rep, _, _ = okf_lint.lint(k)
    assert rep.items == [] and len(rep.notices) == 1
    assert okf_lint.main([str(k), "--strict"]) == 0
    out = capsys.readouterr().out
    assert "NOTICE Domain Profile base/profile.md ignored" in out and "knowledge/3.0" in out
    assert okf_lint.main([str(k), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["notices"][0].startswith("Domain Profile base/profile.md ignored")


def test_extends_cycle_is_invalid_and_names_the_cycle(tmp_path):
    a = _profile_doc("extends: [/base/shared/b.md]\n")
    b = _profile_doc("extends: [/base/shared/a.md]\n")
    k = _bundle(tmp_path, "extends: [/base/shared/a.md]\n", extra={"base/shared/a.md": a, "base/shared/b.md": b})
    f = _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_INVALID")
    assert f["message"] == "extends cycle: base/shared/a.md → base/shared/b.md → base/shared/a.md"
    k = _bundle(tmp_path / "self", "extends: [/base/profile.md]\n")
    assert "base/profile.md → base/profile.md" in _one(load_profile(k, builtin=_builtin(tmp_path)), "PROFILE_INVALID")["message"]


def test_lint_profiles_prints_what_is_in_force_and_who_declared_it(tmp_path, capsys, monkeypatch):
    import okf_lint

    own = (_OWN_ARCHIVED.replace("    required: [tags]\n", "    required: [tags]\n"
                                 "    forbidden: { draft_notes: { reason: drafts stay out, level: warn } }\n")
           + "fixed:\n  okf_lang: { value: en }\n")
    k = _bundle(tmp_path, own)
    monkeypatch.setattr(sys.modules[__name__], "BUILTIN_PATH", _builtin(tmp_path))
    monkeypatch.setattr(okf_lint, "load_profile", lambda b, **kw: load_profile(b, builtin=_builtin(tmp_path), **kw))
    assert okf_lint.main([str(k), "--profiles", "/base/clients/"]) == 0
    out = capsys.readouterr().out
    assert "Domain Profile in force at /base/clients/" in out
    assert "types allowed: Knowledge Fragment, Term, Client Meeting" in out
    assert "type Client Meeting extends Knowledge Fragment  [base/profile.md]" in out
    assert "  field client: string, level warn  [base/profile.md]" in out
    assert "  field distillation_status: enum [pending, distilled, conflict, archived (base/profile.md)]" in out
    assert "  required tags (error)  [base/profile.md]" in out
    assert "  required origin (warn, code FRAGMENT_NO_FIELD)  [built-in]" in out
    assert "  fixed okf_lang = 'en' (error)  [base/profile.md]" in out
    assert "  forbidden draft_notes (warn)  [base/profile.md]" in out
    assert "rule distilled-names-client" in out and "alias (type) Reunión con cliente → Client Meeting" in out
    assert okf_lint.main([str(k), "--profiles", str(k / "base" / "clients"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["path"] == "/base/clients/" and data["types_allowed"] == ["Knowledge Fragment", "Term", "Client Meeting"]
    assert data["types"]["Client Meeting"]["fields"]["client"]["source"] == OWN_REL
    assert data["aliases"]["fields"]["cliente"] == {"to": "client", "source": OWN_REL}
    for t in data["types_allowed"]:
        assert data["types"][t]["fixed"]["okf_lang"] == {"value": "en", "source": OWN_REL}, t
        assert data["types"][t]["forbidden"]["draft_notes"] == {"reason": "drafts stay out", "level": "warn",
                                                                "source": OWN_REL}, t
    assert okf_lint.main([str(k), "--profiles", "/base/", "--json"]) == 0  # the family's forbidden applies only under it
    assert "draft_notes" not in json.loads(capsys.readouterr().out)["types"]["Term"]["forbidden"]
    assert okf_lint.main([str(k), "--profiles", "--no-profile"]) == 2


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
