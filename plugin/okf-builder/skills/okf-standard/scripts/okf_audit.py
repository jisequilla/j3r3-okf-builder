#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_audit.py — The git facts of okf-review's audit mode, the concepts edited after their instance closed, and the
findings earlier audits accepted as is.

Usage:
    uv run okf_audit.py [path/to/bundle] [--since REF] [--json]

- --since: a commit, a tag or a date (YYYY-MM-DD or ISO 8601). A date is resolved to the last
  commit before it (`git log -1 --before=<date>`, a bare date read as its midnight); a commit or
  tag to its full SHA (`git rev-parse`).
- Without --since, or for a bundle outside a git repository, the git facts are skipped with a notice.
- With one, compares the reference commit with the working tree (`git diff --name-status -z -M`, with
  `diff.renames=false` pinned so that -M alone detects renames) and lists every concept or fragment deleted
  (and not back on disk) or renamed since then. A deleted path whose content is identical to an untracked .md
  file (`git ls-files --others`, `git hash-object` without -w) was renamed without `git add`; a deleted path
  with untracked files of the same name but other content stays deleted, with those files as candidates.
- The paths lint leaves out are left out here too (okf_common's scan: .okfignore, nested bundles, non-OKF
  directories), and so are the files that are not concepts (index.md and log.md at any level, the root's
  reserved files, base/profile.md, projections/).
- A deletion is recorded when the old path was `status: deprecated` at the reference commit (`git show`), or
  by an entry added since then, in the root log.md or the log.md of the file's directory (standard §6), that
  names the old path and is a **Deprecation** or says it was deprecated, removed, deleted, retired or
  superseded. A rename is recorded by such an entry naming both the old and the new path. Audit entries never
  record anything. Otherwise it is a finding: DELETED_UNRECORDED or RENAMED_UNRECORDED.
- Looks inside every instance of the bundle, at any depth, with or without --since and inside or outside git:
  EDITED_AFTER_CLOSE for each concept of a closed instance (state: closed, closed_at an ISO 8601 date-time) whose
  generated.at is a later instant than that instance's own closed_at (standard §2.2, ADR-0039 decision 9). index.md
  and log.md are not concepts; every other document of the instance is. The git facts still leave nested bundles out.
- Reads log.md for earlier audits at the same reference point (an `**Update**: Audit since ...
  (reference `<key>`)` entry, the key the full SHA when the reference resolved, else the reference as
  typed, else `none`) and returns the findings they accepted as is, so the audit leaves them out; an item it
  cannot read is a notice, never dropped silently.
- Runs only read-only git (log, diff, rev-parse, show, ls-files, hash-object without -w); writes nothing,
  not even the index. Exit 2 when the reference cannot be resolved.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import (  # noqa: E402
    BASE_DIR,
    DATE_RE,
    ISO_RE,
    LAYER_DIRS,
    PROFILE_REL,
    PROJECTIONS_DIR,
    RESERVED,
    OkfIgnore,
    find_bundle,
    parse_yaml,
    reserved_path,
    scan_bundle,
    root_frontmatter,
    split_frontmatter,
    to_dt,
)
from okf_lint import kind_instances  # noqa: E402
from okf_profile import load_profile  # noqa: E402

READ_ONLY_GIT = ("log", "diff", "rev-parse", "show", "ls-files", "hash-object")
# -M alone detects renames, whatever diff.renames the user's config sets; no colour codes in the output
GIT_PINNED = ("-c", "diff.renames=false", "-c", "color.ui=false")
LOG_DATE_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
LOG_ENTRY_RE = re.compile(r"^\s*[*-]\s+(.*)$")
AUDIT_RE = re.compile(r"\*\*Update\*\*:\s*Audit since\b.*?\(reference `([^`]+)`\)")
ACCEPTED_RE = re.compile(r"Accepted as is:\s*(.*)$")
ACCEPTED_PATH_RE = re.compile(r"`([^`]+)`\s*")
RETIRED_RE = re.compile(r"\b(deprecat|remov|delet|retir|supersed)\w*", re.I)


def git(bundle: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a read-only git command in the bundle; any other subcommand, and hash-object with an option, is refused."""
    if not args or args[0] not in READ_ONLY_GIT:
        raise ValueError(f"okf_audit runs only read-only git ({', '.join(READ_ONLY_GIT)}), not: git {' '.join(args)}")
    if args[0] == "hash-object" and any(a.startswith("-") and a != "--" for a in args[1:]):
        raise ValueError(f"okf_audit runs git hash-object only on paths (never -w), not: git {' '.join(args)}")
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}  # git never refreshes the index on the audit's behalf
    return subprocess.run(["git", "-C", str(bundle), *GIT_PINNED, *args], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, check=False, env=env)


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


def show(bundle: Path, sha: str, rel: str) -> str | None:
    """A file of the bundle as it was at a commit, or None."""
    p = git(bundle, "show", f"{sha}:./{rel}")
    return p.stdout if p.returncode == 0 else None


def is_concept_path(rel: str) -> bool:
    return (rel.endswith(".md") and PurePosixPath(rel).name not in RESERVED and not reserved_path(rel)
            and not rel.startswith(PROJECTIONS_DIR + "/"))


def _declares_version(text: str | None) -> bool:
    raw, _ = split_frontmatter(text or "")
    try:
        return raw is not None and parse_yaml(raw).get("okf_version") is not None
    except Exception:  # noqa: BLE001
        return False


def bundle_paths(bundle: Path, sha: str):
    """A test of whether a path is one lint reads as a concept: okf_common's scan of the bundle on disk (.okfignore,
    nested bundles, non-OKF directories), the .okfignore applied to directories a deletion removed, and a directory
    whose index.md declared okf_version at the reference commit taken as a nested bundle."""
    ign = OkfIgnore.load(bundle)
    sc = scan_bundle(bundle)
    left_out = [*sc.ignored, *sc.nested, *(d for d, _ in sc.not_okf)]
    profile_kept = (bundle / PROFILE_REL).is_file()
    nested_at_ref: dict = {}

    def keep(rel: str) -> bool:
        if not is_concept_path(rel) or ign.match(rel, False):
            return False
        parts = rel.split("/")
        for i in range(1, len(parts)):
            d = "/".join(parts[:i])
            if parts[i - 1].startswith("."):
                return False
            if ign.match(d, True) and not (d == BASE_DIR and profile_kept):
                return False
            if not (i == 1 and d in LAYER_DIRS):
                if d not in nested_at_ref:
                    nested_at_ref[d] = _declares_version(show(bundle, sha, d + "/index.md"))
                if nested_at_ref[d]:
                    return False
        return not any(rel == x or (x.endswith("/") and rel.startswith(x)) for x in left_out)
    return keep


def untracked_md(bundle: Path, keep) -> list[str]:
    out = git(bundle, "ls-files", "-z", "--others", "--exclude-standard", "--", ".").stdout
    return [p for p in out.split("\0") if p and keep(p)]


def deleted_and_renamed(bundle: Path, sha: str) -> list[dict]:
    """The concepts deleted or renamed between the reference commit and the working tree, git's rename detection on;
    a deleted path paired with an untracked file of identical content is a rename not yet added."""
    keep = bundle_paths(bundle, sha)
    out = git(bundle, "diff", "--name-status", "-z", "-M", "--relative", sha, "--", ".").stdout
    fields, i, changes = out.split("\0"), 0, []
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status[0] in "RC":
            old, new, i = fields[i + 1], fields[i + 2], i + 3
        else:
            old, new, i = fields[i + 1], None, i + 2
        if status == "D" and keep(old) and not (bundle / old).exists():
            changes.append({"change": "deleted", "path": old})
        elif status.startswith("R") and keep(old):
            changes.append({"change": "renamed", "path": old, "to": new})
    deleted = [c for c in changes if c["change"] == "deleted"]
    untracked = untracked_md(bundle, keep) if deleted else []
    hashes = dict(zip(untracked, git(bundle, "hash-object", "--", *untracked).stdout.split())) if untracked else {}
    for c in deleted:
        blob = git(bundle, "rev-parse", f"{sha}:./{c['path']}").stdout.strip()
        same = next((u for u in untracked if hashes.get(u) == blob), None)
        if same:
            untracked.remove(same)
            c.update(change="renamed", to=same, untracked=True)
            continue
        name = PurePosixPath(c["path"]).name
        candidates = [u for u in untracked if PurePosixPath(u).name == name]
        if candidates:
            c["untracked_candidates"] = candidates
    return changes


def deprecated_at(bundle: Path, sha: str, rel: str) -> bool:
    raw, _ = split_frontmatter(show(bundle, sha, rel) or "")
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


def disk_log(bundle: Path, rel: str = "log.md") -> str:
    log = bundle / rel
    return log.read_text(encoding="utf-8") if log.is_file() else ""


def added_log_entries(bundle: Path, sha: str, rel: str = "log.md") -> list[str]:
    """The entries of a log.md on disk that its version at the reference commit does not have, audits left out."""
    before = {t for _, t in log_entries(show(bundle, sha, rel) or "")}
    return [t for _, t in log_entries(disk_log(bundle, rel)) if t not in before and not AUDIT_RE.search(t)]


def names_path(text: str, rel: str) -> bool:
    return re.search(rf"(?<![\w/.-])/?{re.escape(rel)}(?![\w/-]|\.\w)", text) is not None


def recorded(bundle: Path, sha: str, c: dict, cache: dict) -> bool:
    """Whether an entry added since the reference, in the root log.md or that of the directory of either path,
    records the change: a deletion as a Deprecation or as deprecated/removed/superseded, a rename by both paths.
    In a directory's log.md a path may also be written relative to that directory."""
    dirs = {""} | {PurePosixPath(p).parent.as_posix() for p in (c["path"], c.get("to")) if p}
    for d in sorted(x for x in dirs if x != "."):
        rel = f"{d}/log.md" if d else "log.md"
        if rel not in cache:
            cache[rel] = added_log_entries(bundle, sha, rel)
        for t in cache[rel]:
            def named(p: str) -> bool:
                return names_path(t, p) or (bool(d) and p.startswith(d + "/") and names_path(t, p[len(d) + 1:]))
            if c["change"] == "renamed":
                if named(c["path"]) and named(c["to"]):
                    return True
            elif named(c["path"]) and (t.startswith("**Deprecation**") or RETIRED_RE.search(t)):
                return True
    return False


def accepted_items(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """The `path` (short name) items of an Accepted-as-is list, a short name with balanced parentheses kept whole;
    and the items that cannot be read."""
    items, bad, pos = [], [], 0
    while (m := ACCEPTED_PATH_RE.search(text, pos)) is not None:
        pos = m.end()
        if not text.startswith("(", pos):
            bad.append(m.group(0).strip())
            continue
        depth, j = 0, pos
        while j < len(text):
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            if depth == 0:
                break
            j += 1
        if depth:
            bad.append(text[m.start():].strip())
            break
        items.append((m.group(1), text[pos + 1:j].strip()))
        pos = j + 1
    return items, bad


def earlier_accepted(entries: list[tuple[str, str]], key: str) -> tuple[int, list[dict], list[str]]:
    """How many earlier audits share this reference key, the findings they accepted as is, and a notice for each
    accepted item that cannot be read."""
    audits, accepted, notices = 0, [], []
    for day, text in entries:
        m = AUDIT_RE.search(text)
        if not m or m.group(1) != key:
            continue
        audits += 1
        a = ACCEPTED_RE.search(text)
        items, bad = accepted_items(a.group(1) if a else "")
        accepted += [{"path": path, "finding": finding, "date": day} for path, finding in items]
        notices += [f"the audit of {day} lists an accepted-as-is item that cannot be read, so it is raised again: {b}"
                    for b in bad]
    return audits, accepted, notices


def edited_after_close(bundle: Path) -> list[dict]:
    """EDITED_AFTER_CLOSE for every concept of a closed instance, at any depth, whose generated.at is later than its
    own instance's closed_at. Instances are found as lint finds them (kind_instances), with the domain bundle's
    Domain Profile at every depth. Reads no git."""
    domain = load_profile(bundle)
    out: list[dict] = []

    def walk(here: Path, prefix: str) -> None:
        for _, _, rels in kind_instances(here, root_frontmatter(here), domain, domain, scan_bundle(here)):
            for rel in rels:
                sub = here / rel.rstrip("/")
                fm = root_frontmatter(sub)
                closed = to_dt(fm.get("closed_at")) if fm.get("state") == "closed" else None
                for d in scan_bundle(sub).docs if closed is not None else []:
                    gen = (d.frontmatter or {}).get("generated")
                    at = to_dt(gen.get("at")) if isinstance(gen, dict) and d.path.name not in RESERVED else None
                    if at is not None and at > closed:
                        out.append({"code": "EDITED_AFTER_CLOSE", "level": "WARN", "path": prefix + rel + d.rel,
                                    "instance": prefix + rel,
                                    "message": f"edited after its instance closed: generated.at {at.isoformat()} is "
                                               f"later than closed_at {closed.isoformat()}; a closed instance is "
                                               "frozen: restore the concept as it was when it closed, or carry the "
                                               "change into the parent"})
                walk(sub, prefix + rel)

    walk(bundle, "")
    return out


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
        cache: dict = {}
        for c in deleted_and_renamed(bundle, sha):
            c["deprecated_at_reference"] = c["change"] == "deleted" and deprecated_at(bundle, sha, c["path"])
            c["logged"] = recorded(bundle, sha, c, cache)
            report["changes"].append(c)
            if c["deprecated_at_reference"] or c["logged"]:
                continue
            ref = f"since {since} ({sha[:12]})"
            if c["change"] == "renamed":
                finding = {"code": "RENAMED_UNRECORDED", "level": "WARN", "path": c["path"], "to": c["to"],
                           "message": f"renamed to {c['to']}" + (" (not yet added to git)" if c.get("untracked") else "")
                                      + f" {ref} without a log.md entry added since then naming both paths"}
            else:
                others = c.get("untracked_candidates")
                finding = {"code": "DELETED_UNRECORDED", "level": "WARN", "path": c["path"],
                           "message": f"deleted {ref} without a deprecation at the reference point or a Deprecation "
                                      "entry added since then (root log.md or its directory's)"
                                      + (f"; untracked files of the same name, other content: {', '.join(others)}"
                                         if others else "")}
            report["findings"].append(finding)
    report["findings"] += edited_after_close(bundle)
    report["earlier_audits"], report["accepted_as_is"], notices = earlier_accepted(
        log_entries(disk_log(bundle)), report["reference_key"])
    report["notices"] += notices
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Git facts and closed-instance edits for okf-review's audit mode "
                                             "(read-only).")
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
    closed = sum(f["code"] == "EDITED_AFTER_CLOSE" for f in report["findings"])
    print(f"{len(report['findings'])} findings ({len(report['findings']) - closed} git facts, {closed} edited after "
          f"close); {report['earlier_audits']} earlier audits at reference "
          f"{report['reference_key']}, {len(report['accepted_as_is'])} findings accepted as is")
    return 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_audit.py --test): each builds a temporary git repository
# --------------------------------------------------------------------------
_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

try:
    import pytest

    @pytest.fixture(autouse=True)
    def _isolated_git(monkeypatch):
        """The code under test runs git without the user's or the system's config, as the helpers do."""
        for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"):
            monkeypatch.setenv(k, _ENV[k])
except ImportError:  # the script run without pytest
    pass


def _g(repo: Path, *args: str, date: str = "2026-11-01T12:00:00+00:00") -> str:
    env = {**os.environ, **_ENV, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def _concept(title: str, status: str = "draft") -> str:
    return (f"---\ntype: Term\ntitle: {title}\ndescription: {title}.\nstatus: {status}\n"
            "generated: { by: human:test, at: 2026-11-01T00:00:00Z }\n---\n\n# Definition\n\n"
            + f"{title} is a word that stays the same across edits, long enough for git to see a rename.\n" * 4)


def _repo(tmp: Path, log: str = "", extra: dict | None = None) -> tuple[Path, str]:
    """A repo with knowledge/ and two terms (and any extra files, bundle path → text) at a first commit;
    returns the bundle and that commit."""
    k = tmp / "knowledge"
    (k / "base" / "domain").mkdir(parents=True)
    (k / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n---\n\n# Root\n', encoding="utf-8")
    (k / "log.md").write_text("# Bundle history\n\n## 2026-11-01\n* **Creation**: terms.\n" + log, encoding="utf-8")
    (k / "base" / "domain" / "alpha.md").write_text(_concept("Alpha"), encoding="utf-8")
    (k / "base" / "domain" / "beta.md").write_text(_concept("Beta"), encoding="utf-8")
    for rel, text in (extra or {}).items():
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
    _g(tmp, "init", "-q")
    _g(tmp, "add", "-A")
    _g(tmp, "commit", "-q", "-m", "first")
    return k, _g(tmp, "rev-parse", "HEAD")


def _commit(tmp: Path, msg: str, date: str = "2026-11-03T12:00:00+00:00") -> None:
    _g(tmp, "add", "-A", date=date)
    _g(tmp, "commit", "-q", "-m", msg, date=date)


def _prepend_log(k: Path, day: str, entry: str, rel: str = "log.md") -> None:
    f = k / rel
    text = f.read_text(encoding="utf-8") if f.is_file() else "# History\n\n"
    head = text.split("\n\n", 1)[0] + "\n\n"
    f.write_text(text.replace(head, f"{head}## {day}\n* {entry}\n\n", 1), encoding="utf-8")


def _codes(r: dict) -> list[tuple[str, str]]:
    return [(f["code"], f["path"]) for f in r["findings"]]


def test_deletion_without_deprecation_or_log_is_a_finding(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    r = audit(k, first)
    assert _codes(r) == [("DELETED_UNRECORDED", "base/domain/alpha.md")]
    assert r["reference"]["commit"] == first and r["reference"]["date"] == "2026-11-01"


def test_a_deleted_path_with_non_ascii_characters_is_reported(tmp_path):
    k, first = _repo(tmp_path, extra={"base/domain/decisión.md": _concept("Decisión")})
    (k / "base" / "domain" / "decisión.md").unlink()
    _commit(tmp_path, "drop the decision")
    assert _codes(audit(k, first)) == [("DELETED_UNRECORDED", "base/domain/decisión.md")]


def test_a_deletion_lint_leaves_out_is_not_reported(tmp_path):
    plain = "# Notes\n\nNo frontmatter.\n"
    k, first = _repo(tmp_path, extra={
        ".okfignore": "base/drafts/\n",
        "base/drafts/wip.md": _concept("Wip"),  # under an .okfignore'd directory, the directory removed with it
        "base/vendor/index.md": '---\nokf_version: "0.2"\n---\n\n# Vendor bundle\n',  # a nested bundle
        "base/vendor/thing.md": _concept("Thing"),
        "base/notes/a.md": plain, "base/notes/b.md": plain,  # a non-OKF directory
        "base/domain/sub/index.md": "# sub\n",  # the index.md of a directory: not a concept
    })
    for rel in ("base/drafts/wip.md", "base/vendor/thing.md", "base/notes/a.md", "base/domain/sub/index.md"):
        (k / rel).unlink()
    (k / "base" / "drafts").rmdir()
    _commit(tmp_path, "drop what lint does not read")
    r = audit(k, first)
    assert r["changes"] == [] and r["findings"] == []


def test_deletion_of_a_concept_deprecated_at_the_reference_is_recorded(tmp_path):
    k, _ = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").write_text(_concept("Alpha", "deprecated"), encoding="utf-8")
    _commit(tmp_path, "deprecate alpha", date="2026-11-02T12:00:00+00:00")
    ref = _g(tmp_path, "rev-parse", "HEAD")
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    r = audit(k, ref)
    assert r["findings"] == [] and r["changes"][0]["deprecated_at_reference"] is True


def test_a_deprecation_entry_since_the_reference_records_a_deletion_and_an_older_one_does_not(tmp_path):
    k, first = _repo(tmp_path, log="* **Deprecation**: [Alpha](/base/domain/alpha.md) is old.\n")
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    assert [f["code"] for f in audit(k, first)["findings"]] == ["DELETED_UNRECORDED"]
    _prepend_log(k, "2026-11-03", "**Deprecation**: `base/domain/alpha.md` retired; see beta.")
    r = audit(k, first)
    assert r["findings"] == [] and r["changes"][0]["logged"] is True


def test_an_unrelated_update_naming_the_path_does_not_record_a_deletion(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    _prepend_log(k, "2026-11-03", "**Update**: [Alpha](/base/domain/alpha.md) gains an example.")
    assert _codes(audit(k, first)) == [("DELETED_UNRECORDED", "base/domain/alpha.md")]
    _prepend_log(k, "2026-11-04", "**Update**: [Alpha](/base/domain/alpha.md) removed, merged into Beta.")
    assert audit(k, first)["findings"] == []


def test_the_audits_own_entry_does_not_record_a_deletion(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    _prepend_log(k, "2026-11-03", f"**Update**: Audit since `{first}` (reference `{first}`): 1 findings; "
                                  "tracker: `/base/domain/alpha.md` deleted unrecorded; decided by human:t.")
    assert _codes(audit(k, first)) == [("DELETED_UNRECORDED", "base/domain/alpha.md")]


def test_a_deprecation_in_the_directorys_log_records_a_deletion(tmp_path):
    k, first = _repo(tmp_path, extra={"base/domain/log.md": "# Domain history\n\n## 2026-11-01\n* **Creation**: terms.\n"})
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    assert _codes(audit(k, first)) == [("DELETED_UNRECORDED", "base/domain/alpha.md")]
    _prepend_log(k, "2026-11-03", "**Deprecation**: [Alpha](alpha.md), replaced by Beta.", rel="base/domain/log.md")
    assert audit(k, first)["findings"] == []


def test_rename_is_detected_by_git_and_recorded_only_by_an_entry_naming_both_paths(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").rename(k / "base" / "domain" / "alpha-term.md")
    (k / "base" / "domain" / "alpha-term.md").write_text(_concept("Alpha") + "One more line.\n", encoding="utf-8")
    _commit(tmp_path, "rename alpha")
    r = audit(k, first)
    assert [(f["code"], f["path"], f.get("to")) for f in r["findings"]] == [
        ("RENAMED_UNRECORDED", "base/domain/alpha.md", "base/domain/alpha-term.md")]
    _prepend_log(k, "2026-11-03", "**Update**: [Alpha](/base/domain/alpha-term.md) gains a line.")
    assert _codes(audit(k, first)) == [("RENAMED_UNRECORDED", "base/domain/alpha.md")]
    _prepend_log(k, "2026-11-03", "**Update**: [Alpha](/base/domain/alpha-term.md) moved from /base/domain/alpha.md.")
    assert audit(k, first)["findings"] == []


def test_rename_detection_does_not_depend_on_the_repositorys_diff_renames(tmp_path):
    k, first = _repo(tmp_path)
    _g(tmp_path, "config", "diff.renames", "false")
    (k / "base" / "domain" / "beta.md").rename(k / "base" / "domain" / "beta-term.md")
    _commit(tmp_path, "rename beta")
    assert [(f["code"], f.get("to")) for f in audit(k, first)["findings"]] == [
        ("RENAMED_UNRECORDED", "base/domain/beta-term.md")]


def test_a_rename_not_yet_added_to_git_is_a_rename(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").rename(k / "base" / "domain" / "alpha-term.md")  # mv, no git add
    r = audit(k, first)
    assert [(f["code"], f["path"], f.get("to")) for f in r["findings"]] == [
        ("RENAMED_UNRECORDED", "base/domain/alpha.md", "base/domain/alpha-term.md")]
    assert r["changes"][0]["untracked"] is True and "not yet added" in r["findings"][0]["message"]
    assert "?? knowledge/base/domain/alpha-term.md" in _g(tmp_path, "status", "--porcelain")  # still not added


def test_an_untracked_file_of_the_same_name_but_other_content_is_named_as_a_candidate(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").unlink()
    (k / "base" / "other").mkdir()
    (k / "base" / "other" / "alpha.md").write_text(_concept("Other alpha"), encoding="utf-8")
    r = audit(k, first)
    assert _codes(r) == [("DELETED_UNRECORDED", "base/domain/alpha.md")]
    assert r["changes"][0]["untracked_candidates"] == ["base/other/alpha.md"]
    assert "base/other/alpha.md" in r["findings"][0]["message"]


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


def test_outside_git_an_earlier_audit_is_matched_by_the_reference_as_typed(tmp_path):
    plain = tmp_path / "plain" / "knowledge"
    plain.mkdir(parents=True)
    (plain / "index.md").write_text('---\nokf_version: "0.2"\n---\n', encoding="utf-8")
    (plain / "log.md").write_text("# Bundle history\n\n## 2026-11-03\n* **Update**: Audit since `v1` (reference `v1`): "
                                  "1 findings; Accepted as is: `/base/domain/alpha.md` (no rollback).\n", encoding="utf-8")
    r = audit(plain, "v1")
    assert r["earlier_audits"] == 1 and [a["path"] for a in r["accepted_as_is"]] == ["/base/domain/alpha.md"]
    assert audit(plain, "v2")["earlier_audits"] == 0


def test_an_accepted_short_name_with_parentheses_is_kept_whole_and_an_unreadable_item_is_a_notice(tmp_path):
    k, first = _repo(tmp_path)
    _prepend_log(k, "2026-11-03", f"**Update**: Audit since `v1` (reference `{first}`): 2 findings; "
                                  "Accepted as is: `/base/domain/alpha.md` (mention of Gamma (the system)); "
                                  "`/base/domain/beta.md` no short name.")
    r = audit(k, first)
    assert [(a["path"], a["finding"]) for a in r["accepted_as_is"]] == [
        ("/base/domain/alpha.md", "mention of Gamma (the system)")]
    assert any("cannot be read" in n and "/base/domain/beta.md" in n for n in r["notices"])


def test_json_output_lists_the_findings(tmp_path, capsys):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path, "drop alpha")
    assert main([str(k), "--since", first, "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["findings"][0]["code"] == "DELETED_UNRECORDED" and out["findings"][0]["level"] == "WARN"


def test_git_refuses_any_command_but_read_only_ones(tmp_path):
    for bad in (("commit", "-m", "x"), ("checkout", "."), ("push",), ("hash-object", "-w", "x.md"),
                ("hash-object", "--stdin-paths", "-w"), ()):
        try:
            git(tmp_path, *bad)
        except ValueError:
            continue
        raise AssertionError(f"git {bad} was not refused")


def test_the_audit_writes_nothing_to_the_object_store_or_the_index(tmp_path):
    k, first = _repo(tmp_path)
    (k / "base" / "domain" / "alpha.md").rename(k / "base" / "domain" / "alpha-term.md")
    objects = _g(tmp_path, "count-objects", "-v")
    index = (tmp_path / ".git" / "index").read_bytes()
    audit(k, first)
    assert _g(tmp_path, "count-objects", "-v") == objects and (tmp_path / ".git" / "index").read_bytes() == index


# --- concepts edited after their instance closed (standard §2.2, ADR-0039 decision 9) ---
_KINDS = ("---\ntype: Domain Profile\ntitle: DP\ndescription: DP.\nstatus: draft\nkinds:\n"
          "  Request: { extends: Operational Bundle, description: A request, directory: requests/, states: [in-review] }\n"
          "  Release: { extends: Operational Bundle, description: A release, directory: releases/, holds: [Request] }\n"
          "generated: { by: human:test, at: 2026-11-01T00:00:00Z }\n---\n\n# What this bundle holds\n\nText.\n")
_ROOT = '---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n{}---\n\n# Root\n'
_CLOSED = "state: closed\nclosed_at: 2026-11-10T10:00:00+00:00\n"
_LATER = ("edited after its instance closed: generated.at {} is later than closed_at {}; a closed instance is frozen: "
          "restore the concept as it was when it closed, or carry the change into the parent")


def _doc(at: str | None, type_: str = "Term") -> str:
    gen = f"generated: {{ by: human:test, at: {at} }}\n" if at is not None else ""
    return f"---\ntype: {type_}\ntitle: X\ndescription: X.\nstatus: draft\n{gen}---\n\n# Definition\n\nX.\n"


def _tree_files(instances: dict, kinds: bool = True) -> dict:
    """The files of a domain bundle (bundle path → text) holding instances {path: (root index keys, {doc: at})}; the
    kind is the instance's directory (requests/ Request, releases/ Release)."""
    files = {"index.md": _ROOT.format(""), "log.md": "# Bundle history\n"}
    if kinds:
        files["base/profile.md"] = _KINDS
    for rel, (keys, docs) in instances.items():
        kind = {"requests": "Request", "releases": "Release"}.get(rel.split("/")[-2], "Request")
        files[f"{rel}/index.md"] = _ROOT.format(f"kind: {kind}\n{keys}parent: ../..\n")
        files[f"{rel}/log.md"] = "# Bundle history\n"
        for doc, at in docs.items():
            files[f"{rel}/{doc}"] = _doc(at, "Project" if doc == "project.md" else "Term")
    return files


def _tree(tmp: Path, instances: dict, kinds: bool = True) -> Path:
    k = tmp / "knowledge"
    for rel, text in _tree_files(instances, kinds).items():
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
    return k


def _closed_edits(k: Path) -> list[dict]:
    return [f for f in audit(k, None)["findings"] if f["code"] == "EDITED_AFTER_CLOSE"]


def _one(tmp: Path, keys: str, at: str | None) -> list[dict]:
    return _closed_edits(_tree(tmp, {"requests/r": (keys, {"base/x.md": at})}))


def test_a_concept_edited_after_its_instance_closed_is_a_finding(tmp_path):
    assert _one(tmp_path / "a", _CLOSED, "2026-11-10T11:00:00Z") == [
        {"code": "EDITED_AFTER_CLOSE", "level": "WARN", "path": "requests/r/base/x.md", "instance": "requests/r/",
         "message": _LATER.format("2026-11-10T11:00:00+00:00", "2026-11-10T10:00:00+00:00")}]
    later = "2026-11-10T11:00:00Z"
    k = _tree(tmp_path / "b", {"requests/r": (_CLOSED, {"project.md": later, "fragments/f.md": later,
                                                         "base/x.md": later})})
    assert _codes({"findings": _closed_edits(k)}) == [
        ("EDITED_AFTER_CLOSE", "requests/r/project.md"), ("EDITED_AFTER_CLOSE", "requests/r/base/x.md"),
        ("EDITED_AFTER_CLOSE", "requests/r/fragments/f.md")]


def test_an_edit_at_or_before_closed_at_is_no_finding(tmp_path):
    assert _one(tmp_path / "equal", _CLOSED, "2026-11-10T10:00:00Z") == []
    assert _one(tmp_path / "earlier", _CLOSED, "2026-11-10T09:59:59Z") == []


def test_closed_edits_compare_instants_across_offsets(tmp_path):
    assert _one(tmp_path / "same", _CLOSED, "2026-11-10T12:00:00+02:00") == []
    assert [f["message"] for f in _one(tmp_path / "later", _CLOSED, "2026-11-10T09:30:00-02:00")] == [
        _LATER.format("2026-11-10T09:30:00-02:00", "2026-11-10T10:00:00+00:00")]


def test_the_reserved_files_of_a_closed_instance_are_no_finding(tmp_path):
    later = "2026-11-10T11:00:00Z"
    gen = f"generated: {{ by: human:test, at: {later} }}\n"
    k = _tree(tmp_path, {"requests/r": (_CLOSED, {"base/x.md": later})})
    r = k / "requests" / "r"
    (r / "index.md").write_text(_ROOT.format(f"kind: Request\n{_CLOSED}parent: ../..\n{gen}"), encoding="utf-8")
    (r / "log.md").write_text(f"---\n{gen}---\n\n# Bundle history\n", encoding="utf-8")
    (r / "base" / "index.md").write_text(f"---\n{gen}---\n\n# base\n", encoding="utf-8")
    assert [(f["code"], f["path"]) for f in _closed_edits(k)] == [("EDITED_AFTER_CLOSE", "requests/r/base/x.md")]


def test_only_a_closed_instance_is_read(tmp_path):
    later = "2026-11-10T11:00:00Z"
    for i, keys in enumerate(("state: open\n", "state: in-review\n",
                              "state: open\nclosed_at: 2026-11-10T10:00:00+00:00\n",
                              "state: closed\n", "state: closed\nclosed_at: 2026-11-10\n")):
        assert _one(tmp_path / f"s{i}", keys, later) == [], keys
    assert _one(tmp_path / "nogen", _CLOSED, None) == []
    assert _one(tmp_path / "noniso", _CLOSED, "yesterday") == []
    no_kinds = _tree(tmp_path / "nokinds", {"requests/r": (_CLOSED, {"base/x.md": later})}, kinds=False)
    outside = _tree(tmp_path / "outside", {"requests/r": (_CLOSED, {"base/x.md": later}),
                                           "elsewhere/r": (_CLOSED, {"base/x.md": later})})
    (outside / "requests" / "r" / "base" / "x.md").write_text(_doc("2026-11-10T09:00:00Z"), encoding="utf-8")
    for k in (no_kinds, outside):
        r = audit(k, None)
        assert r["findings"] == [] and r["notices"] == ["the bundle is not in a git repository: git facts skipped"]


def test_nested_instances_are_read_against_their_own_closed_at(tmp_path):
    def nested(tmp: Path, at: str) -> list[dict]:
        return _closed_edits(_tree(tmp, {"releases/rel": (_CLOSED, {}),
                                         "releases/rel/requests/req": ("state: closed\nclosed_at: 2026-11-10T12:00:00Z\n",
                                                                       {"base/x.md": at})}))
    assert nested(tmp_path / "before", "2026-11-10T11:00:00Z") == []
    assert [(f["path"], f["instance"]) for f in nested(tmp_path / "after", "2026-11-10T13:00:00Z")] == [
        ("releases/rel/requests/req/base/x.md", "releases/rel/requests/req/")]


def test_closed_edits_need_no_git_or_reference(tmp_path, capsys):
    instances = {"requests/r": (_CLOSED, {"base/x.md": "2026-11-10T11:00:00Z"})}
    k = _tree(tmp_path / "plain", instances)
    r = audit(k, None)
    assert _codes(r) == [("EDITED_AFTER_CLOSE", "requests/r/base/x.md")]
    assert r["notices"] == ["the bundle is not in a git repository: git facts skipped"]
    assert main([str(k)]) == 0
    assert capsys.readouterr().out.rstrip("\n").split("\n")[-1] == (
        "1 findings (0 git facts, 1 edited after close); 0 earlier audits at reference none, 0 findings accepted as is")
    k, first = _repo(tmp_path / "repo", extra=_tree_files(instances))
    (k / "base" / "domain" / "alpha.md").unlink()
    _commit(tmp_path / "repo", "drop alpha")
    assert _codes(audit(k, first)) == [("DELETED_UNRECORDED", "base/domain/alpha.md"),
                                       ("EDITED_AFTER_CLOSE", "requests/r/base/x.md")]


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
