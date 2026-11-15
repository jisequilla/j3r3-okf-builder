#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_viewer.py — Build the Knowledge Viewer of a bundle (ADR-0042): a page and its data file, written outside the
bundle, which the agent publishes as a Claude artifact. A viewer setup, neither a knowledge projection nor a platform
package; no script publishes it and none writes verified (SDR-0022 decision 3).

Usage:
    uv run okf_viewer.py path/to/bundle --out DIR [--round NAME [--round-title TEXT] [--paths P ...]] [--force]
    uv run okf_viewer.py path/to/bundle --answers FILE|DIR [--since TIME] [--json]

- Writes DIR/index.html, the page template the plugin ships (okf-standard/viewer/index.html) byte for byte, and
  DIR/concepts.json, a snapshot of the bundle the page reads:
  {commit, dirty, built_at, round: {name, title, paths}, concepts: [...]}.
- Reads the bundle as okf-lint does (scan_bundle): the paths .okfignore matches, projections/ and nested bundles are
  left out, the nested bundles named on one NOTICE line. Each Markdown file with a frontmatter is one concept, but
  each index.md, log.md and the Conflict Log (by its type); fragments, project.md and base/profile.md included. A
  frontmatter that cannot be parsed (lint's BAD_YAML) is left out and named on one NOTICE line.
- Each concept: path (bundle path), type, title, description, status, decision_status, question_status,
  distillation_status, owner, generated_by, generated_at, verified_by, verified_at (the last entry when verified is
  a list), stale_after, supersedes, superseded_by, layer (base, fragments or root), frontmatter (the raw YAML between
  the '---' lines), body, and links: the bundle paths of the concepts its body links to, read with the link reader
  lint uses, in order of first appearance, with no external, broken or non-concept target. The keys are read with
  the aliases of the Domain Profile lint has in force resolved, also when that profile has findings (one NOTICE line
  says so); frontmatter stays as written.
- commit is the repository's HEAD and dirty says whether git reports a change under the bundle; outside git, commit
  is null and dirty false. built_at is now.
- The round: --round NAME with --paths gives those concepts (each must be one); with no --paths, or no --round, the
  round is every base/ concept in status draft that no person verified at its current generated.at, read as lint's
  VERIFIED_STALE reads it (human: actors, the latest by time). --round-title defaults to the name.
- Never overwrites an existing file unless given --force; prints `created <path>`, `rewritten <path>` (with --force)
  or `skipped (exists) <path>` for each file.
- Exit: 2, writing nothing, when the bundle has no index.md, --out is the bundle or inside it, --paths names no
  concept or is given without --round; 1, writing nothing, when lint reports SECRET_IN_BUNDLE (the data leaves the
  machine), each finding named by file and line, never by value; else 0.

--answers checks the answers the page stored against the bundle as it is now, and writes nothing: not the bundle,
not verified (SDR-0022 decision 3). It takes none of --out, --round, --round-title, --paths and --force.
- Input: a JSON file holding a list of answer objects, or a directory of `<doc_id>.json` files, one answer object
  each, as the platform's database export writes them. An answer: {path, commit, generated_at, choice (confirmed |
  not_confirmed), answered_at, by, page_built_at, round, comment?, commented_at?}, plus the store's `id` and
  `version` when the list carries them; in a directory, `id` defaults to the file name without `.json`.
- One row per answer, newest first by answered_at; an answer is listed when its answered_at or its commented_at is
  later than --since (the page keeps answered_at when a comment is added later). The path checks come first, then
  the version, then the choice:
  UNKNOWN         the path names no concept of the bundle (an index.md, a log.md, a file lint leaves out, none);
  NOT_VERIFIABLE  a fragment, the Conflict Log or a concept in status deprecated;
  STALE           generated_at is not the concept's current generated.at, whatever the choice: ask again;
  NOT_CONFIRMED   not_confirmed at the current version, with the comment verbatim ("" when none);
  ALREADY         confirmed at the current version, and a verified entry by a human: actor is at answered_at;
  APPLY           confirmed at the current version, not yet applied.
  Times compare as times, never as text. The keys are read with the aliases of the Domain Profile in force, as the
  build reads them. A concept at the root (project.md) or the Domain Profile is checked as a base/ concept is.
- --json prints the rows as a JSON list, each {row, path, id, version, choice, answered_at, by, generated_at,
  current_generated_at, comment, reason, answer}, `answer` the object as read; without it, one line per row.
  NOTICE lines go to stderr.
- Exit: 2 when an input cannot be read (no index.md; an answers path that is missing or not JSON; an answer that is
  no object, or lacks a path, a choice of the two, or a generated_at or answered_at read as a time; a --since that
  is no time), the message on stderr; else 0, whatever the rows say.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    BASE_DIR,
    FRAGMENTS_DIR,
    Scan,
    as_list,
    extract_links,
    now_iso,
    resolve_link,
    scan_bundle,
    split_frontmatter,
    to_dt,
)
from okf_lint import (  # noqa: E402
    Report,
    check_secrets,
    find_tree,
    last_human_verification,
    profile_structure,
    verified_stale,
)
from okf_profile import Resolved, concept_type, is_a, resolve_aliases  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent.parent / "viewer" / "index.html"
KEYS = ("type", "title", "description", "status", "decision_status", "question_status", "distillation_status",
        "owner", "stale_after", "supersedes", "superseded_by")
DEFAULT_ROUND = ("unverified", "Base concepts in draft, not verified at their current version")


def _text(v):
    """A frontmatter value as the page shows it: a timestamp as YAML wrote it (UTC as Z), a date as ISO, None kept."""
    if v is None or isinstance(v, (str, bool, int, float)):
        return v
    if isinstance(v, _dt.datetime):
        if v.tzinfo is not None and v.utcoffset() == _dt.timedelta(0):
            return v.replace(tzinfo=None).isoformat() + "Z"
        return v.isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    return str(v)


def _entry(v) -> dict:
    """generated or verified as one mapping: verified's last entry when it is a list."""
    if isinstance(v, list):
        v = v[-1] if v else None
    return v if isinstance(v, dict) else {}


def bundle_profile(root: Path, sc: Scan) -> tuple[Resolved | None, str | None]:
    """The Domain Profile lint has in force for the bundle (profile_structure, the tree's domain for an instance), and
    the NOTICE line to print when it has findings: lint keeps such a profile in force and reports them beside it, so
    the keys are still read through it. A profile whose loading raises leaves the keys as written, with its NOTICE."""
    tree = find_tree(root, Report())
    try:
        prof, findings, _ = profile_structure(root, sc.docs, tree.domain if tree is not None else None)
    except Exception as e:  # noqa: BLE001
        return None, f"NOTICE the Domain Profile cannot be loaded ({e}): every key is read as written"
    if findings:
        return prof, (f"NOTICE the Domain Profile in force has {len(findings)} finding(s), read as lint reads it: "
                      "see okf_lint.py --profiles")
    return prof, None


def git_state(root: Path) -> tuple[str | None, bool]:
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)

    head = git("rev-parse", "HEAD")
    if head.returncode != 0:
        return None, False
    return head.stdout.strip(), bool(git("status", "--porcelain", "--", ".").stdout.strip())


def layer_of(rel: str) -> str:
    for layer in (BASE_DIR, FRAGMENTS_DIR):
        if rel.startswith(layer + "/"):
            return layer
    return "root"


def body_of(text: str) -> str:
    """The body as written: what follows the frontmatter's closing '---' line, its trailing newline kept and the
    blank lines that open it dropped."""
    lines = text.splitlines(keepends=True)
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    return "".join(lines[end + 1:]).lstrip("\n")


def build(root: Path, sc: Scan, prof: Resolved | None) -> tuple[list[dict], list[str], list[str]]:
    """The concepts of the bundle, sorted by path; the bundle paths of the default round; the files whose frontmatter
    cannot be parsed (lint's BAD_YAML), which are left out."""
    docs, bad = [], []
    for d in sc.docs:
        if d.path.name in ("index.md", "log.md") or not d.has_fm_block:
            continue
        if not isinstance(d.frontmatter, dict):
            bad.append(d.rel)
            continue
        fm = resolve_aliases(prof, d.frontmatter) if prof is not None else d.frontmatter
        if concept_type(None, fm) == "Conflict Log":
            continue
        docs.append((d, fm))
    concepts = {d.path.resolve(): "/" + d.rel for d, _ in docs}
    out, round_paths = [], []
    for d, fm in sorted(docs, key=lambda x: x[0].rel):
        text = d.path.read_text(encoding="utf-8")
        raw, body = split_frontmatter(text)
        links: list[str] = []
        for target in extract_links(body):
            p = resolve_link(root, d, target)
            bp = concepts.get(p) if p is not None else None
            if bp and bp not in links:
                links.append(bp)
        gen, ver = _entry(fm.get("generated")), _entry(fm.get("verified"))
        c = {"path": "/" + d.rel, **{k: _text(fm.get(k)) for k in KEYS},
             "generated_by": _text(gen.get("by")), "generated_at": _text(gen.get("at")),
             "verified_by": _text(ver.get("by")), "verified_at": _text(ver.get("at")),
             "layer": layer_of(d.rel), "frontmatter": raw, "body": body_of(text), "links": links}
        out.append(c)
        if unverified(c, fm):
            round_paths.append(c["path"])
    return out, round_paths, bad


def unverified(c: dict, fm: dict) -> bool:
    """In the default round: a base/ concept in status draft that no person verified at its current generated.at, read
    as VERIFIED_STALE reads it (human: actors only, the latest by time)."""
    return (c["layer"] == BASE_DIR and c["status"] == "draft"
            and (last_human_verification(fm) is None or verified_stale(fm) is not None))


def write(path: Path, content: bytes, force: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return f"skipped (exists) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return f"{'rewritten' if existed else 'created'} {path}"


CHOICES = ("confirmed", "not_confirmed")


def read_answers(src: Path) -> list[tuple[dict, dict]]:
    """The answers of a JSON list file or of a directory of <doc_id>.json files, each as (the answer as read, its id
    and version); ValueError naming what cannot be read."""
    def load(f: Path):
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"{f} cannot be read as JSON ({e})") from None

    if src.is_dir():
        items = [(str(f), load(f), f.stem) for f in sorted(src.glob("*.json"))]
    elif src.is_file():
        data = load(src)
        if not isinstance(data, list):
            raise ValueError(f"{src} holds no list of answers")
        items = [(f"{src}, answer {n + 1}", a, None) for n, a in enumerate(data)]
    else:
        raise ValueError(f"{src}: no such file or directory")
    out = []
    for where, a, stem in items:
        if not isinstance(a, dict):
            raise ValueError(f"{where} is no answer object")
        if not isinstance(a.get("path"), str) or not a["path"].strip("/"):
            raise ValueError(f"{where} has no path")
        if a.get("choice") not in CHOICES:
            raise ValueError(f"{where} has choice {a.get('choice')!r}, not one of {', '.join(CHOICES)}")
        for k in ("generated_at", "answered_at"):
            if to_dt(a.get(k)) is None:
                raise ValueError(f"{where} has a {k} that cannot be read as a time: {a.get(k)!r}")
        out.append((a, {"id": a.get("id", stem), "version": a.get("version")}))
    return out


def _is(prof: Resolved | None, t, base: str) -> bool:
    """t is base, or a local type of the profile in force that extends it."""
    return isinstance(t, str) and (t == base or (prof is not None and is_a(prof, t, base)))


def classify(rel: str | None, fm: dict | None, answer: dict, prof: Resolved | None) -> tuple[str, str]:
    """The row of one answer and its reason, against the concept at rel (None when the path names no concept) and
    its frontmatter with the aliases resolved: the path checks, then the version, then the choice."""
    if rel is None or fm is None:
        return "UNKNOWN", "the path names no concept of the bundle"
    t = concept_type(None, fm)
    if rel.startswith(FRAGMENTS_DIR + "/") or _is(prof, t, "Knowledge Fragment"):
        return "NOT_VERIFIABLE", "a fragment is never verified"
    if _is(prof, t, "Conflict Log"):
        return "NOT_VERIFIABLE", "the Conflict Log is never verified"
    if fm.get("status") == "deprecated":
        return "NOT_VERIFIABLE", "a deprecated concept is not verified"
    current = to_dt(_entry(fm.get("generated")).get("at"))
    if current is None or current != to_dt(answer["generated_at"]):
        return "STALE", "the concept's generated.at changed since the page was built: ask again"
    if answer["choice"] == "not_confirmed":
        return "NOT_CONFIRMED", "not confirmed: propose what the comment asks, never apply it unasked"
    at = to_dt(answer["answered_at"])
    if any(isinstance(v, dict) and str(v.get("by") or "").startswith("human:") and to_dt(v.get("at")) == at
           for v in as_list(fm.get("verified"))):
        return "ALREADY", "a person's verified entry is already at answered_at"
    return "APPLY", "confirmed at the current version"


def check_answers(sc: Scan, prof: Resolved | None, answers: list[tuple[dict, dict]], since) -> list[dict]:
    """One row per answer whose answered_at or commented_at is later than since (every answer when None), newest
    first by answered_at."""
    docs = {"/" + d.rel: d for d in sc.docs
            if d.path.name not in ("index.md", "log.md") and d.has_fm_block and isinstance(d.frontmatter, dict)}
    rows = []
    for a, ident in answers:
        if since is not None and not any(t is not None and t > since
                                         for t in (to_dt(a["answered_at"]), to_dt(a.get("commented_at")))):
            continue
        path = "/" + a["path"].lstrip("/")
        d = docs.get(path)
        fm = None if d is None else resolve_aliases(prof, d.frontmatter) if prof is not None else d.frontmatter
        row, reason = classify(d.rel if d is not None else None, fm, a, prof)
        comment = a.get("comment")
        rows.append({"row": row, "path": path, **ident, "choice": a["choice"], "answered_at": _text(a["answered_at"]),
                     "by": a.get("by"), "generated_at": _text(a["generated_at"]),
                     "current_generated_at": _text(_entry(fm.get("generated")).get("at")) if fm else None,
                     "comment": "" if comment is None else comment, "reason": reason, "answer": a})
    rows.sort(key=lambda r: to_dt(r["answered_at"]), reverse=True)
    return rows


def row_line(r: dict) -> str:
    """One row as one line."""
    line = f"{r['row']} {r['path']} answered_at {r['answered_at']} by {r['by']} (id {r['id']}, version {r['version']})"
    if r["row"] == "STALE":
        return f"{line}: generated_at {r['generated_at']} is not the current {r['current_generated_at']}, ask again"
    if r["row"] == "NOT_CONFIRMED":
        return f"{line}: comment {json.dumps(r['comment'], ensure_ascii=False)}"
    if r["row"] in ("UNKNOWN", "NOT_VERIFIABLE"):
        return f"{line}: {r['reason']}"
    return line


def answers_mode(root: Path, src: Path, since_arg: str | None, as_json: bool, fail) -> int:
    """--answers: the rows of the stored answers against the bundle as it is now; the bundle is only read."""
    if not (root / "index.md").is_file():
        return fail(f"{root} is not an OKF bundle (no index.md)")
    since = None
    if since_arg is not None:
        since = to_dt(since_arg)
        if since is None:
            return fail(f"--since {since_arg!r} is not an ISO 8601 time")
    try:
        answers = read_answers(src)
    except ValueError as e:
        return fail(str(e))
    sc = scan_bundle(root)
    prof, notice = bundle_profile(root, sc)
    if notice:
        sys.stderr.write(notice + "\n")
    rows = check_answers(sc, prof, answers, since)
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            print(row_line(r))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="bundle root, the directory that holds index.md")
    ap.add_argument("--out", help="output directory, outside the bundle: builds the page")
    ap.add_argument("--round", help="name of the review round")
    ap.add_argument("--round-title", help="title of the review round (default: its name)")
    ap.add_argument("--paths", nargs="+", help="bundle paths of the round's concepts (with --round)")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--answers", help="the page's stored answers, a JSON list file or a directory of <doc_id>.json "
                    "files: checks them against the bundle and writes nothing")
    ap.add_argument("--since", help="with --answers: only the answers later than this time")
    ap.add_argument("--json", action="store_true", help="with --answers: the rows as a JSON list")
    args = ap.parse_args(argv)

    def fail(msg: str, code: int = 2) -> int:
        sys.stderr.write(f"okf_viewer: {msg}; nothing written\n")
        return code

    root = Path(args.bundle).resolve()
    if args.answers is not None:
        build_flags = [f for f, v in (("--out", args.out), ("--round", args.round), ("--round-title", args.round_title),
                                      ("--paths", args.paths), ("--force", args.force)) if v]
        if build_flags:
            return fail(f"--answers checks stored answers and builds nothing: it takes no {', '.join(build_flags)}")
        return answers_mode(root, Path(args.answers), args.since, args.json, fail)
    if args.out is None:
        return fail("give --out DIR to build the page, or --answers to check stored answers")
    if args.since is not None or args.json:
        return fail("--since and --json go with --answers")
    out = Path(args.out).resolve()
    if not (root / "index.md").is_file():
        return fail(f"{root} is not an OKF bundle (no index.md)")
    if out == root or root in out.parents:
        return fail(f"--out {out} is inside the bundle {root}: the page is written outside it")
    if args.paths and not args.round:
        return fail("--paths needs --round")
    sc = scan_bundle(root)
    rep = Report()
    check_secrets(sc.docs, rep)
    leaks = [i for i in rep.items if i["code"] == "SECRET_IN_BUNDLE"]
    if leaks:
        for i in leaks:
            sys.stderr.write(f"okf_viewer: SECRET_IN_BUNDLE {i['path']}: {i['message']}\n")
        return fail("the page's data leaves the machine, so a bundle lint finds a credential in is not built", 1)
    prof, notice = bundle_profile(root, sc)
    concepts, default_round, bad = build(root, sc, prof)
    paths = {c["path"] for c in concepts}
    if args.round and args.paths:
        missing = [p for p in args.paths if p not in paths]
        if missing:
            return fail(f"--paths names no concept of the bundle: {', '.join(missing)}")
        round_paths = list(args.paths)
    else:
        round_paths = default_round
    name, title = (args.round, args.round_title or args.round) if args.round else DEFAULT_ROUND
    commit, dirty = git_state(root)
    data = {"commit": commit, "dirty": dirty, "built_at": now_iso(),
            "round": {"name": name, "title": title, "paths": round_paths}, "concepts": concepts}
    if notice:
        print(notice)
    if sc.nested:
        print(f"NOTICE nested bundles left out: {', '.join(sc.nested)}")
    if bad:
        print(f"NOTICE frontmatter that cannot be parsed (BAD_YAML), left out: {', '.join(bad)}")
    print(write(out / "index.html", TEMPLATE.read_bytes(), args.force))
    print(write(out / "concepts.json", (json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode(), args.force))
    print(f"{len(concepts)} concepts, commit {commit or '(not in git)'}{' (dirty)' if dirty else ''}, "
          f"round {name}: {len(round_paths)}")
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_viewer.py --test): each builds a temporary bundle
# --------------------------------------------------------------------------
_ROOT = '---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n---\n\n# K\n'


def _concept(type_: str, title: str, extra: str = "", body: str = "") -> str:
    return (f"---\ntype: {type_}\ntitle: {title}\ndescription: d\nstatus: draft\n{extra}"
            f"generated: {{ by: human:a, at: 2026-11-01T10:00:00Z }}\n---\n\n{body}")


def _bundle(tmp_path: Path) -> Path:
    b = tmp_path / "knowledge"
    (b / "base" / "terms").mkdir(parents=True)
    (b / "fragments").mkdir()
    (b / "index.md").write_text(_ROOT, encoding="utf-8")
    (b / "log.md").write_text("# Bundle history\n", encoding="utf-8")
    (b / "project.md").write_text(_concept("Project", "P", body="# Purpose\n\nSee [a](/base/terms/a.md).\n"),
                                  encoding="utf-8")
    (b / "conflict-log.md").write_text(_concept("Conflict Log", "Conflicts"), encoding="utf-8")
    (b / "base" / "index.md").write_text("# base\n", encoding="utf-8")
    (b / "base" / "terms" / "index.md").write_text("# terms\n", encoding="utf-8")
    (b / "base" / "terms" / "a.md").write_text(_concept(
        "Term", "A", body="[b](b.md), [b again](/base/terms/b.md#x), [site](https://example.com/x.md), "
        "[gone](missing.md), [index](index.md), [self](#top), ![img](/project.md)\n"), encoding="utf-8")
    (b / "base" / "terms" / "b.md").write_text(_concept(
        "Term", "B", "verified: [{ by: human:a, at: 2026-11-02T10:00:00Z }, { by: human:c, at: 2026-11-03T10:00:00Z }]\n"),
        encoding="utf-8")
    (b / "fragments" / "index.md").write_text("# fragments\n", encoding="utf-8")
    (b / "fragments" / "2026-11-01-m.md").write_text(_concept(
        "Knowledge Fragment", "M", "distillation_status: pending\n", "# Record\n\nx\n"), encoding="utf-8")
    return b


def _run(b: Path, out: Path, *extra: str) -> int:
    return main([str(b), "--out", str(out), *extra])


def _data(out: Path) -> dict:
    return json.loads((out / "concepts.json").read_text(encoding="utf-8"))


def _by_path(out: Path) -> dict:
    return {c["path"]: c for c in _data(out)["concepts"]}


def test_builds_the_page_and_one_concept_per_file_lint_reads(tmp_path, capsys):
    b = _bundle(tmp_path)
    out = tmp_path / "viewer"
    assert _run(b, out) == 0
    assert (out / "index.html").read_bytes() == TEMPLATE.read_bytes()
    expected = sorted("/" + d.rel for d in scan_bundle(b).docs if d.path.name not in ("index.md", "log.md")
                      and concept_type(None, d.frontmatter) != "Conflict Log")
    assert [c["path"] for c in _data(out)["concepts"]] == expected
    c = _by_path(out)
    assert (c["/project.md"]["layer"], c["/base/terms/a.md"]["layer"], c["/fragments/2026-11-01-m.md"]["layer"]) == (
        "root", "base", "fragments")
    assert c["/project.md"]["body"] == "# Purpose\n\nSee [a](/base/terms/a.md).\n"
    assert c["/fragments/2026-11-01-m.md"]["distillation_status"] == "pending"
    assert c["/base/terms/a.md"]["generated_at"] == "2026-11-01T10:00:00Z"


def test_links_hold_concept_paths_only(tmp_path, capsys):
    b = _bundle(tmp_path)
    assert _run(b, tmp_path / "v") == 0
    c = _by_path(tmp_path / "v")
    assert c["/base/terms/a.md"]["links"] == ["/base/terms/b.md", "/project.md"]
    assert c["/project.md"]["links"] == ["/base/terms/a.md"]


def test_verified_as_a_list_gives_its_last_entry(tmp_path, capsys):
    b = _bundle(tmp_path)
    assert _run(b, tmp_path / "v") == 0
    c = _by_path(tmp_path / "v")["/base/terms/b.md"]
    assert (c["verified_by"], c["verified_at"]) == ("human:c", "2026-11-03T10:00:00Z")


def test_the_default_round_is_every_base_draft_not_verified_at_its_version(tmp_path, capsys):
    b = _bundle(tmp_path)
    assert _run(b, tmp_path / "v") == 0
    assert _data(tmp_path / "v")["round"] == {"name": DEFAULT_ROUND[0], "title": DEFAULT_ROUND[1],
                                               "paths": ["/base/terms/a.md"]}
    assert _run(b, tmp_path / "w", "--round", "r1", "--round-title", "Round one", "--paths", "/project.md") == 0
    assert _data(tmp_path / "w")["round"] == {"name": "r1", "title": "Round one", "paths": ["/project.md"]}
    assert _run(b, tmp_path / "x", "--round", "r1", "--paths", "/nope.md") == 2
    assert _run(b, tmp_path / "x", "--paths", "/project.md") == 2
    assert not (tmp_path / "x").exists()


def _base_term(b: Path, name: str, generated_at: str, verified: str) -> None:
    (b / "base" / "terms" / f"{name}.md").write_text(
        f"---\ntype: Term\ntitle: {name}\ndescription: d\nstatus: draft\n"
        f"generated: {{ by: human:a, at: {generated_at} }}\nverified: {verified}\n---\n\nx\n", encoding="utf-8")


def test_the_default_round_reads_verification_times_as_lint_does(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base" / "terms" / "b.md").unlink()
    one = "[{ by: human:a, at: 2026-11-01T10:30:00Z }]"
    _base_term(b, "before", "2026-11-01T12:00:00+02:00", one)
    _base_term(b, "after", "2026-11-01T09:00:00-03:00", one)
    _base_term(b, "machine", "2026-11-01T12:00:00Z",
               "[{ by: human:a, at: 2026-11-01T11:00:00Z }, { by: okf-builder/m, at: 2026-11-01T13:00:00Z }]")
    _base_term(b, "early", "2026-11-01T12:00:00Z",
               "[{ by: human:a, at: 2026-11-01T13:00:00Z }, { by: human:c, at: 2026-11-01T09:00:00Z }]")
    assert _run(b, tmp_path / "v") == 0
    assert _data(tmp_path / "v")["round"]["paths"] == [
        "/base/terms/a.md", "/base/terms/after.md", "/base/terms/machine.md"]


def test_an_aliased_bundle_whose_profile_has_a_finding_still_resolves_its_aliases(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base" / "profile.md").write_text(
        "---\ntype: Domain Profile\ntitle: Profile\ndescription: d\n"
        "aliases:\n  fields: { tipo: type }\n  types: { Termino: Term, Registro: Conflict Log }\n"
        "types:\n  Rara: { extends: Nope, description: d }\n"
        "generated: { by: human:a, at: 2026-11-01T10:00:00Z }\n---\n\n# What this bundle holds\n\nx\n",
        encoding="utf-8")
    (b / "conflict-log.md").write_text(
        "---\ntipo: Registro\ntitle: Conflicts\ndescription: d\nstatus: draft\n"
        "generated: { by: human:a, at: 2026-11-01T10:00:00Z }\n---\n\nx\n", encoding="utf-8")
    (b / "base" / "terms" / "c.md").write_text(
        "---\ntipo: Termino\ntitle: C\ndescription: d\nstatus: draft\n"
        "generated: { by: human:a, at: 2026-11-01T10:00:00Z }\n---\n\nx\n", encoding="utf-8")
    sc = scan_bundle(b)
    assert profile_structure(b, sc.docs)[1], "the planted profile has no finding"
    capsys.readouterr()
    assert _run(b, tmp_path / "v") == 0
    out = capsys.readouterr().out
    assert any(x.startswith("NOTICE the Domain Profile in force has ") for x in out.splitlines())
    c = _by_path(tmp_path / "v")
    assert c["/base/terms/c.md"]["type"] == "Term" and "/conflict-log.md" not in c


def test_a_frontmatter_that_cannot_be_parsed_is_named_on_a_notice(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base" / "terms" / "broken.md").write_text("---\ntitle: [unclosed\n---\n\nx\n", encoding="utf-8")
    capsys.readouterr()
    assert _run(b, tmp_path / "v") == 0
    assert "NOTICE frontmatter that cannot be parsed (BAD_YAML), left out: base/terms/broken.md" in (
        capsys.readouterr().out.splitlines())
    assert "/base/terms/broken.md" not in _by_path(tmp_path / "v")


def test_ignored_paths_and_nested_bundles_are_left_out(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / ".okfignore").write_text("base/drafts/\n", encoding="utf-8")
    (b / "base" / "drafts").mkdir()
    (b / "base" / "drafts" / "d.md").write_text(_concept("Term", "D"), encoding="utf-8")
    (b / "nested").mkdir()
    (b / "nested" / "index.md").write_text(_ROOT, encoding="utf-8")
    (b / "nested" / "x.md").write_text(_concept("Term", "X"), encoding="utf-8")
    capsys.readouterr()
    assert _run(b, tmp_path / "v") == 0
    assert "NOTICE nested bundles left out: nested/" in capsys.readouterr().out.splitlines()
    paths = set(_by_path(tmp_path / "v"))
    assert not {"/base/drafts/d.md", "/nested/x.md", "/nested/index.md"} & paths


def test_an_aliased_type_key_is_read_as_the_type_while_frontmatter_stays_raw(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base" / "profile.md").write_text(
        "---\ntype: Domain Profile\ntitle: Profile\ndescription: d\n"
        "aliases:\n  fields: { tipo: type }\n  types: { Termino: Term }\n"
        "generated: { by: human:a, at: 2026-11-01T10:00:00Z }\n---\n\n# What this bundle holds\n\nx\n",
        encoding="utf-8")
    (b / "base" / "terms" / "c.md").write_text(
        "---\ntipo: Termino\ntitle: C\ndescription: d\nstatus: draft\n"
        "generated: { by: human:a, at: 2026-11-01T10:00:00Z }\n---\n\nx\n", encoding="utf-8")
    assert _run(b, tmp_path / "v") == 0
    c = _by_path(tmp_path / "v")["/base/terms/c.md"]
    assert c["type"] == "Term"
    assert c["frontmatter"].startswith("tipo: Termino\n")


def test_out_inside_the_bundle_is_refused(tmp_path, capsys):
    b = _bundle(tmp_path)
    for out in (b, b / "viewer"):
        assert _run(b, out) == 2
    assert not (b / "viewer").exists() and not (b / "concepts.json").exists()


def test_an_existing_file_is_kept_without_force(tmp_path, capsys):
    b = _bundle(tmp_path)
    out = tmp_path / "v"
    out.mkdir()
    (out / "concepts.json").write_text("old\n", encoding="utf-8")
    capsys.readouterr()
    assert _run(b, out) == 0
    lines = capsys.readouterr().out.splitlines()
    assert f"skipped (exists) {out / 'concepts.json'}" in lines and f"created {out / 'index.html'}" in lines
    assert (out / "concepts.json").read_text(encoding="utf-8") == "old\n"
    assert _run(b, out, "--force") == 0
    assert f"rewritten {out / 'concepts.json'}" in capsys.readouterr().out.splitlines()
    assert _data(out)["concepts"]


def test_a_bundle_outside_git_has_no_commit(tmp_path, capsys):
    b = _bundle(tmp_path)
    if git_state(b)[0] is not None:
        import pytest

        pytest.skip("the temporary directory is inside a git repository")
    assert _run(b, tmp_path / "v") == 0
    assert (_data(tmp_path / "v")["commit"], _data(tmp_path / "v")["dirty"]) == (None, False)


def test_a_bundle_in_git_names_its_commit_and_dirt(tmp_path, capsys):
    b = _bundle(tmp_path)
    git = ["git", "-C", str(b), "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "x"], check=True)
    head = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert _run(b, tmp_path / "v") == 0
    assert (_data(tmp_path / "v")["commit"], _data(tmp_path / "v")["dirty"]) == (head, False)
    (b / "base" / "terms" / "a.md").write_text(_concept("Term", "A2"), encoding="utf-8")
    assert _run(b, tmp_path / "w") == 0
    assert _data(tmp_path / "w")["dirty"] is True


def test_a_planted_credential_is_refused_without_printing_it(tmp_path, capsys):
    b = _bundle(tmp_path)
    secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    (b / "base" / "terms" / "leak.md").write_text(_concept("Term", "Leak", body=f"token: {secret}\n"), encoding="utf-8")
    capsys.readouterr()
    assert _run(b, tmp_path / "v") == 1
    out, err = capsys.readouterr()
    assert "SECRET_IN_BUNDLE base/terms/leak.md: line" in err
    assert secret not in out + err
    assert not (tmp_path / "v").exists()


def _answer(path: str, generated_at: str, answered_at: str, choice: str = "confirmed", **extra) -> dict:
    return {"path": path, "commit": "c0ffee", "generated_at": generated_at, "choice": choice, "answered_at": answered_at,
            "by": "u_test", "page_built_at": "2026-11-01T09:00:00Z", "round": None, **extra}


def _tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _answers_run(capsys, b: Path, answers, tmp_path: Path, *extra: str) -> tuple[int, list[dict], str]:
    src = tmp_path / "answers.json"
    src.write_text(json.dumps(answers), encoding="utf-8")
    capsys.readouterr()
    code = main([str(b), "--answers", str(src), "--json", *extra])
    out, err = capsys.readouterr()
    return code, (json.loads(out) if code == 0 else []), err


GEN = "2026-11-01T10:00:00Z"


def test_answers_give_one_row_of_each_kind_newest_first_and_leave_the_bundle_as_it_was(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base" / "terms" / "c.md").write_text(_concept("Term", "C").replace(GEN, "2026-11-05T10:00:00Z"),
                                               encoding="utf-8")
    (b / "base" / "terms" / "d.md").write_text(_concept("Term", "D"), encoding="utf-8")
    answers = [
        _answer("/base/terms/a.md", "2026-11-01T12:00:00+02:00", "2026-11-10T10:00:00Z", id="base~terms~a.md",
                version=3),
        _answer("/base/terms/c.md", GEN, "2026-11-09T10:00:00Z", "not_confirmed"),
        _answer("/base/terms/d.md", GEN, "2026-11-08T10:00:00Z", "not_confirmed", comment="Say *why*.\n\"Two\" lines"),
        _answer("/base/terms/missing.md", GEN, "2026-11-07T10:00:00Z"),
        _answer("/fragments/2026-11-01-m.md", GEN, "2026-11-06T10:00:00Z"),
        _answer("/base/terms/b.md", GEN, "2026-11-02T11:00:00+01:00"),
        _answer("/base/terms/d.md", GEN, "2026-10-31T10:00:00Z"),
        _answer("/base/terms/d.md", GEN, "2026-11-01T00:00:00Z"),
    ]
    before = _tree(b)
    code, rows, _ = _answers_run(capsys, b, answers, tmp_path, "--since", "2026-11-01T00:00:00Z")
    assert code == 0 and _tree(b) == before
    assert [(r["row"], r["path"]) for r in rows] == [
        ("APPLY", "/base/terms/a.md"), ("STALE", "/base/terms/c.md"), ("NOT_CONFIRMED", "/base/terms/d.md"),
        ("UNKNOWN", "/base/terms/missing.md"), ("NOT_VERIFIABLE", "/fragments/2026-11-01-m.md"),
        ("ALREADY", "/base/terms/b.md")]
    assert (rows[0]["id"], rows[0]["version"]) == ("base~terms~a.md", 3)
    assert rows[1]["current_generated_at"] == "2026-11-05T10:00:00Z"
    assert rows[2]["comment"] == "Say *why*.\n\"Two\" lines" and rows[2]["answer"] == answers[2]
    code, rows, _ = _answers_run(capsys, b, answers, tmp_path)
    assert len(rows) == 8 and rows[-1]["answered_at"] == "2026-10-31T10:00:00Z"
    assert _tree(b) == before


def test_since_lists_an_older_answer_whose_comment_came_after_it(tmp_path, capsys):
    b = _bundle(tmp_path)
    answers = [
        _answer("/base/terms/a.md", GEN, "2026-10-30T10:00:00Z", "not_confirmed", comment="Name the *owner*.\nTwo lines",
                commented_at="2026-11-03T10:00:00+01:00"),
        _answer("/base/terms/b.md", GEN, "2026-10-30T10:00:00Z", "not_confirmed", comment="old",
                commented_at="2026-11-01T01:00:00+01:00"),
    ]
    code, rows, _ = _answers_run(capsys, b, answers, tmp_path, "--since", "2026-11-01T00:00:00Z")
    assert code == 0
    assert [(r["row"], r["path"], r["comment"]) for r in rows] == [
        ("NOT_CONFIRMED", "/base/terms/a.md", "Name the *owner*.\nTwo lines")]


def test_the_conflict_log_a_deprecated_concept_and_an_index_are_never_applied(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base" / "terms" / "old.md").write_text(_concept("Term", "Old").replace("status: draft", "status: deprecated"),
                                                 encoding="utf-8")
    answers = [_answer("/conflict-log.md", GEN, "2026-11-10T10:00:00Z"),
               _answer("base/terms/old.md", "2026-01-01T00:00:00Z", "2026-11-09T10:00:00Z"),
               _answer("/base/terms/index.md", GEN, "2026-11-08T10:00:00Z"),
               _answer("/project.md", GEN, "2026-11-07T10:00:00Z", "not_confirmed")]
    code, rows, _ = _answers_run(capsys, b, answers, tmp_path)
    assert code == 0
    assert [(r["row"], r["path"]) for r in rows] == [
        ("NOT_VERIFIABLE", "/conflict-log.md"), ("NOT_VERIFIABLE", "/base/terms/old.md"),
        ("UNKNOWN", "/base/terms/index.md"), ("NOT_CONFIRMED", "/project.md")]
    assert rows[3]["comment"] == ""


def test_an_aliased_bundle_is_read_as_lint_reads_it(tmp_path, capsys):
    b = _bundle(tmp_path)
    (b / "base" / "profile.md").write_text(
        "---\ntype: Domain Profile\ntitle: Profile\ndescription: d\n"
        "aliases:\n  fields: { tipo: type, hecho: generated, revisado: verified, estado: status }\n"
        "  types: { Termino: Term, Registro: Conflict Log, Acta: Knowledge Fragment }\n"
        "generated: { by: human:a, at: 2026-11-01T10:00:00Z }\n---\n\n# What this bundle holds\n\nx\n",
        encoding="utf-8")
    (b / "conflict-log.md").write_text(
        "---\ntipo: Registro\ntitle: Conflicts\ndescription: d\nestado: draft\n"
        f"hecho: {{ by: human:a, at: {GEN} }}\n---\n\nx\n", encoding="utf-8")

    def term(name: str, extra: str = "") -> None:
        (b / "base" / "terms" / f"{name}.md").write_text(
            f"---\ntipo: Termino\ntitle: {name}\ndescription: d\nestado: draft\n"
            f"hecho: {{ by: human:a, at: 2026-11-04T10:00:00Z }}\n{extra}---\n\nx\n", encoding="utf-8")

    term("new")
    term("seen", "revisado: [{ by: human:a, at: 2026-11-05T10:00:00Z }]\n")
    term("gone", "")
    (b / "base" / "terms" / "gone.md").write_text(
        (b / "base" / "terms" / "gone.md").read_text(encoding="utf-8").replace("estado: draft", "estado: deprecated"),
        encoding="utf-8")
    (b / "base" / "acta.md").write_text(
        f"---\ntipo: Acta\ntitle: A\ndescription: d\nhecho: {{ by: human:a, at: {GEN} }}\n---\n\nx\n",
        encoding="utf-8")
    at = "2026-11-04T10:00:00Z"
    answers = [_answer("/base/terms/new.md", at, "2026-11-10T10:00:00Z"),
               _answer("/base/terms/seen.md", at, "2026-11-05T10:00:00Z"),
               _answer("/base/terms/gone.md", at, "2026-11-04T12:00:00Z"),
               _answer("/conflict-log.md", GEN, "2026-11-04T11:00:00Z"),
               _answer("/base/acta.md", GEN, "2026-11-03T11:00:00Z")]
    code, rows, _ = _answers_run(capsys, b, answers, tmp_path)
    assert code == 0
    assert [r["row"] for r in rows] == ["APPLY", "ALREADY", "NOT_VERIFIABLE", "NOT_VERIFIABLE", "NOT_VERIFIABLE"]
    assert rows[0]["current_generated_at"] == at


def test_a_directory_of_exported_answers_takes_each_id_from_its_file_name(tmp_path, capsys):
    b = _bundle(tmp_path)
    src = tmp_path / "answers"
    src.mkdir()
    (src / "base~terms~a.md.json").write_text(json.dumps(_answer("/base/terms/a.md", GEN, "2026-11-10T10:00:00Z")),
                                              encoding="utf-8")
    (src / "base~terms~b.md.json").write_text(json.dumps(_answer(
        "/base/terms/b.md", GEN, "2026-11-11T10:00:00Z", "not_confirmed", comment="no", version=2)), encoding="utf-8")
    capsys.readouterr()
    assert main([str(b), "--answers", str(src)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        'NOT_CONFIRMED /base/terms/b.md answered_at 2026-11-11T10:00:00Z by u_test (id base~terms~b.md, version 2): '
        'comment "no"',
        "APPLY /base/terms/a.md answered_at 2026-11-10T10:00:00Z by u_test (id base~terms~a.md, version None)"]


def test_an_unreadable_input_or_a_mixed_mode_exits_2(tmp_path, capsys):
    b = _bundle(tmp_path)
    good = [_answer("/base/terms/a.md", GEN, "2026-11-10T10:00:00Z")]
    bad = (tmp_path / "bad.json")
    bad.write_text("{not json", encoding="utf-8")
    assert main([str(b), "--answers", str(bad)]) == 2
    assert main([str(b), "--answers", str(tmp_path / "none.json")]) == 2
    for wrong in ({"path": "/base/terms/a.md"}, [{"choice": "confirmed"}], [{**good[0], "choice": "yes"}],
                  [{**good[0], "answered_at": "yesterday"}], ["x"]):
        code, _, err = _answers_run(capsys, b, wrong, tmp_path)
        assert code == 2 and err.startswith("okf_viewer: "), (wrong, err)
    assert _answers_run(capsys, b, good, tmp_path, "--since", "last week")[0] == 2
    assert _answers_run(capsys, b, good, tmp_path, "--out", str(tmp_path / "v"))[0] == 2
    assert _answers_run(capsys, b, good, tmp_path, "--force")[0] == 2
    assert not (tmp_path / "v").exists()
    assert main([str(b)]) == 2
    assert _run(b, tmp_path / "w", "--json") == 2 and not (tmp_path / "w").exists()


def test_the_template_reads_concepts_json_and_holds_no_data():
    page = TEMPLATE.read_text(encoding="utf-8")
    assert 'fetch("concepts.json")' in page
    assert "<title>Knowledge Viewer</title>" in page
    assert '"concepts":' not in page and "generated_at\":" not in page


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
