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

- Writes DIR/index.html, the page template the plugin ships (okf-standard/viewer/index.html) byte for byte, and
  DIR/concepts.json, a snapshot of the bundle the page reads:
  {commit, dirty, built_at, round: {name, title, paths}, concepts: [...]}.
- Reads the bundle as okf-lint does (scan_bundle): the paths .okfignore matches, projections/ and nested bundles are
  left out, each nested bundle named on one NOTICE line. Each Markdown file with a frontmatter is one concept, but
  each index.md, log.md and the Conflict Log; fragments, project.md and base/profile.md included.
- Each concept: path (bundle path), type, title, description, status, decision_status, question_status,
  distillation_status, owner, generated_by, generated_at, verified_by, verified_at (the last entry when verified is
  a list), stale_after, supersedes, superseded_by, layer (base, fragments or root), frontmatter (the raw YAML between
  the '---' lines), body, and links: the bundle paths of the concepts its body links to, read with the link reader
  lint uses, in order of first appearance, with no external, broken or non-concept target. The keys are read with
  the aliases of the Domain Profile in force resolved (knowledge/3.0); frontmatter stays as written.
- commit is the repository's HEAD and dirty says whether git reports a change under the bundle; outside git, commit
  is null and dirty false. built_at is now.
- The round: --round NAME with --paths gives those concepts (each must be one); with no --paths, or no --round, the
  round is every base/ concept in status draft and not verified at its current generated.at. --round-title defaults
  to the name.
- Never overwrites an existing file unless given --force; prints `created <path>`, `rewritten <path>` (with --force)
  or `skipped (exists) <path>` for each file.
- Exit: 2, writing nothing, when the bundle has no index.md, --out is the bundle or inside it, --paths names no
  concept or is given without --round; 1, writing nothing, when lint reports SECRET_IN_BUNDLE (the data leaves the
  machine), each finding named by file and line, never by value; else 0.
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
    PROFILE_30,
    declared_profile,
    extract_links,
    now_iso,
    resolve_link,
    scan_bundle,
    split_frontmatter,
)
from okf_lint import Report, check_secrets  # noqa: E402
from okf_profile import Resolved, load_profile, resolve_aliases  # noqa: E402

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


def bundle_profile(root: Path) -> Resolved | None:
    """The Domain Profile in force, or None (not knowledge/3.0, or a profile that cannot be read: keys as written)."""
    if declared_profile(root) != PROFILE_30:
        return None
    try:
        r = load_profile(root)
    except Exception:  # noqa: BLE001
        return None
    return None if r.findings else r


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


def build(root: Path, prof: Resolved | None) -> tuple[list[dict], list[str]]:
    """The concepts of the bundle, sorted by path, and the nested bundles left out."""
    sc = scan_bundle(root)
    docs = []
    for d in sc.docs:
        if d.path.name in ("index.md", "log.md") or not d.has_fm_block or not isinstance(d.frontmatter, dict):
            continue
        fm = resolve_aliases(prof, d.frontmatter) if prof is not None else d.frontmatter
        if fm.get("type") == "Conflict Log":
            continue
        docs.append((d, fm))
    concepts = {d.path.resolve(): "/" + d.rel for d, _ in docs}
    out = []
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
    return out, sc.nested


def unverified(c: dict) -> bool:
    return (c["layer"] == BASE_DIR and c["status"] == "draft"
            and not (c["verified_at"] and c["generated_at"] and str(c["verified_at"]) >= str(c["generated_at"])))


def write(path: Path, content: bytes, force: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return f"skipped (exists) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return f"{'rewritten' if existed else 'created'} {path}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="bundle root, the directory that holds index.md")
    ap.add_argument("--out", required=True, help="output directory, outside the bundle")
    ap.add_argument("--round", help="name of the review round")
    ap.add_argument("--round-title", help="title of the review round (default: its name)")
    ap.add_argument("--paths", nargs="+", help="bundle paths of the round's concepts (with --round)")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args(argv)

    def fail(msg: str, code: int = 2) -> int:
        sys.stderr.write(f"okf_viewer: {msg}; nothing written\n")
        return code

    root = Path(args.bundle).resolve()
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
    concepts, nested = build(root, bundle_profile(root))
    paths = {c["path"] for c in concepts}
    if args.round and args.paths:
        missing = [p for p in args.paths if p not in paths]
        if missing:
            return fail(f"--paths names no concept of the bundle: {', '.join(missing)}")
        round_paths = list(args.paths)
    else:
        round_paths = [c["path"] for c in concepts if unverified(c)]
    name, title = (args.round, args.round_title or args.round) if args.round else DEFAULT_ROUND
    commit, dirty = git_state(root)
    data = {"commit": commit, "dirty": dirty, "built_at": now_iso(),
            "round": {"name": name, "title": title, "paths": round_paths}, "concepts": concepts}
    if nested:
        print(f"NOTICE nested bundles left out: {', '.join(nested)}")
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
    expected = sorted("/" + d.rel for d in scan_bundle(b).docs
                      if d.path.name not in ("index.md", "log.md") and d.rel != "conflict-log.md")
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
