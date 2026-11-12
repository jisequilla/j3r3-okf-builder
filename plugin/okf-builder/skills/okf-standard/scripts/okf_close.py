#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_close.py — Checks that an operational instance may close into its parent, and writes the closing once a
person has approved it (standard §2.2, ADR-0039 decisions 7, 8, 9 and 12).

Usage:
    uv run okf_close.py <instance> [--json]
    uv run okf_close.py <instance> --apply --fragment /fragments/<file>.md --by human:<id> --actor <actor>
                        [--carry <instance item>=<parent item>]... [--at <ISO 8601>] [--dry-run]

- Report mode writes nothing. It lists what blocks the closing (NOT_INSTANCE: no kind or no parent;
  ALREADY_CLOSED; PARENT_CLOSED; CHILD_OPEN: it holds an instance not closed; PENDING_FRAGMENT: a pending fragment,
  aliases resolved), every concept of the instance's base/ (index.md and profile.md aside, the questions included)
  with its path from the parent (from_parent) and the parent concept at the same path, the open questions and the
  open or proposed conflicts of its Conflict Log. Exit 0 when nothing blocks, 1 when something does, 2 on a bad
  argument.
- Sorting each concept (promote, conflict or stays) is the person's and the agent's, never this script's: okf-distill's
  Closing mode proposes it, the person approves it and the agent applies it in the parent, with the closing fragment
  in the parent's fragments/.
- --apply checks first, and on any failure writes nothing and exits 1, naming each one:
  1. nothing blocks;
  2. --fragment is in the parent's fragments/, distilled, and the Concept cells of its ledger link, resolved from
     the parent, exactly the instance's concepts; each row's Kind is promote, conflict or stays;
  3. a promote row also links a parent concept whose sources hold resource == that instance concept's from_parent;
  4. every open question and every open or proposed conflict has a --carry: a question to an open Open Question of
     the parent whose asked_in is its from_parent, a conflict to an open row of the parent's Conflict Log whose Source
     or Description links a path inside the instance.
  Then it writes: each carried question (question_status: carried, carried_to the parent's item as a path relative to
  the instance root, generated), each carried conflict row (State carried, Resolution naming the parent's row and
  Conflict Log path in code, Decided --by) with the Conflict Log's generated, each instance fragment in conflict whose
  conflicts are now all carried or closed (distillation_status: distilled, its ledger Outcome `carried up: C-NNN
  (`<path>`)`), the instance's root index.md (state: closed and closed_at, other keys untouched), then regenerates the
  indexes of the instance and of the parent. --at (default now, computed once) is closed_at and every generated.at.
- --carry: `<instance item>=<parent item>`, a question as `base/questions/<q>.md` or `/base/questions/<q>.md` (both
  read alike) to its parent bundle path, or a conflict as `C-001=C-002`.
- --dry-run: the checks and the list of writes, with nothing written.
- The log entries (**Closing** in the instance, **Update** in the parent) are the agent's, as is the closing fragment.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    ACTOR_RE,
    BASE_DIR,
    FRAGMENTS_DIR,
    LINK_RE,
    PROFILE_REL,
    TABLE_SEP_RE,
    Doc,
    as_list,
    is_iso,
    now_iso,
    resolve_link,
    root_frontmatter,
    scan_bundle,
    split_frontmatter,
    table_cells,
)
from okf_lint import Report, _is_fragment, find_tree, kind_of, profile_structure, read_ledger  # noqa: E402
from okf_migrate import blocks_to_raw, fm_blocks, get_block  # noqa: E402
from okf_profile import Resolved, canonical_type, resolve_aliases  # noqa: E402

OPEN_CONFLICT = ("open", "proposed")
CLOSING_KINDS = ("promote", "conflict", "stays")
CONFLICT_ID_RE = re.compile(r"^C-\d+$")
OUTCOME_RE = re.compile(r"^(?:open|proposed):\s*(C-\d+)$")


@dataclass
class Bundle:
    root: Path
    fm: dict
    prof: Resolved
    docs: list[Doc]
    nested: list[str]

    def doc(self, path: Path) -> Doc | None:
        return next((d for d in self.docs if d.path.resolve() == path.resolve()), None)

    def fm_of(self, d: Doc) -> dict:
        return resolve_aliases(self.prof, d.frontmatter or {})

    def type_of(self, d: Doc) -> str | None:
        return canonical_type(self.prof, (d.frontmatter or {}).get("type"))

    def conflict_log(self) -> Doc | None:
        return next((d for d in self.docs if not d.is_reserved and self.type_of(d) == "Conflict Log"), None)


def load_bundle(root: Path) -> Bundle:
    """The bundle as lint reads it: its scan and the Domain Profile in force (the tree's, for an instance)."""
    tree = find_tree(root, Report())
    sc = scan_bundle(root)
    prof = profile_structure(root, sc.docs, tree.domain if tree is not None else None)[0]
    return Bundle(root, root_frontmatter(root), prof, sc.docs, sc.nested)


def bpath(root: Path, path: Path) -> str:
    """A bundle path: `/` and the path from the bundle root."""
    return "/" + Path(os.path.relpath(path.resolve(), root.resolve())).as_posix()


def under(path: Path | None, root: Path) -> bool:
    return path is not None and path.resolve().is_relative_to(root.resolve())


# --------------------------------------------------------------------------
# Conflict Log rows
# --------------------------------------------------------------------------
@dataclass
class ConflictRow:
    cells: list[str]
    line: int  # index in the file's lines
    cols: dict

    def get(self, name: str) -> str:
        i = self.cols.get(name)
        return self.cells[i] if i is not None and i < len(self.cells) else ""

    @property
    def id(self) -> str:
        return self.get("id").strip("`* ")

    @property
    def state(self) -> str:
        return self.get("state").strip("`* ").lower()


def conflict_rows(text: str) -> list[ConflictRow]:
    """The rows of each table whose header names a State column, read as lint reads them (_open_conflicts)."""
    rows: list[ConflictRow] = []
    cols: dict | None = None
    for n, line in enumerate(text.split("\n")):
        cells = table_cells(line)
        if cells is None:
            cols = None
            continue
        if cols is None:
            names = [c.strip("`* ").lower() for c in cells]
            cols = {name: i for i, name in enumerate(names)} if "state" in names else {}
            continue
        if cols and not TABLE_SEP_RE.match(line.strip()):
            rows.append(ConflictRow(cells, n, cols))
    return rows


def row_line(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
def parent_root(inst: Bundle) -> Path | None:
    par = inst.fm.get("parent")
    return (inst.root / par).resolve() if isinstance(par, str) and par.strip() else None


def blockers(inst: Bundle, parent: Bundle | None) -> list[dict]:
    def b(code: str, path: str, message: str) -> dict:
        return {"code": code, "path": path, "message": message}

    kind = kind_of(inst.fm, inst.prof)
    if kind is None or parent is None:
        why = "declares no kind" if kind is None else "declares no parent, or its parent is not a bundle"
        return [b("NOT_INSTANCE", "index.md", f"the root index.md {why}: only an operational instance in a tree closes")]
    out = []
    if inst.fm.get("state") == "closed":
        out.append(b("ALREADY_CLOSED", "index.md", f"it is already closed (closed_at {inst.fm.get('closed_at')})"))
    if parent.fm.get("state") == "closed":
        out.append(b("PARENT_CLOSED", os.path.relpath(parent.root / "index.md", inst.root),
                     "its parent is closed: a closed bundle is never edited, so nothing can be distilled into it"))
    for rel in inst.nested:
        cfm = root_frontmatter(inst.root / rel.rstrip("/"))
        if kind_of(cfm, None) is not None and cfm.get("state") != "closed":
            out.append(b("CHILD_OPEN", rel + "index.md", f"it holds an instance whose state is {cfm.get('state')}: "
                         "close it first, one level at a time"))
    for d in inst.docs:
        fm = inst.fm_of(d)
        if (d.rel.startswith(FRAGMENTS_DIR + "/") and not d.is_reserved and _is_fragment(fm, inst.prof)
                and fm.get("distillation_status") == "pending"):
            out.append(b("PENDING_FRAGMENT", d.rel, "a pending fragment: distill it into the instance first"))
    return out


def concepts(inst: Bundle, parent: Bundle | None) -> list[dict]:
    out = []
    for d in sorted(inst.docs, key=lambda x: x.rel):
        if not d.rel.startswith(BASE_DIR + "/") or d.path.name == "index.md" or d.rel == PROFILE_REL:
            continue
        fm = d.frontmatter or {}
        same = parent is not None and (parent.root / d.rel).is_file()
        out.append({"path": "/" + d.rel, "type": inst.type_of(d), "title": fm.get("title"),
                    "from_parent": bpath(parent.root, d.path) if parent is not None else None,
                    "parent_same_path": "/" + d.rel if same else None})
    return out


def open_questions(inst: Bundle) -> list[dict]:
    out = []
    for d in sorted(inst.docs, key=lambda x: x.rel):
        fm = inst.fm_of(d)
        if fm.get("type") == "Open Question" and fm.get("question_status") == "open":
            out.append({"path": "/" + d.rel, "owner": fm.get("owner")})
    return out


def open_conflicts(inst: Bundle) -> list[dict]:
    log = inst.conflict_log()
    if log is None:
        return []
    return [{"id": r.id, "state": r.state, "description": r.get("description")}
            for r in conflict_rows(log.path.read_text(encoding="utf-8")) if r.state in OPEN_CONFLICT]


def report(instance: str) -> dict:
    inst = load_bundle(Path(instance).resolve())
    proot = parent_root(inst)
    parent = load_bundle(proot) if proot is not None and (proot / "index.md").is_file() else None
    return {"instance": instance, "parent": inst.fm.get("parent"), "kind": kind_of(inst.fm, inst.prof),
            "state": inst.fm.get("state"), "blockers": blockers(inst, parent), "concepts": concepts(inst, parent),
            "questions": open_questions(inst), "conflicts": open_conflicts(inst)}


# --------------------------------------------------------------------------
# Apply: the checks, then the writes, all or nothing
# --------------------------------------------------------------------------
@dataclass
class Plan:
    failures: list[tuple[int, str, str]] = field(default_factory=list)  # (check, subject, message)
    writes: dict = field(default_factory=dict)  # Path -> new text, in the order written

    def fail(self, check: int, subject: str, message: str) -> None:
        self.failures.append((check, subject, message))


def set_keys(text: str, values: dict, after: dict | None = None) -> str:
    """The text with each `key: value` of values set in its frontmatter, every other line kept; a new key goes after
    the key `after` names, else last."""
    lines = text.split("\n")
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    blocks = fm_blocks("\n".join(lines[1:end]))
    for key, value in values.items():
        i = get_block(blocks, key)
        if i >= 0:
            blocks[i] = (key, [f"{key}: {value}"])
        else:
            j = get_block(blocks, (after or {}).get(key, ""))
            blocks.insert(j + 1 if j >= 0 else len(blocks), (key, [f"{key}: {value}"]))
    return "\n".join(["---", blocks_to_raw(blocks), *lines[end:]])


def body_start(text: str) -> int:
    """The index, in the file's lines, of the first body line (the one after the closing ---)."""
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return 0
    return next((i + 1 for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)


def parse_carries(values: list[str]) -> dict:
    """{instance item: parent item}; a question as its /base/... path, a conflict as its C-NNN. ValueError if bad."""
    out = {}
    for v in values:
        left, sep, right = v.partition("=")
        left, right = left.strip(), right.strip()
        if not sep or not left or not right:
            raise ValueError(f"--carry {v!r}: write <instance item>=<parent item>")
        if CONFLICT_ID_RE.match(left) or CONFLICT_ID_RE.match(right):
            if not (CONFLICT_ID_RE.match(left) and CONFLICT_ID_RE.match(right)):
                raise ValueError(f"--carry {v!r}: a conflict is carried as C-NNN=C-NNN")
        else:
            left, right = "/" + left.lstrip("/"), "/" + right.lstrip("/")
        if left in out:
            raise ValueError(f"--carry {left} given twice")
        out[left] = right
    return out


def check_fragment(inst: Bundle, parent: Bundle, fragment: str, items: list[dict], plan: Plan) -> None:
    """Checks 2 and 3: the closing fragment and its ledger."""
    path = (parent.root / fragment.lstrip("/")).resolve()
    if not under(path, parent.root / FRAGMENTS_DIR) or under(path, inst.root):
        plan.fail(2, fragment, "is not in the parent's fragments/")
        return
    doc = parent.doc(path)
    if doc is None:
        plan.fail(2, fragment, "does not exist in the parent")
        return
    fm = parent.fm_of(doc)
    status = fm.get("distillation_status")
    if not _is_fragment(fm, parent.prof) or status != "distilled":
        plan.fail(2, fragment, f"is not a distilled Knowledge Fragment (distillation_status {status})")
        return
    led = read_ledger(doc.body)
    if not led.rows:
        plan.fail(2, fragment, "has no ledger in # Distillation")
        return
    want = {c["from_parent"] for c in items}
    base = inst.root / BASE_DIR
    lines = doc.body.split("\n")
    got: set = set()
    for row in led.rows:
        cells = table_cells(lines[row.line]) or []
        kind = re.sub(r"[*_`]", "", cells[1] if len(cells) > 1 else "").strip().lower()
        if kind not in CLOSING_KINDS:
            plan.fail(2, fragment, f"ledger row '{row.item}' has Kind '{kind}', not promote, conflict or stays")
        targets = [resolve_link(parent.root, doc, m.group(2)) for m in LINK_RE.finditer(row.concept)]
        mine = [bpath(parent.root, t) for t in targets if under(t, base)]
        got |= set(mine)
        if kind != "promote":
            continue
        cites: set = set()
        for t in targets:
            if under(t, parent.root) and not under(t, inst.root) and parent.doc(t) is not None:
                cites |= {str(s.get("resource")) for s in as_list(parent.fm_of(parent.doc(t)).get("sources"))
                          if isinstance(s, dict)}
        for m in mine:
            if m not in cites:
                plan.fail(3, fragment, f"ledger row '{row.item}' promotes {m} but links no parent concept whose "
                          "sources cite it")
    for m in sorted(want - got):
        plan.fail(2, fragment, f"no ledger row links {m}")
    for m in sorted(got - want):
        plan.fail(2, fragment, f"ledger links {m}, which is no concept of the instance's base/")


def plan_closing(inst: Bundle, parent: Bundle | None, fragment: str, carries: dict, by: str, actor: str,
                 at: str) -> Plan:
    plan = Plan()
    for b in blockers(inst, parent):
        plan.fail(1, b["path"], f"{b['code']}: {b['message']}")
    if plan.failures:
        return plan
    items = concepts(inst, parent)
    from_parent = {c["path"]: c["from_parent"] for c in items}
    check_fragment(inst, parent, fragment, items, plan)

    gen = f"{{ by: {actor}, at: {at} }}"
    used: set = set()
    question_writes: dict = {}
    for q in open_questions(inst):
        target = carries.get(q["path"])
        if target is None:
            plan.fail(4, q["path"], "an open question with no --carry: answer or drop it in the instance, or carry it up")
            continue
        used.add(q["path"])
        tdoc = parent.doc(parent.root / target.lstrip("/"))
        tfm = parent.fm_of(tdoc) if tdoc is not None else {}
        if tdoc is None or tfm.get("type") != "Open Question" or tfm.get("question_status") != "open":
            plan.fail(4, q["path"], f"carried to {target}, which is no open Open Question of the parent")
        elif from_parent[q["path"]] not in [str(x) for x in as_list(tfm.get("asked_in"))]:
            plan.fail(4, q["path"], f"carried to {target}, whose asked_in is not {from_parent[q['path']]}")
        else:
            path = inst.root / q["path"].lstrip("/")
            rel = Path(os.path.relpath(tdoc.path, inst.root)).as_posix()
            question_writes[path] = set_keys(path.read_text(encoding="utf-8"),
                                             {"question_status": "carried", "carried_to": rel, "generated": gen},
                                             {"carried_to": "question_status"})

    log = inst.conflict_log()
    plog = parent.conflict_log()
    carried_ids: dict = {}  # instance row id -> parent row id
    log_text = log.path.read_text(encoding="utf-8") if log is not None else ""
    log_lines = log_text.split("\n")
    rows = conflict_rows(log_text)
    prows = {r.id: r for r in conflict_rows(plog.path.read_text(encoding="utf-8"))} if plog is not None else {}
    plog_rel = Path(os.path.relpath(plog.path, inst.root)).as_posix() if plog is not None else ""
    for r in rows:
        if r.state not in OPEN_CONFLICT:
            continue
        target = carries.get(r.id)
        if target is None:
            plan.fail(4, r.id, f"an {r.state} conflict with no --carry: resolve or dismiss it in the instance, or "
                      "carry it up")
            continue
        used.add(r.id)
        pr = prows.get(target)
        links = [resolve_link(parent.root, plog, m.group(2)) for cell in (pr.get("source"), pr.get("description"))
                 for m in LINK_RE.finditer(cell)] if pr is not None else []
        if pr is None or pr.state != "open":
            plan.fail(4, r.id, f"carried to {target}, which is no open row of the parent's Conflict Log")
        elif not any(under(t, inst.root) for t in links):
            plan.fail(4, r.id, f"carried to {target}, whose Source and Description link nothing in the instance")
        elif not all(c in r.cols for c in ("resolution", "state", "decided")):
            plan.fail(4, r.id, "the instance's Conflict Log has no Resolution, State or Decided column")
        else:
            cells = list(r.cells)
            cells[r.cols["resolution"]] = f"carried up to {target} (`{plog_rel}`)"
            cells[r.cols["state"]] = "carried"
            cells[r.cols["decided"]] = by
            log_lines[r.line] = row_line(cells)
            carried_ids[r.id] = target
    for key in carries:
        if key not in used:
            plan.fail(4, key, "--carry names no open question nor open or proposed conflict of the instance")

    fragment_writes: dict = {}
    if carried_ids:
        after = {r.id: ("carried" if r.id in carried_ids else r.state) for r in rows}
        for d in inst.docs:
            fm = inst.fm_of(d)
            if not (d.rel.startswith(FRAGMENTS_DIR + "/") and _is_fragment(fm, inst.prof)
                    and fm.get("distillation_status") == "conflict"):
                continue
            mine = [r for r in rows if any(resolve_link(inst.root, log, m.group(2)) == d.path.resolve()
                                           for m in LINK_RE.finditer(r.get("source")))]
            if not any(r.id in carried_ids for r in mine) or any(after[r.id] in OPEN_CONFLICT for r in mine):
                continue
            text = d.path.read_text(encoding="utf-8")
            raw, _ = split_frontmatter(text)
            if not re.search(r"^distillation_status\s*:", raw or "", re.M):
                plan.fail(4, d.rel, "its distillation_status is written under a local name: release it by hand")
                continue
            text = set_keys(text, {"distillation_status": "distilled"})
            lines, start = text.split("\n"), body_start(text)
            for row in read_ledger("\n".join(lines[start:])).rows or []:
                cells = table_cells(lines[start + row.line]) or []
                m = OUTCOME_RE.match(cells[2].strip()) if len(cells) == 4 else None
                if m and m.group(1) in carried_ids:
                    cells[2] = f"carried up: {carried_ids[m.group(1)]} (`{plog_rel}`)"
                    lines[start + row.line] = row_line(cells)
            fragment_writes[d.path] = "\n".join(lines)

    if plan.failures:
        return plan
    plan.writes.update(question_writes)
    if carried_ids:
        plan.writes[log.path] = set_keys("\n".join(log_lines), {"generated": gen})
    plan.writes.update(fragment_writes)
    index = inst.root / "index.md"
    plan.writes[index] = set_keys(index.read_text(encoding="utf-8"), {"state": "closed", "closed_at": at},
                                  {"closed_at": "state"})
    return plan


def apply(args) -> int:
    inst = load_bundle(Path(args.instance).resolve())
    proot = parent_root(inst)
    parent = load_bundle(proot) if proot is not None and (proot / "index.md").is_file() else None
    try:
        carries = parse_carries(args.carry)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    plan = plan_closing(inst, parent, args.fragment, carries, args.by, args.actor, args.at)
    if plan.failures:
        for check, subject, message in plan.failures:
            print(f"FAIL check {check}: {subject}: {message}")
        print(f"{len(plan.failures)} failed check{'s' if len(plan.failures) != 1 else ''}: nothing written")
        return 1
    verb = "WOULD WRITE" if args.dry_run else "WROTE"
    for path, text in plan.writes.items():
        if not args.dry_run:
            path.write_text(text, encoding="utf-8")
        print(f"{verb} {os.path.relpath(path, inst.root)}")
    if args.dry_run:
        print("WOULD REGENERATE the indexes of the instance and of its parent")
        return 0
    from okf_index import main as index_main  # noqa: E402

    index_main([str(inst.root)])
    index_main([str(parent.root)])
    print(f"closed {args.instance} at {args.at}: write the Closing entry in its log.md, the Update entry in the "
          "parent's, then run okf_lint.py on the parent")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instance", help="path to the operational instance")
    ap.add_argument("--json", action="store_true", help="the report as JSON")
    ap.add_argument("--apply", action="store_true", help="check the approved closing and write it")
    ap.add_argument("--fragment", help="the closing fragment, as a parent bundle path (/fragments/<file>.md)")
    ap.add_argument("--by", help="the person who approved the closing (human:<id>)")
    ap.add_argument("--actor", help="the actor writing the closing, for generated")
    ap.add_argument("--carry", action="append", default=[], metavar="ITEM=PARENT_ITEM",
                    help="an open question (base/questions/<q>.md=/base/questions/<q>.md) or conflict (C-001=C-002) "
                         "carried up")
    ap.add_argument("--at", help="closed_at and generated.at, ISO 8601 with an offset (default: now)")
    ap.add_argument("--dry-run", action="store_true", help="with --apply: check and list the writes, writing nothing")
    args = ap.parse_args(argv)
    if not (Path(args.instance) / "index.md").is_file():
        print(f"ERROR: {args.instance} has no index.md: pass the instance's directory", file=sys.stderr)
        return 2
    if not args.apply:
        if args.fragment or args.by or args.actor or args.carry or args.at or args.dry_run:
            ap.error("--fragment, --by, --actor, --carry, --at and --dry-run go with --apply")
        rep = report(args.instance)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            print_report(rep)
        return 1 if rep["blockers"] else 0
    missing = [f"--{k}" for k in ("fragment", "by", "actor") if not getattr(args, k)]
    if missing:
        ap.error(f"--apply needs {', '.join(missing)}")
    if not (args.by.startswith("human:") and ACTOR_RE.match(args.by)):
        ap.error(f"--by {args.by}: the person who approved, human:<id>")
    if not ACTOR_RE.match(args.actor):
        ap.error(f"--actor {args.actor}: an actor (human:<id>, process:<id> or <tool>/<model>)")
    args.at = args.at or now_iso()
    if not is_iso(args.at):
        ap.error(f"--at {args.at}: ISO 8601 with an offset")
    return apply(args)


def print_report(rep: dict) -> None:
    print(f"{rep['instance']}: {rep['kind']} ({rep['state']}), parent {rep['parent']}")
    for b in rep["blockers"]:
        print(f"BLOCKER {b['code']:16} {b['path']}: {b['message']}")
    for c in rep["concepts"]:
        same = f" (the parent has {c['parent_same_path']})" if c["parent_same_path"] else ""
        print(f"CONCEPT {c['path']} [{c['type']}] {c['title']}{same}")
    for q in rep["questions"]:
        print(f"QUESTION {q['path']} (owner {q['owner']})")
    for c in rep["conflicts"]:
        print(f"CONFLICT {c['id']} ({c['state']}): {c['description']}")
    print("nothing blocks the closing" if not rep["blockers"] else f"{len(rep['blockers'])} blocker(s): not closable")


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_close.py --test)
# --------------------------------------------------------------------------
_REQ = "requests/req-0042"
_FRAGMENT = "/fragments/2026-11-09-closing-req-0042.md"
_QUESTION = "base/questions/who-approves-partial-refunds.md"
_APPLY = ["--apply", "--fragment", _FRAGMENT, "--carry", f"{_QUESTION}=/{_QUESTION}", "--carry", "C-001=C-002",
          "--by", "human:test", "--actor", "okf-builder/test", "--at", "2026-11-09T17:00:00Z"]
_EXPECTED_CONCEPTS = [
    {"path": "/base/domain/dual-approval.md", "type": "Term", "title": "Dual approval",
     "from_parent": "/requests/req-0042/base/domain/dual-approval.md", "parent_same_path": None},
    {"path": "/base/domain/refund-window.md", "type": "Term", "title": "Refund window",
     "from_parent": "/requests/req-0042/base/domain/refund-window.md",
     "parent_same_path": "/base/domain/refund-window.md"},
    {"path": "/" + _QUESTION, "type": "Open Question", "title": "Who approves partial refunds?",
     "from_parent": "/requests/req-0042/" + _QUESTION, "parent_same_path": "/" + _QUESTION},
    {"path": "/base/runbooks/refund-retry.md", "type": "Runbook", "title": "Refund retry",
     "from_parent": "/requests/req-0042/base/runbooks/refund-retry.md", "parent_same_path": None}]


def _fixture(tmp_path: Path) -> Path:
    import shutil

    import pytest

    src = next((p / "examples" / "fixtures" / "closing-instance" / "knowledge" for p in Path(__file__).resolve().parents
                if (p / "examples" / "fixtures" / "closing-instance" / "knowledge" / "index.md").is_file()), None)
    if src is None:
        pytest.skip("examples/fixtures/closing-instance not beside this script")
    shutil.copytree(src, tmp_path / "knowledge")
    return tmp_path / "knowledge"


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, (path, old)
    path.write_text(text.replace(old, new), encoding="utf-8")


def _hashes(root: Path) -> dict:
    import hashlib

    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _report(capsys, inst: Path) -> tuple[int, dict]:
    code = main([str(inst), "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_the_report_of_the_fixture_is_exact(tmp_path, capsys):
    inst = _fixture(tmp_path) / _REQ
    code, rep = _report(capsys, inst)
    assert code == 0
    assert rep == {"instance": str(inst), "parent": "../..", "kind": "Request", "state": "open", "blockers": [],
                   "concepts": _EXPECTED_CONCEPTS,
                   "questions": [{"path": "/" + _QUESTION, "owner": "human:maria"}],
                   "conflicts": [{"id": "C-001", "state": "open",
                                  "description": "Ana says the refund API returns 200 for a refund still pending; "
                                                 "Maria says finance reads every 200 as paid"}]}


def _blockers(capsys, inst: Path) -> list[dict]:
    code, rep = _report(capsys, inst)
    assert code == 1
    return [{"code": b["code"], "path": b["path"]} for b in rep["blockers"]]


def test_not_instance_without_kind_or_parent(tmp_path, capsys):
    k = _fixture(tmp_path)
    assert _blockers(capsys, k) == [{"code": "NOT_INSTANCE", "path": "index.md"}]
    _edit(k / _REQ / "index.md", "parent: ../..\n", "")
    assert _blockers(capsys, k / _REQ) == [{"code": "NOT_INSTANCE", "path": "index.md"}]


def test_already_closed(tmp_path, capsys):
    inst = _fixture(tmp_path) / _REQ
    _edit(inst / "index.md", "state: open\n", "state: closed\nclosed_at: 2026-11-08T10:00:00Z\n")
    assert _blockers(capsys, inst) == [{"code": "ALREADY_CLOSED", "path": "index.md"}]


def test_parent_closed(tmp_path, capsys):
    k = _fixture(tmp_path)
    _edit(k / "index.md", 'okf_profile: "knowledge/3.0"\n', 'okf_profile: "knowledge/3.0"\nstate: closed\n')
    assert _blockers(capsys, k / _REQ) == [{"code": "PARENT_CLOSED", "path": "../../index.md"}]


def test_child_open(tmp_path, capsys):
    inst = _fixture(tmp_path) / _REQ
    (inst / "requests" / "req-0043").mkdir(parents=True)
    (inst / "requests" / "req-0043" / "index.md").write_text(
        '---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\nkind: Request\nstate: open\nparent: ../..\n---\n',
        encoding="utf-8")
    assert _blockers(capsys, inst) == [{"code": "CHILD_OPEN", "path": "requests/req-0043/index.md"}]


def test_pending_fragment_aliases_resolved(tmp_path, capsys):
    inst = _fixture(tmp_path) / _REQ
    frag = inst / "fragments" / "2026-11-05-scoping-call.md"
    _edit(frag, "distillation_status: conflict\n", "distillation_status: pending\n")
    assert _blockers(capsys, inst) == [{"code": "PENDING_FRAGMENT", "path": "fragments/2026-11-05-scoping-call.md"}]
    _edit(tmp_path / "knowledge" / PROFILE_REL, "kinds:\n",
          "aliases:\n  values:\n    - { from: { ingerido: false }, to: { distillation_status: pending } }\nkinds:\n")
    _edit(frag, "distillation_status: pending\n", "ingerido: false\n")
    assert _blockers(capsys, inst) == [{"code": "PENDING_FRAGMENT", "path": "fragments/2026-11-05-scoping-call.md"}]


def test_apply_closes_the_fixture_and_lint_finds_nothing(tmp_path, capsys):
    from datetime import datetime, timezone

    from okf_lint import lint

    k = _fixture(tmp_path)
    inst = k / _REQ
    assert main([str(inst), *_APPLY]) == 0
    assert root_frontmatter(inst) == {"okf_version": "0.2", "okf_profile": "knowledge/3.0", "kind": "Request",
                                      "state": "closed", "parent": "../..",
                                      "closed_at": datetime(2026, 11, 9, 17, tzinfo=timezone.utc)}
    q = inst / _QUESTION
    raw, _ = split_frontmatter(q.read_text(encoding="utf-8"))
    assert "question_status: carried\ncarried_to: ../../base/questions/who-approves-partial-refunds.md\n" in raw
    assert "generated: { by: okf-builder/test, at: 2026-11-09T17:00:00Z }" in raw
    assert "| C-001 | [Scoping call](/fragments/2026-11-05-scoping-call.md) | Ana says the refund API returns 200 for a " \
           "refund still pending; Maria says finance reads every 200 as paid | sources disagree | carried up to C-002 " \
           "(`../../conflict-log.md`) | carried | human:test |" in (inst / "conflict-log.md").read_text(encoding="utf-8")
    frag = (inst / "fragments" / "2026-11-05-scoping-call.md").read_text(encoding="utf-8")
    assert "distillation_status: distilled\n" in frag
    assert "| Pending refunds | Conflict | carried up: C-002 (`../../conflict-log.md`) | [Conflict log](/conflict-log.md) |" \
           in frag
    rep = lint(k)[0]
    assert rep.items == []
    assert [(i["path"], i["kind"], i["state"]) for i in rep.instances] == [("requests/req-0042/", "Request", "closed")]
    capsys.readouterr()
    assert main([str(inst), "--json"]) == 1
    assert [b["code"] for b in json.loads(capsys.readouterr().out)["blockers"]] == ["ALREADY_CLOSED"]


def test_dry_run_writes_nothing(tmp_path):
    k = _fixture(tmp_path)
    before = _hashes(k)
    assert main([str(k / _REQ), *_APPLY, "--dry-run"]) == 0
    assert _hashes(k) == before


def _failed_apply(tmp_path, capsys, plant, argv=None) -> list[tuple[int, str]]:
    """Plants a defect, runs --apply, and returns the (check, subject) of each failure once nothing was written."""
    k = _fixture(tmp_path)
    plant(k)
    before = _hashes(k)
    inst = load_bundle(k / _REQ)
    proot = parent_root(inst)
    args = argv or _APPLY
    carries = parse_carries([args[i + 1] for i, a in enumerate(args) if a == "--carry"])
    plan = plan_closing(inst, load_bundle(proot), _FRAGMENT, carries, "human:test", "okf-builder/test",
                        "2026-11-09T17:00:00Z")
    assert main([str(k / _REQ), *args]) == 1
    assert _hashes(k) == before
    assert "nothing written" in capsys.readouterr().out
    return [(c, s) for c, s, _ in plan.failures]


def test_a_missing_ledger_row_fails_check_2(tmp_path, capsys):
    def plant(k):
        _edit(k / _FRAGMENT.lstrip("/"), "| Refund retry | stays | applied | [req-0042: Refund retry]"
              "(/requests/req-0042/base/runbooks/refund-retry.md) |\n", "")
    assert _failed_apply(tmp_path, capsys, plant) == [(2, _FRAGMENT)]


def test_a_closing_fragment_not_distilled_fails_check_2(tmp_path, capsys):
    for status in ("conflict", "pending"):
        def plant(k, status=status):
            _edit(k / _FRAGMENT.lstrip("/"), "distillation_status: distilled\n", f"distillation_status: {status}\n")
        assert _failed_apply(tmp_path / status, capsys, plant) == [(2, _FRAGMENT)]


def test_a_promoted_concept_without_its_source_fails_check_3(tmp_path, capsys):
    def plant(k):
        _edit(k / "base/domain/refund-window.md", "  - { id: req-0042, resource: /requests/req-0042/base/domain/"
              "refund-window.md, title: \"req-0042: Refund window\" }\n", "")
    assert _failed_apply(tmp_path, capsys, plant) == [(3, _FRAGMENT)]


def test_a_parent_question_not_asked_in_the_instance_fails_check_4(tmp_path, capsys):
    def plant(k):
        _edit(k / _QUESTION, "asked_in: /requests/req-0042/", "asked_in: /requests/req-0041/")
    assert _failed_apply(tmp_path, capsys, plant) == [(4, "/" + _QUESTION)]


def test_an_open_question_without_carry_fails_check_4(tmp_path, capsys):
    argv = _APPLY[:3] + _APPLY[5:]  # without --carry <question>
    assert argv.count("--carry") == 1
    assert _failed_apply(tmp_path, capsys, lambda k: None, argv) == [(4, "/" + _QUESTION)]


def test_a_parent_row_not_linking_the_instance_fails_check_4(tmp_path, capsys):
    def plant(k):
        _edit(k / "conflict-log.md", "Carried up from C-001 of [req-0042's conflict log](/requests/req-0042/"
              "conflict-log.md)", "Carried up from C-001 of req-0042")
    assert _failed_apply(tmp_path, capsys, plant) == [(4, "C-001")]


def test_a_pending_fragment_blocks_apply(tmp_path, capsys):
    def plant(k):
        _edit(k / _REQ / "fragments/2026-11-05-scoping-call.md", "distillation_status: conflict\n",
              "distillation_status: pending\n")
    assert _failed_apply(tmp_path, capsys, plant) == [(1, "fragments/2026-11-05-scoping-call.md")]


def test_a_fragment_with_a_conflict_still_open_blocks_and_is_not_rewritten(tmp_path, capsys):
    def plant(k):
        _edit(k / _REQ / "conflict-log.md", "| sources disagree | | open | — |\n",
              "| sources disagree | | open | — |\n| C-002 | [Scoping call](/fragments/2026-11-05-scoping-call.md) | "
              "a second one | sources disagree | | open | — |\n")
    assert _failed_apply(tmp_path, capsys, plant) == [(4, "C-002")]


def test_a_carry_naming_no_open_item_and_a_bad_carry(tmp_path, capsys):
    assert _failed_apply(tmp_path, capsys, lambda k: None, _APPLY + ["--carry", "C-009=C-002"]) == [(4, "C-009")]
    k = tmp_path / "knowledge"
    assert main([str(k / _REQ), *_APPLY[:-2], "--carry", "C-001", "--at", "2026-11-09T17:00:00Z"]) == 2
    assert parse_carries([f"/{_QUESTION}=/{_QUESTION}"]) == parse_carries([f"{_QUESTION}={_QUESTION}"])


def test_bad_arguments_exit_2(tmp_path, capsys):
    import pytest

    k = _fixture(tmp_path)
    assert main([str(tmp_path / "nowhere")]) == 2
    for argv in (["--apply"], [*_APPLY[:-2], "--at", "yesterday"], [*_APPLY, "--by", "okf-builder/test"],
                 ["--fragment", _FRAGMENT]):
        with pytest.raises(SystemExit) as e:
            main([str(k / _REQ), *argv])
        assert e.value.code == 2


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
