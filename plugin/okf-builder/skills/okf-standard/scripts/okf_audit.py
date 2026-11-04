#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_audit.py — The git facts of okf-review's audit mode, and the findings earlier audits accepted as is.

Usage:
    uv run okf_audit.py [path/to/bundle] [--since REF] [--json]

- --since: a commit, a tag or a date (YYYY-MM-DD or ISO 8601). A date is resolved to the last
  commit before it (`git log -1 --before=<date>`, a bare date read as its midnight); a commit or
  tag to its full SHA (`git rev-parse`).
- Without --since, or for a bundle outside a git repository, the git facts are skipped with a notice.
- With one, compares the reference commit with the working tree (`git diff --name-status -M`) and
  lists every concept or fragment deleted (and not back on disk) or renamed since then. A change is recorded when the old
  path was `status: deprecated` at the reference commit (`git show`) or when an entry of the root
  log.md that its version at the reference commit lacks names the old path; otherwise it is a finding:
  DELETED_UNRECORDED or RENAMED_UNRECORDED. index.md, log.md and projections/ are not concepts.
- Reads log.md for earlier audits at the same reference point (an `**Update**: Audit since ...
  (reference `<key>`)` entry, the key the full SHA when the reference resolved, else the reference as
  typed, else `none`) and returns the findings they accepted as is, so the audit leaves them out.
- Runs only read-only git (log, diff, rev-parse, show); writes nothing. Exit 2 when the reference
  cannot be resolved.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    DATE_RE,
    ISO_RE,
    PROJECTIONS_DIR,
    RESERVED,
    find_bundle,
    parse_yaml,
    split_frontmatter,
)

READ_ONLY_GIT = ("log", "diff", "rev-parse", "show")
LOG_DATE_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
LOG_ENTRY_RE = re.compile(r"^\s*[*-]\s+(.*)$")
AUDIT_RE = re.compile(r"\*\*Update\*\*:\s*Audit since\b.*?\(reference `([^`]+)`\)")
ACCEPTED_RE = re.compile(r"Accepted as is:\s*(.*)$")
ACCEPTED_ITEM_RE = re.compile(r"`([^`]+)`\s*\(([^()]+)\)")


def git(bundle: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a read-only git command in the bundle; any other subcommand is refused."""
    if not args or args[0] not in READ_ONLY_GIT:
        raise ValueError(f"okf_audit runs only read-only git ({', '.join(READ_ONLY_GIT)}), not: git {' '.join(args)}")
    return subprocess.run(["git", "-C", str(bundle), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          check=False)


def in_git(bundle: Path) -> bool:
    try:
        p = git(bundle, "rev-parse", "--is-inside-work-tree")
    except FileNotFoundError:
        return False
    return p.returncode == 0 and p.stdout.strip() == "true"


def resolve(bundle: Path, ref: str) -> str | None:
    """The full SHA of a commit or tag, or of the last commit before a date."""
    if DATE_RE.match(ref) or ISO_RE.match(ref):
        before = f"{ref} 00:00:00" if DATE_RE.match(ref) else ref
        p = git(bundle, "log", "-1", "--format=%H", f"--before={before}")
    else:
        p = git(bundle, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    sha = p.stdout.strip()
    return sha if p.returncode == 0 and sha else None


def commit_date(bundle: Path, sha: str) -> str:
    return git(bundle, "show", "-s", "--format=%cI", sha).stdout.strip()[:10]


def is_concept_path(rel: str) -> bool:
    return rel.endswith(".md") and rel.rsplit("/", 1)[-1] not in RESERVED and not rel.startswith(PROJECTIONS_DIR + "/")


def deleted_and_renamed(bundle: Path, sha: str) -> list[dict]:
    """The concepts deleted or renamed between the reference commit and the working tree, git's rename detection on."""
    out = git(bundle, "diff", "--name-status", "-M", "--relative", sha, "--", ".").stdout
    changes = []
    for line in out.splitlines():
        parts = line.split("\t")
        status = parts[0]
        if status == "D" and len(parts) == 2 and is_concept_path(parts[1]) and not (bundle / parts[1]).exists():
            changes.append({"change": "deleted", "path": parts[1]})
        elif status.startswith("R") and len(parts) == 3 and is_concept_path(parts[1]):
            changes.append({"change": "renamed", "path": parts[1], "to": parts[2]})
    return changes


def deprecated_at(bundle: Path, sha: str, rel: str) -> bool:
    p = git(bundle, "show", f"{sha}:./{rel}")
    if p.returncode != 0:
        return False
    raw, _ = split_frontmatter(p.stdout)
    try:
        fm = parse_yaml(raw) if raw is not None else {}
    except Exception:  # noqa: BLE001
        return False
    return str(fm.get("status", "")).strip() == "deprecated"


def log_entries(text: str) -> list[tuple[str, str]]:
    """(date, text) of each entry of a log.md."""
    entries, day = [], ""
    for line in text.splitlines():
        m = LOG_DATE_RE.match(line)
        if m:
            day = m.group(1)
            continue
        e = LOG_ENTRY_RE.match(line)
        if e and day:
            entries.append((day, e.group(1)))
    return entries


def disk_log(bundle: Path) -> str:
    log = bundle / "log.md"
    return log.read_text(encoding="utf-8") if log.is_file() else ""


def added_log_entries(bundle: Path, sha: str) -> list[str]:
    """The entries of the root log.md on disk that its version at the reference commit does not have."""
    p = git(bundle, "show", f"{sha}:./log.md")
    before = {t for _, t in log_entries(p.stdout)} if p.returncode == 0 else set()
    return [t for _, t in log_entries(disk_log(bundle)) if t not in before]


def names_path(text: str, rel: str) -> bool:
    return re.search(rf"(?<![\w/.-])/?{re.escape(rel)}(?![\w/-]|\.\w)", text) is not None


def earlier_accepted(entries: list[tuple[str, str]], key: str) -> tuple[int, list[dict]]:
    """How many earlier audits share this reference key, and the findings they accepted as is."""
    audits, accepted = 0, []
    for day, text in entries:
        m = AUDIT_RE.search(text)
        if not m or m.group(1) != key:
            continue
        audits += 1
        a = ACCEPTED_RE.search(text)
        for path, finding in ACCEPTED_ITEM_RE.findall(a.group(1) if a else ""):
            accepted.append({"path": path, "finding": finding.strip(), "date": day})
    return audits, accepted


def audit(bundle: Path, since: str | None) -> dict:
    report = {"bundle": str(bundle), "git": in_git(bundle), "reference": None, "reference_key": since or "none",
              "notices": [], "changes": [], "findings": [], "earlier_audits": 0, "accepted_as_is": []}
    if not report["git"]:
        report["notices"].append("the bundle is not in a git repository: git facts skipped")
    elif not since:
        report["notices"].append("no reference point (a commit, tag or date): git facts skipped")
    else:
        sha = resolve(bundle, since)
        if sha is None:
            raise LookupError(f"reference point '{since}' does not resolve to a commit"
                              + (" (no commit before that date)" if DATE_RE.match(since) or ISO_RE.match(since) else ""))
        day = commit_date(bundle, sha)
        report["reference"] = {"given": since, "commit": sha, "date": day}
        report["reference_key"] = sha
        later = added_log_entries(bundle, sha)
        for c in deleted_and_renamed(bundle, sha):
            c["deprecated_at_reference"] = deprecated_at(bundle, sha, c["path"])
            c["logged"] = any(names_path(t, c["path"]) for t in later)
            report["changes"].append(c)
            if c["deprecated_at_reference"] or c["logged"]:
                continue
            what = f"renamed to {c['to']}" if c["change"] == "renamed" else "deleted"
            finding = {"code": "RENAMED_UNRECORDED" if c["change"] == "renamed" else "DELETED_UNRECORDED",
                       "level": "WARN", "path": c["path"],
                       "message": f"{what} since {since} ({sha[:12]}) without a deprecation at the reference point "
                                  "or a log.md entry added since then naming it"}
            if "to" in c:
                finding["to"] = c["to"]
            report["findings"].append(finding)
    report["earlier_audits"], report["accepted_as_is"] = earlier_accepted(log_entries(disk_log(bundle)), report["reference_key"])
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Git facts for okf-review's audit mode (read-only).")
    ap.add_argument("bundle", nargs="?")
    ap.add_argument("--since", help="reference point: a commit, a tag or a date")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    bundle = Path(a.bundle).resolve() if a.bundle else find_bundle()
    if bundle is None or not (bundle / "index.md").is_file():
        print("no OKF bundle found (knowledge/index.md)", file=sys.stderr)
        return 2
    try:
        report = audit(bundle, a.since)
    except LookupError as e:
        print(f"okf_audit: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    for n in report["notices"]:
        print(f"NOTICE {n}")
    if report["reference"]:
        r = report["reference"]
        print(f"reference point {r['given']} = {r['commit']} ({r['date']})")
    for c in report["changes"]:
        state = "recorded" if c["deprecated_at_reference"] or c["logged"] else "unrecorded"
        print(f"{c['change']:8} {c['path']}" + (f" -> {c['to']}" if "to" in c else "") + f"  [{state}]")
    for f in report["findings"]:
        print(f"WARN {f['code']} {f['path']}: {f['message']}")
    print(f"{len(report['findings'])} git findings; {report['earlier_audits']} earlier audits at reference "
          f"{report['reference_key']}, {len(report['accepted_as_is'])} findings accepted as is")
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_audit.py --test): each builds a temporary git repository
# --------------------------------------------------------------------------
_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def _g(repo: Path, *args: str, date: str = "2026-11-01T12:00:00+00:00") -> str:
    env = {**os.environ, **_ENV, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def _concept(title: str, status: str = "draft") -> str:
    return (f"---\ntype: Term\ntitle: {title}\ndescription: {title}.\nstatus: {status}\n"
            "generated: { by: human:test, at: 2026-11-01T00:00:00Z }\n---\n\n# Definition\n\n"
            + f"{title} is a word that stays the same across edits, long enough for git to see a rename.\n" * 4)


def _repo(tmp: Path, log: str = "") -> tuple[Path, str]:
    """A repo with knowledge/ and two terms at a first commit; returns the bundle and that commit."""
    k = tmp / "knowledge"
    (k / "base" / "domain").mkdir(parents=True)
    (k / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n---\n\n# Root\n', encoding="utf-8")
    (k / "log.md").write_text("# Bundle history\n\n## 2026-11-01\n* **Creation**: terms.\n" + log, encoding="utf-8")
    (k / "base" / "domain" / "alpha.md").write_text(_concept("Alpha"), encoding="utf-8")
    (k / "base" / "domain" / "beta.md").write_text(_concept("Beta"), encoding="utf-8")
    _g(tmp, "init", "-q")
    _g(tmp, "add", "-A")
    _g(tmp, "commit", "-q", "-m", "first")
    return k, _g(tmp, "rev-parse", "HEAD")


def _commit(tmp: Path, msg: str, date: str = "2026-11-03T12:00:00+00:00") -> None:
    _g(tmp, "add", "-A", date=date)
    _g(tmp, "commit", "-q", "-m", msg, date=date)


def _prepend_log(k: Path, day: str, entry: str) -> None:
    text = (k / "log.md").read_text(encoding="utf-8").replace("# Bundle history\n\n", f"# Bundle history\n\n## {day}\n* {entry}\n\n", 1)
    (k / "log.md").write_text(text, encoding="utf-8")


def test_deletion_without_deprecation_or_log_is_a_finding(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    r = audit(k, first)
    assert [(f["code"], f["path"]) for f in r["findings"]] == [("DELETED_UNRECORDED", "base/domain/alpha.md")]
    assert r["reference"]["commit"] == first and r["reference"]["date"] == "2026-11-01"


def test_deletion_of_a_concept_deprecated_at_the_reference_is_recorded(tmp_path):
    k, _ = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").write_text(_concept("Alpha", "deprecated"), encoding="utf-8")
    _commit(tmp_path, "deprecate alpha", date="2026-11-02T12:00:00+00:00")
    ref = _g(tmp_path, "rev-parse", "HEAD")
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    r = audit(k, ref)
    assert r["findings"] == [] and r["changes"][0]["deprecated_at_reference"] is True


def test_a_log_entry_since_the_reference_records_a_deletion_and_an_older_one_does_not(tmp_path):
    k, first = _repo(tmp_path, log="* **Creation**: [Alpha](/base/domain/alpha.md).\n")
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    assert [f["code"] for f in audit(k, first)["findings"]] == ["DELETED_UNRECORDED"]
    _prepend_log(k, "2026-11-03", "**Deprecation**: `base/domain/alpha.md` removed; see beta.")
    r = audit(k, first)
    assert r["findings"] == [] and r["changes"][0]["logged"] is True


def test_rename_is_detected_by_git_and_reported_with_its_target(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").rename(k / "base" / "domain" / "alpha-term.md")
    (k / "base" / "domain" / "alpha-term.md").write_text(_concept("Alpha") + "One more line.\n", encoding="utf-8")
    _commit(tmp_path, "rename alpha")
    r = audit(k, first)
    assert [(f["code"], f["path"], f.get("to")) for f in r["findings"]] == [
        ("RENAMED_UNRECORDED", "base/domain/alpha.md", "base/domain/alpha-term.md")]
    _prepend_log(k, "2026-11-03", "**Update**: [Alpha](/base/domain/alpha-term.md) moved from /base/domain/alpha.md.")
    assert audit(k, first)["findings"] == []


def test_a_tag_and_a_date_resolve_to_the_reference_commit(tmp_path):
    k, first = _repo(tmp_path)
    _g(tmp_path, "tag", "v1")
    (k / "base" / "domain" / "beta.md").unlink()
    _commit(tmp_path, "drop beta", date="2026-11-03T12:00:00+00:00")
    assert resolve(k, "v1") == first
    assert resolve(k, "2026-11-02") == first  # the last commit before that date
    assert resolve(k, "2026-11-03") == first  # a bare date is its midnight: the 12:00 commit is not before it
    assert resolve(k, "2026-11-04") == _g(tmp_path, "rev-parse", "HEAD")
    assert resolve(k, "2026-10-01") is None
    assert [f["path"] for f in audit(k, "2026-11-02")["findings"]] == ["base/domain/beta.md"]


def test_a_file_put_back_but_not_yet_added_is_not_deleted(tmp_path):
    k, first = _repo(tmp_path)
    alpha = k / "base" / "domain" / "alpha.md"
    text = alpha.read_text(encoding="utf-8")
    alpha.unlink()
    _commit(tmp_path, "drop alpha")
    alpha.write_text(text, encoding="utf-8")  # untracked: git diff against the working tree still says D
    assert audit(k, first)["changes"] == []


def test_reserved_files_and_projections_are_not_concepts(tmp_path):
    k, _ = _repo(tmp_path)
    (k / "projections").mkdir()
    (k / "projections" / "view.md").write_text("# View\n", encoding="utf-8")
    (k / "base" / "domain" / "index.md").write_text("# domain\n", encoding="utf-8")
    _commit(tmp_path, "add a projection and an index", date="2026-11-02T12:00:00+00:00")
    ref = _g(tmp_path, "rev-parse", "HEAD")
    (k / "projections" / "view.md").unlink()
    (k / "base" / "domain" / "index.md").unlink()
    _commit(tmp_path, "drop them")
    assert audit(k, ref)["changes"] == []


def test_without_a_reference_or_outside_git_the_git_facts_are_skipped(tmp_path):
    k, _ = _repo(tmp_path / "repo")
    r = audit(k, None)
    assert r["changes"] == [] and r["notices"] == ["no reference point (a commit, tag or date): git facts skipped"]
    plain = tmp_path / "plain" / "knowledge"
    plain.mkdir(parents=True)
    (plain / "index.md").write_text('---\nokf_version: "0.2"\n---\n', encoding="utf-8")
    r = audit(plain, "2026-11-02")
    assert r["notices"] == ["the bundle is not in a git repository: git facts skipped"] and r["reference"] is None


def test_an_unknown_reference_exits_2(tmp_path, capsys):
    k, _ = _repo(tmp_path)
    assert main([str(k), "--since", "no-such-tag"]) == 2
    assert "does not resolve" in capsys.readouterr().err


def test_earlier_audits_at_the_same_resolved_reference_give_their_accepted_findings(tmp_path):
    k, first = _repo(tmp_path)
    _g(tmp_path, "tag", "v1")
    _prepend_log(k, "2026-11-03", f"**Update**: Audit since `2026-11-02` (reference `{first}`): 3 findings; "
                                  "fixed now: 1; Accepted as is: `/base/domain/alpha.md` (no rollback); "
                                  "`/base/domain/beta.md` (mention of Gamma).")
    _prepend_log(k, "2026-11-04", "**Update**: Audit since `HEAD~5` (reference `0000000000000000000000000000000000000000`): "
                                  "Accepted as is: `/base/domain/beta.md` (other).")
    r = audit(k, "v1")  # a tag that resolves to the same commit as the earlier date
    assert r["earlier_audits"] == 1
    assert [(a["path"], a["finding"]) for a in r["accepted_as_is"]] == [
        ("/base/domain/alpha.md", "no rollback"), ("/base/domain/beta.md", "mention of Gamma")]
    assert audit(k, None)["earlier_audits"] == 0


def test_json_output_lists_the_findings(tmp_path, capsys):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    assert main([str(k), "--since", first, "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["findings"][0]["code"] == "DELETED_UNRECORDED" and out["findings"][0]["level"] == "WARN"


def test_git_refuses_any_command_but_read_only_ones(tmp_path):
    for bad in (("commit", "-m", "x"), ("checkout", "."), ("push",), ()):
        try:
            git(tmp_path, *bad)
        except ValueError:
            continue
        raise AssertionError(f"git {bad} was not refused")


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
