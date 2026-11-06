#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""okf_projection.py — Check a bundle's knowledge projections (ADR-0022, ADR-0031): each projection.yaml, the
dependency rule and drift by nature.

Usage:
    uv run okf_projection.py [path/to/bundle] [--json] [--strict] [--run-render] [--record-hashes SLUG]

- Reads every <bundle>/projections/<slug>/projection.yaml (hidden entries and plain files such as .gitkeep are
  ignored). Without a bundle, finds knowledge/ upwards from the current directory, as okf_audit.py does.
- Checks the keys of ADR-0022 decision 2 (PROJ_NO_MANIFEST, PROJ_BAD_YAML, PROJ_MISSING_KEY, PROJ_BAD_VALUE), that
  each ref exists (PROJ_REF_MISSING) and the dependency rule of decision 3 (PROJ_DEPENDENCY). A ref is a bundle path
  `/base/...` or `/projections/<slug>[/<file>]`; a projection ref takes the lifecycle of the projection it names.
- Drift by nature (decision 4), the warning PROJ_DRIFT: a composed ref whose SHA-256 (the file's bytes; for a
  projection directory, its content.md) is not the recorded one; a rendered projection whose `render`, run with
  --run-render, writes a file into $OKF_PROJECTION_OUT that differs from the file of the same relative path in the
  projection's directory, or that is absent there (or, inside git, not tracked there, unless the projection is
  transient, which is never committed). A render that fails or runs over 120 s is the error PROJ_RENDER_FAILED, its
  output's last lines masked as okf_lint masks a validator's; on a timeout the render's whole process group is killed.
- Without --run-render nothing is executed: rendered projections are listed under not_checked. Recomputable ones are
  listed under to_recompute, for a person; frozen ones under frozen, not checked for drift.
- --record-hashes SLUG writes each ref's current sha256 into a composed projection's projection.yaml in place, every
  other byte left as it was; exit 2, changing nothing, when the slug is not a composed projection, is frozen, its
  manifest has errors besides its sha256 values, or a ref is not a one-line `{ path: ..., sha256: ... }` flow map.
- Exit: 2 without a bundle; 1 if any error, or any warning with --strict; else 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_common import PROJECTIONS_DIR, find_bundle, yaml  # noqa: E402
from okf_lint import mask_secrets  # noqa: E402

MANIFEST = "projection.yaml"
CONTENT = "content.md"
LIFECYCLES = ("canonical", "deliverable", "transient")  # ordered from the most stable
NATURES = ("rendered", "composed", "recomputable")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REF_RE = re.compile(r"^/(?:base/[^/].*|projections/[^/]+(?:/.*)?)$")
RENDER_TIMEOUT = 120
KILL_WAIT = 5  # seconds to read what a killed render left, before its pipes are closed
RENDER_TAIL = 20  # last lines of a failed render's output kept in the finding
RENDER_OUTPUT_MAX = 2000
OUT_ENV = "OKF_PROJECTION_OUT"
RENDER_NOTICE = "render not run (use --run-render)"


class Refused(Exception):
    """--record-hashes refuses and changes nothing (exit 2)."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref_path(ref) -> object:
    return ref.get("path") if isinstance(ref, dict) else ref


def ref_target(bundle: Path, path: str) -> tuple[Path, str | None]:
    """The file or directory a ref names, and the slug of the projection it belongs to (None for /base/)."""
    parts = path.lstrip("/").split("/")
    return bundle.joinpath(*parts), (parts[1] if parts[0] == PROJECTIONS_DIR else None)


def hashed_file(bundle: Path, path: str) -> Path:
    """What a composed ref's hash is taken from: the file, or a projection directory's content.md."""
    target, slug = ref_target(bundle, path)
    return target / CONTENT if slug is not None and target.is_dir() else target


def slugs(bundle: Path) -> list[str]:
    root = bundle / PROJECTIONS_DIR
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))


def load_manifest(pdir: Path) -> tuple[dict | None, tuple[str, str] | None]:
    """The parsed manifest, or the (code, message) of why it cannot be read."""
    f = pdir / MANIFEST
    if not f.is_file():
        return None, ("PROJ_NO_MANIFEST", f"no {MANIFEST} in projections/{pdir.name}/")
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as e:
        return None, ("PROJ_BAD_YAML", f"{MANIFEST} is not valid YAML: {str(e).splitlines()[0]}")
    if not isinstance(data, dict):
        return None, ("PROJ_BAD_YAML", f"{MANIFEST} is not a mapping")
    return data, None


def _missing(m: dict, key: str) -> bool:
    return m.get(key) in (None, "", [], {})


def check_manifest(bundle: Path, slug: str, m: dict, lifecycles: dict[str, str | None]) -> list[dict]:
    """The findings of one parsed manifest; a finding about a ref's sha256 value carries sha_only=True."""
    out: list[dict] = []

    def add(code: str, message: str, sha_only: bool = False) -> None:
        f = {"code": code, "level": "ERROR", "slug": slug, "message": message}
        if sha_only:
            f["sha_only"] = True
        out.append(f)

    lifecycle, nature = m.get("lifecycle"), m.get("nature")
    for key in ("lifecycle", "nature", "intent"):
        if _missing(m, key):
            add("PROJ_MISSING_KEY", f"missing key '{key}'")
    if not _missing(m, "lifecycle") and lifecycle not in LIFECYCLES:
        add("PROJ_BAD_VALUE", f"lifecycle '{lifecycle}' is not one of {', '.join(LIFECYCLES)}")
    if not _missing(m, "nature") and nature not in NATURES:
        add("PROJ_BAD_VALUE", f"nature '{nature}' is not one of {', '.join(NATURES)}")
    if "frozen" in m and not isinstance(m["frozen"], bool):
        add("PROJ_BAD_VALUE", f"frozen '{m['frozen']}' is not a boolean (true or false)")
    if nature in ("rendered", "composed") and _missing(m, "refs"):
        add("PROJ_MISSING_KEY", f"missing key 'refs' (required on a {nature} projection)")
    if nature == "rendered":
        if _missing(m, "render"):
            add("PROJ_MISSING_KEY", "missing key 'render' (required on a rendered projection)")
        elif not isinstance(m["render"], str):
            add("PROJ_BAD_VALUE", "render is not a command (a string)")
    if lifecycle == "deliverable":
        versions = m.get("versions")
        if _missing(m, "versions"):
            add("PROJ_MISSING_KEY", "missing key 'versions' (required on a deliverable projection)")
        elif not isinstance(versions, list):
            add("PROJ_BAD_VALUE", "versions is not a list")
        else:
            for i, v in enumerate(versions):
                lacking = [k for k in ("version", "date") if not isinstance(v, dict) or _missing(v, k)]
                if lacking:
                    add("PROJ_BAD_VALUE", f"versions[{i}] has no {' or '.join(lacking)}")
    refs = m.get("refs")
    if refs in (None, ""):
        return out
    if not isinstance(refs, list):
        add("PROJ_BAD_VALUE", "refs is not a list")
        return out
    for i, ref in enumerate(refs):
        path = ref_path(ref)
        if not isinstance(path, str) or not REF_RE.match(path) or ".." in path.split("/"):
            add("PROJ_BAD_VALUE", f"refs[{i}] path '{path}' is not a bundle path under /base/ or /projections/")
            continue
        if isinstance(ref, dict) and "sha256" in ref:
            if not isinstance(ref["sha256"], str) or not SHA_RE.match(ref["sha256"]):
                add("PROJ_BAD_VALUE", f"refs[{i}].sha256 of {path} is not 64 lowercase hex characters", sha_only=True)
        elif nature == "composed":
            add("PROJ_MISSING_KEY", f"refs[{i}].sha256 missing for {path} (required on a composed projection)")
        target, ref_slug = ref_target(bundle, path)
        if ref_slug is not None and not (bundle / PROJECTIONS_DIR / ref_slug).is_dir():
            add("PROJ_REF_MISSING", f"refs[{i}] {path}: no projection '{ref_slug}'")
            continue
        if not target.exists():
            add("PROJ_REF_MISSING", f"refs[{i}] {path} does not exist")
            continue
        if nature == "composed" and not hashed_file(bundle, path).is_file():
            add("PROJ_REF_MISSING", f"refs[{i}] {path}: no file to hash"
                + (f" (no {CONTENT})" if ref_slug is not None else " (a directory)"))
            continue
        target_lc = lifecycles.get(ref_slug) if ref_slug is not None else None
        if (lifecycle in LIFECYCLES and target_lc in LIFECYCLES
                and LIFECYCLES.index(target_lc) > LIFECYCLES.index(lifecycle)):
            add("PROJ_DEPENDENCY", f"refs[{i}] {path}: a {lifecycle} projection cannot reference the {target_lc} "
                                   f"projection '{ref_slug}' (ADR-0022 decision 3)")
    return out


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, stdin=subprocess.DEVNULL,
                              check=False, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    except OSError:
        return None


def tracked_files(pdir: Path) -> set[str] | None:
    """The files git tracks in the projection's directory, relative to it; None outside a git work tree."""
    p = _git(pdir, "rev-parse", "--is-inside-work-tree")
    if p is None or p.returncode != 0 or p.stdout.strip() != b"true":
        return None
    p = _git(pdir, "ls-files", "-z", "--", ".")
    if p is None or p.returncode != 0:
        return None
    return {s.decode("utf-8", "replace") for s in p.stdout.split(b"\0") if s}


def _tail(text: str) -> str:
    out = mask_secrets("\n".join(text.strip().splitlines()[-RENDER_TAIL:]))
    return out[-RENDER_OUTPUT_MAX:] if len(out) > RENDER_OUTPUT_MAX else out


def _kill_group(proc: subprocess.Popen) -> None:
    """Kill the render and every process in its session; proc.kill() where there is no killpg. A descendant that left
    the session (setsid) is beyond it: _drain does not wait for it."""
    if hasattr(os, "killpg"):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except (ProcessLookupError, PermissionError):
            pass
    proc.kill()


def _drain(proc: subprocess.Popen) -> tuple[str, str]:
    """What a killed render wrote, read for at most KILL_WAIT seconds: a descendant that left its session may still
    hold the pipes open, so they are closed and the check goes on without the rest of its output."""
    try:
        return proc.communicate(timeout=KILL_WAIT)
    except subprocess.TimeoutExpired:
        for pipe in (proc.stdout, proc.stderr):
            if pipe is not None:
                pipe.close()
        try:
            proc.wait(timeout=KILL_WAIT)
        except subprocess.TimeoutExpired:
            pass
        return "", ""


def run_render(bundle: Path, slug: str, command: str, lifecycle: str | None = None) -> list[dict]:
    """Run a rendered projection's render into an empty directory and compare what it writes (ADR-0031 decision 2).
    A transient projection is never committed, so its files are not checked against git."""
    pdir = bundle / PROJECTIONS_DIR / slug
    findings: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="okf-projection-") as out:
        env = {**os.environ, OUT_ENV: out}
        why, output = None, ""
        try:
            proc = subprocess.Popen(command, shell=True, cwd=bundle, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, errors="replace", stdin=subprocess.DEVNULL,
                                    start_new_session=True)
        except OSError as e:
            why, output = "could not start", str(e)
        else:
            try:
                stdout, stderr = proc.communicate(timeout=RENDER_TIMEOUT)
                if proc.returncode != 0:
                    why, output = f"exit {proc.returncode}", stdout + stderr
            except subprocess.TimeoutExpired:
                _kill_group(proc)
                stdout, stderr = _drain(proc)
                why, output = f"timed out after {RENDER_TIMEOUT}s", (stdout or "") + (stderr or "")
        if why:
            tail = _tail(output)
            return [{"code": "PROJ_RENDER_FAILED", "level": "ERROR", "slug": slug,
                     "message": f"render failed ({why})" + (f": {tail}" if tail else "")}]
        written = sorted(f for f in Path(out).rglob("*") if f.is_file())
        tracked = tracked_files(pdir) if written and lifecycle != "transient" else None
        for f in written:
            rel = f.relative_to(out).as_posix()
            committed = pdir / rel
            if not committed.is_file():
                why = "is not in the projection's directory"
            elif tracked is not None and rel not in tracked:
                why = "is not committed in the projection's directory"
            elif committed.read_bytes() != f.read_bytes():
                why = "differs from the committed file"
            else:
                continue
            findings.append({"code": "PROJ_DRIFT", "level": "WARN", "slug": slug,
                             "message": f"rendered file {rel} {why}"})
    return findings


def composed_drift(bundle: Path, slug: str, m: dict) -> list[dict]:
    out = []
    for i, ref in enumerate(m["refs"]):
        now = sha256(hashed_file(bundle, ref["path"]))
        if now != ref["sha256"]:
            out.append({"code": "PROJ_DRIFT", "level": "WARN", "slug": slug,
                        "message": f"refs[{i}] {ref['path']} changed since its hash was recorded "
                                   f"(recorded {ref['sha256'][:12]}, now {now[:12]})"})
    return out


def check(bundle: Path, run_render_flag: bool = False) -> dict:
    report: dict = {"bundle": str(bundle), "projections": [], "findings": [], "not_checked": [],
                    "to_recompute": [], "frozen": [], "notices": []}
    found = slugs(bundle)
    manifests: dict[str, dict | None] = {}
    for slug in found:
        m, err = load_manifest(bundle / PROJECTIONS_DIR / slug)
        manifests[slug] = m
        if err:
            report["findings"].append({"code": err[0], "level": "ERROR", "slug": slug, "message": err[1]})
    lifecycles = {s: (m.get("lifecycle") if m else None) for s, m in manifests.items()}
    for slug in found:
        m = manifests[slug]
        frozen = bool(m and m.get("frozen") is True)
        report["projections"].append({"slug": slug, "lifecycle": m.get("lifecycle") if m else None,
                                      "nature": m.get("nature") if m else None, "frozen": frozen})
        if m is None:
            continue
        own = check_manifest(bundle, slug, m, lifecycles)
        report["findings"] += own
        nature = m.get("nature")
        if frozen:
            report["frozen"].append(slug)
            continue
        if nature == "recomputable":
            report["to_recompute"].append(slug)
            report["notices"].append(f"{slug} is recomputable: recompute it by hand, rerunning the procedure in its "
                                     f"{CONTENT}, and propose the difference for a person to approve")
            continue
        if own:
            continue  # a manifest with errors is not checked for drift
        if nature == "composed":
            report["findings"] += composed_drift(bundle, slug, m)
        elif nature == "rendered":
            if run_render_flag:
                report["findings"] += run_render(bundle, slug, m["render"], m.get("lifecycle"))
            else:
                report["not_checked"].append(slug)
    if report["not_checked"]:
        report["notices"].insert(0, f"{len(report['not_checked'])} rendered projection(s) not checked for drift: "
                                    f"{RENDER_NOTICE}")
    for f in report["findings"]:
        f.pop("sha_only", None)
    return report


def record_hashes(bundle: Path, slug: str) -> list[tuple[str, str]]:
    """Write each ref's current sha256 into projections/<slug>/projection.yaml in place; returns (path, sha256)."""
    pdir = bundle / PROJECTIONS_DIR / slug
    if slug not in slugs(bundle):
        raise Refused(f"no projection '{slug}' in {bundle / PROJECTIONS_DIR}")
    m, err = load_manifest(pdir)
    if err:
        raise Refused(f"{slug}: {err[1]}")
    if m.get("nature") != "composed":
        raise Refused(f"{slug} is not a composed projection (nature: {m.get('nature')}): only a composed one "
                      "records hashes")
    if m.get("frozen") is True:
        raise Refused(f"{slug} is frozen: it keeps its last state")
    lifecycles = {s: (mm.get("lifecycle") if mm else None) for s in slugs(bundle)
                  for mm in [load_manifest(bundle / PROJECTIONS_DIR / s)[0]]}
    errors = [f for f in check_manifest(bundle, slug, m, lifecycles) if not f.get("sha_only")]
    if errors:
        raise Refused(f"{slug}: fix its manifest first: " + "; ".join(f"{f['code']} {f['message']}" for f in errors))
    f = pdir / MANIFEST
    text = f.read_bytes().decode("utf-8")
    root = yaml.compose(text)
    refs_node = next(v for k, v in root.value if isinstance(k, yaml.ScalarNode) and k.value == "refs")
    edits, recorded = [], []
    for i, (item, ref) in enumerate(zip(refs_node.value, m["refs"])):
        keys = ([k.value for k, _ in item.value] if isinstance(item, yaml.MappingNode) else [])
        if (not isinstance(item, yaml.MappingNode) or not item.flow_style or sorted(keys) != ["path", "sha256"]
                or item.start_mark.line != item.end_mark.line):
            raise Refused(f"{slug}: refs[{i}] {ref_path(ref)} is not a one-line {{ path: ..., sha256: ... }} flow map")
        node = next(v for k, v in item.value if k.value == "sha256")
        if not isinstance(node, yaml.ScalarNode):
            raise Refused(f"{slug}: refs[{i}] {ref['path']}: sha256 is not a scalar")
        now = sha256(hashed_file(bundle, ref["path"]))
        quote = node.style if node.style in ('"', "'") else ('"' if now.isdigit() else "")  # all digits reads as a number
        edits.append((node.start_mark.index, node.end_mark.index, f"{quote}{now}{quote}"))
        recorded.append((ref["path"], now))
    for start, end, new in sorted(edits, reverse=True):
        text = text[:start] + new + text[end:]
    after = yaml.safe_load(text)
    assert [r["sha256"] for r in after["refs"]] == [h for _, h in recorded], "record-hashes produced other values"
    f.write_bytes(text.encode("utf-8"))
    return recorded


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check knowledge projections: projection.yaml, dependencies and drift.")
    ap.add_argument("bundle", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings (PROJ_DRIFT) too")
    ap.add_argument("--run-render", action="store_true",
                    help="run each rendered projection's render command (only when a person asks)")
    ap.add_argument("--record-hashes", metavar="SLUG", help="write a composed projection's current ref hashes")
    a = ap.parse_args(argv)
    bundle = Path(a.bundle).resolve() if a.bundle else find_bundle()
    if bundle is None or not (bundle / "index.md").is_file():
        print("no OKF bundle found (knowledge/index.md)", file=sys.stderr)
        return 2
    if a.record_hashes:
        try:
            recorded = record_hashes(bundle, a.record_hashes)
        except Refused as e:
            print(f"okf_projection: {e}; nothing changed", file=sys.stderr)
            return 2
        for path, h in recorded:
            print(f"recorded {path} {h}")
        print(f"{len(recorded)} hashes recorded in projections/{a.record_hashes}/{MANIFEST}")
        return 0
    report = check(bundle, a.run_render)
    errors = [f for f in report["findings"] if f["level"] == "ERROR"]
    warnings = [f for f in report["findings"] if f["level"] == "WARN"]
    if a.json:
        print(json.dumps({k: v for k, v in report.items() if k != "bundle"}, ensure_ascii=False, indent=2))
    else:
        for n in report["notices"]:
            print(f"NOTICE {n}")
        for f in report["findings"]:
            print(f"{f['level']} {f['code']} {f['slug']}: {f['message']}")
        for key in ("not_checked", "to_recompute", "frozen"):
            if report[key]:
                print(f"{key}: {', '.join(report[key])}")
        print(f"{len(report['projections'])} projections · {len(errors)} errors · {len(warnings)} warnings")
    return 1 if errors or (a.strict and warnings) else 0


# --------------------------------------------------------------------------
# Tests (uv run --with pytest okf_projection.py --test): each builds a temporary bundle
# --------------------------------------------------------------------------
_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def _bundle(tmp: Path, projections: dict | None = None, files: dict | None = None) -> Path:
    """A bundle with a term in base/ and the given projections (slug → projection.yaml text, or a dict of
    file → text inside the projection's directory) and extra files (bundle path → text)."""
    k = tmp / "knowledge"
    (k / "base" / "domain").mkdir(parents=True)
    (k / "index.md").write_text('---\nokf_version: "0.2"\nokf_profile: "knowledge/3.0"\n---\n\n# Root\n', encoding="utf-8")
    (k / "base" / "domain" / "alpha.md").write_text("---\ntype: Term\ntitle: Alpha\n---\n\nAlpha.\n", encoding="utf-8")
    (k / "projections").mkdir()
    for slug, spec in (projections or {}).items():
        d = k / "projections" / slug
        d.mkdir(parents=True)
        for name, text in ({MANIFEST: spec} if isinstance(spec, str) else spec).items():
            (d / name).parent.mkdir(parents=True, exist_ok=True)
            (d / name).write_text(text, encoding="utf-8")
    for rel, text in (files or {}).items():
        (k / rel).parent.mkdir(parents=True, exist_ok=True)
        (k / rel).write_text(text, encoding="utf-8")
    return k


def _sha(k: Path, rel: str) -> str:
    return sha256(k / rel)


def _codes(r: dict) -> list[tuple[str, str]]:
    return [(f["code"], f["slug"]) for f in r["findings"]]


def _canonical(refs: str = "[/base/domain/alpha.md]", nature: str = "rendered", extra: str = "") -> str:
    return (f"lifecycle: canonical\nnature: {nature}\nintent: For readers.\nrefs: {refs}\n"
            + ("render: 'true'\n" if nature == "rendered" else "") + extra)


def test_no_projections_or_an_empty_directory_is_zero_projections(tmp_path, capsys):
    k = _bundle(tmp_path)
    (k / "projections" / ".gitkeep").write_text("", encoding="utf-8")
    (k / "projections" / ".hidden").mkdir()
    assert main([str(k)]) == 0
    assert "0 projections" in capsys.readouterr().out
    (k / "projections" / ".gitkeep").unlink()
    (k / "projections" / ".hidden").rmdir()
    (k / "projections").rmdir()
    assert main([str(k)]) == 0
    assert "0 projections" in capsys.readouterr().out


def test_a_directory_without_projection_yaml_is_proj_no_manifest(tmp_path):
    k = _bundle(tmp_path, {"glossary": {CONTENT: "# Glossary\n"}})
    assert _codes(check(k)) == [("PROJ_NO_MANIFEST", "glossary")]
    assert main([str(k)]) == 1


def test_invalid_yaml_or_not_a_mapping_is_proj_bad_yaml(tmp_path):
    k = _bundle(tmp_path, {"broken": "lifecycle: [canonical\n", "listed": "- a\n- b\n"})
    assert _codes(check(k)) == [("PROJ_BAD_YAML", "broken"), ("PROJ_BAD_YAML", "listed")]


def test_missing_keys_are_proj_missing_key_naming_the_key(tmp_path):
    k = _bundle(tmp_path, {
        "bare": "intent: x\n",
        "rendered": "lifecycle: canonical\nnature: rendered\nintent: x\n",
        "composed": "lifecycle: canonical\nnature: composed\nintent: x\n",
        "deliverable": "lifecycle: deliverable\nnature: recomputable\nintent: x\n",
        "no-intent": "lifecycle: canonical\nnature: recomputable\n",
    })
    msgs = {(f["slug"], f["message"].split("'")[1]) for f in check(k)["findings"] if f["code"] == "PROJ_MISSING_KEY"}
    assert msgs == {("bare", "lifecycle"), ("bare", "nature"), ("rendered", "refs"), ("rendered", "render"),
                    ("composed", "refs"), ("deliverable", "versions"), ("no-intent", "intent")}


def test_bad_values_are_proj_bad_value(tmp_path):
    k = _bundle(tmp_path, {
        "lc": "lifecycle: forever\nnature: recomputable\nintent: x\n",
        "nat": "lifecycle: canonical\nnature: drawn\nintent: x\n",
        "frz": "lifecycle: canonical\nnature: recomputable\nintent: x\nfrozen: 'yes'\n",
        "ref": _canonical("[/elsewhere/x.md, base/domain/alpha.md, /base/../index.md]"),
        "sha": _canonical("[{ path: /base/domain/alpha.md, sha256: ABC }]", nature="composed"),
        "ver": "lifecycle: deliverable\nnature: recomputable\nintent: x\nversions: [{ version: 1 }, { date: 2026-11-01 }]\n",
    })
    bad = [(f["slug"], f["message"]) for f in check(k)["findings"]]
    assert all(code == "PROJ_BAD_VALUE" for code, _ in _codes(check(k))), bad
    assert sorted(s for s, _ in bad) == ["frz", "lc", "nat", "ref", "ref", "ref", "sha", "ver", "ver"]


def test_a_composed_ref_without_sha256_is_proj_missing_key(tmp_path):
    k = _bundle(tmp_path, {"c": _canonical("[/base/domain/alpha.md]", nature="composed")})
    [f] = check(k)["findings"]
    assert f["code"] == "PROJ_MISSING_KEY" and f["message"].startswith("refs[0].sha256")


def test_a_ref_to_a_missing_path_or_projection_is_proj_ref_missing(tmp_path):
    k = _bundle(tmp_path, {
        "a": _canonical("[/base/domain/gone.md]"),
        "b": _canonical("[/projections/nowhere]"),
        "c": _canonical("[/projections/a/missing.md]"),
        "d": _canonical("[/projections/a, /projections/a/, /projections/a/projection.yaml, /base/domain]"),
    })
    assert _codes(check(k)) == [("PROJ_REF_MISSING", "a"), ("PROJ_REF_MISSING", "b"), ("PROJ_REF_MISSING", "c")]


def test_the_dependency_rule_is_proj_dependency(tmp_path):
    def p(lc: str, refs: str = "[/base/domain/alpha.md]") -> str:
        return (f"lifecycle: {lc}\nnature: recomputable\nintent: x\nrefs: {refs}\n"
                + ("versions: [{ version: '1', date: 2026-11-01 }]\n" if lc == "deliverable" else ""))
    k = _bundle(tmp_path, {
        "can": p("canonical"), "del": p("deliverable"), "tra": p("transient"),
        "can-del": p("canonical", "[/projections/del]"),
        "can-tra": p("canonical", "[/projections/tra/content.md]"),
        "del-tra": p("deliverable", "[/projections/tra]"),
        "can-can": p("canonical", "[/projections/can]"),
        "del-can-del": p("deliverable", "[/projections/can, /projections/del]"),
        "tra-all": p("transient", "[/projections/can, /projections/del, /projections/tra]"),
    }, files={"projections/tra/content.md": "x\n"})
    assert sorted(_codes(check(k))) == [("PROJ_DEPENDENCY", "can-del"), ("PROJ_DEPENDENCY", "can-tra"),
                                        ("PROJ_DEPENDENCY", "del-tra")]


def test_composed_drift_is_a_proj_drift_warning_naming_the_ref(tmp_path, capsys):
    k = _bundle(tmp_path, {"src": {MANIFEST: "lifecycle: canonical\nnature: recomputable\nintent: x\n",
                                   CONTENT: "procedure\n"}})
    alpha, src = _sha(k, "base/domain/alpha.md"), _sha(k, "projections/src/content.md")
    (k / "projections" / "c").mkdir()
    (k / "projections" / "c" / MANIFEST).write_text(_canonical(
        f"\n  - {{ path: /base/domain/alpha.md, sha256: {alpha} }}\n  - {{ path: /projections/src, sha256: {src} }}",
        nature="composed"), encoding="utf-8")
    assert check(k)["findings"] == []
    (k / "projections" / "src" / CONTENT).write_text("procedure, changed\n", encoding="utf-8")
    [f] = check(k)["findings"]
    assert (f["code"], f["level"], f["slug"]) == ("PROJ_DRIFT", "WARN", "c") and "/projections/src" in f["message"]
    assert main([str(k)]) == 0 and main([str(k), "--strict"]) == 1
    capsys.readouterr()


def test_without_run_render_nothing_runs_and_the_projection_is_not_checked(tmp_path, capsys):
    marker = tmp_path / "ran"
    k = _bundle(tmp_path, {"r": _canonical().replace("render: 'true'", f"render: touch {marker}")})
    r = check(k)
    assert r["not_checked"] == ["r"] and r["findings"] == []
    assert [n for n in r["notices"] if RENDER_NOTICE in n] == r["notices"] and len(r["notices"]) == 1
    assert main([str(k)]) == 0 and main([str(k), "--json"]) == 0
    assert not marker.exists()
    check(k, run_render_flag=True)
    assert marker.exists()  # the same command does run with the flag
    capsys.readouterr()


def test_run_render_compares_what_it_writes_with_the_projection(tmp_path):
    cmd = "mkdir -p \"$OKF_PROJECTION_OUT/deliverables\" && cp base/domain/alpha.md \"$OKF_PROJECTION_OUT/deliverables/alpha.md\""
    k = _bundle(tmp_path, {"r": _canonical(extra="").replace("render: 'true'", f"render: '{cmd}'")})
    out = k / "projections" / "r" / "deliverables" / "alpha.md"
    out.parent.mkdir()
    out.write_bytes((k / "base" / "domain" / "alpha.md").read_bytes())
    r = check(k, run_render_flag=True)
    assert r["findings"] == [] and r["not_checked"] == []
    out.write_text("edited by hand\n", encoding="utf-8")
    [f] = check(k, run_render_flag=True)["findings"]
    assert (f["code"], f["level"]) == ("PROJ_DRIFT", "WARN") and "deliverables/alpha.md differs" in f["message"]
    out.unlink()
    [f] = check(k, run_render_flag=True)["findings"]
    assert f["code"] == "PROJ_DRIFT" and "is not in the projection's directory" in f["message"]


def test_run_render_inside_git_flags_a_file_that_is_not_committed(tmp_path, monkeypatch):
    for key, v in _ENV.items():
        monkeypatch.setenv(key, v)
    k = _bundle(tmp_path, {"r": _canonical().replace("render: 'true'", "render: 'echo hi > \"$OKF_PROJECTION_OUT/out.txt\"'")})
    (k / "projections" / "r" / "out.txt").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    [f] = check(k, run_render_flag=True)["findings"]
    assert f["code"] == "PROJ_DRIFT" and "out.txt is not committed" in f["message"]
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    assert check(k, run_render_flag=True)["findings"] == []


def test_run_render_inside_git_does_not_ask_a_transient_projection_to_be_committed(tmp_path, monkeypatch):
    for key, v in _ENV.items():
        monkeypatch.setenv(key, v)
    render = "render: 'echo hi > \"$OKF_PROJECTION_OUT/out.txt\"'"
    k = _bundle(tmp_path, {
        "can": _canonical().replace("render: 'true'", render),
        "tra": _canonical().replace("lifecycle: canonical", "lifecycle: transient").replace("render: 'true'", render),
    })
    for slug in ("can", "tra"):
        (k / "projections" / slug / "out.txt").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    [f] = check(k, run_render_flag=True)["findings"]
    assert (f["code"], f["slug"]) == ("PROJ_DRIFT", "can") and "out.txt is not committed" in f["message"]
    (k / "projections" / "tra" / "out.txt").write_text("edited\n", encoding="utf-8")
    assert [(f["slug"], "differs" in f["message"]) for f in check(k, run_render_flag=True)["findings"]] == [
        ("can", False), ("tra", True)]  # a transient render is still compared byte for byte
    (k / "projections" / "tra" / "out.txt").unlink()
    assert [(f["slug"], "is not in the projection's directory" in f["message"])
            for f in check(k, run_render_flag=True)["findings"]] == [("can", False), ("tra", True)]


def test_a_failing_or_slow_render_is_proj_render_failed_with_its_output_masked(tmp_path, monkeypatch):
    k = _bundle(tmp_path, {"r": _canonical().replace(
        "render: 'true'", "render: 'echo token=FAKE-TOKEN-0001; echo boom >&2; exit 3'")})
    [f] = check(k, run_render_flag=True)["findings"]
    assert (f["code"], f["level"]) == ("PROJ_RENDER_FAILED", "ERROR") and "exit 3" in f["message"]
    assert "boom" in f["message"] and "FAKE-TOKEN-0001" not in f["message"] and "token=[masked]" in f["message"]
    monkeypatch.setattr(sys.modules[__name__], "RENDER_TIMEOUT", 1)
    (k / "projections" / "r" / MANIFEST).write_text(_canonical().replace("render: 'true'", "render: 'sleep 5'"),
                                                    encoding="utf-8")
    [f] = check(k, run_render_flag=True)["findings"]
    assert f["code"] == "PROJ_RENDER_FAILED" and "timed out" in f["message"]


def _alive(pid: int) -> bool:
    """Whether pid is still running, waiting up to 2 s for a killed process to be reaped (a zombie is not alive)."""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        if not state or state.startswith("Z"):
            return False
        time.sleep(0.05)
    return True


def test_a_render_timeout_kills_the_processes_the_render_started(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "RENDER_TIMEOUT", 1)
    pidfile = tmp_path / "child.pid"
    k = _bundle(tmp_path, {"r": _canonical().replace(
        "render: 'true'", f"render: \"sh -c 'echo $$ > {pidfile}; exec sleep 30' & wait\"")})
    [f] = check(k, run_render_flag=True)["findings"]
    assert f["code"] == "PROJ_RENDER_FAILED" and "timed out after 1s" in f["message"]
    assert not _alive(int(pidfile.read_text().strip()))


def test_a_descendant_that_left_the_session_does_not_hold_the_check(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "RENDER_TIMEOUT", 1)
    monkeypatch.setattr(sys.modules[__name__], "KILL_WAIT", 1)
    pidfile = tmp_path / "escaped.pid"
    escape = f"import os, time; os.setsid(); open({str(pidfile)!r}, 'w').write(str(os.getpid())); time.sleep(30)"
    render = "render: " + json.dumps(f"{sys.executable} -c \"{escape}\" & wait")
    k = _bundle(tmp_path, {"r": _canonical().replace("render: 'true'", render)})
    start = time.monotonic()
    try:
        [f] = check(k, run_render_flag=True)["findings"]
        elapsed = time.monotonic() - start
    finally:
        if pidfile.exists():
            os.kill(int(pidfile.read_text().strip()), signal.SIGKILL)
    assert f["code"] == "PROJ_RENDER_FAILED" and "timed out after 1s" in f["message"]
    assert elapsed < 6, elapsed  # 1 s timeout + at most 2 x KILL_WAIT, not the descendant's 30 s


def test_recomputable_is_validated_and_listed_to_recompute(tmp_path):
    k = _bundle(tmp_path, {"m": "lifecycle: canonical\nnature: recomputable\nintent: x\n",
                           "bad": "lifecycle: canonical\nnature: recomputable\nintent: x\nrefs: [/base/nope.md]\n"})
    r = check(k)
    assert r["to_recompute"] == ["bad", "m"] and _codes(r) == [("PROJ_REF_MISSING", "bad")]
    assert len([n for n in r["notices"] if "recompute it by hand" in n]) == 2


def test_frozen_is_validated_not_checked_for_drift_and_listed(tmp_path):
    stale = "a" * 64
    k = _bundle(tmp_path, {
        "c": _canonical(f"[{{ path: /base/domain/alpha.md, sha256: {stale} }}]", nature="composed", extra="frozen: true\n"),
        "r": _canonical(extra="frozen: true\n").replace("render: 'true'", "render: 'exit 1'"),
        "bad": "lifecycle: canonical\nnature: composed\nintent: x\nfrozen: true\n",
    })
    r = check(k, run_render_flag=True)
    assert r["frozen"] == ["bad", "c", "r"] and r["not_checked"] == []
    assert _codes(r) == [("PROJ_MISSING_KEY", "bad")]


MANIFEST_TEXT = ("# A glossary for new joiners\r\nlifecycle: canonical   # stays\r\nnature: composed\r\n"
                 "intent: >\r\n  For new joiners.\r\nrefs:\r\n"
                 "  - { path: /base/domain/alpha.md, sha256: \"" + "0" * 64 + "\" }  # the term\r\n"
                 "  - {path: '/projections/src',sha256: " + "1" * 64 + "}\r\n"
                 "owner: me\r\n")


def test_record_hashes_replaces_only_the_hash_values_byte_for_byte(tmp_path, capsys):
    k = _bundle(tmp_path, {"g": MANIFEST_TEXT,
                           "src": {MANIFEST: "lifecycle: canonical\nnature: recomputable\nintent: x\n", CONTENT: "p\n"}})
    f = k / "projections" / "g" / MANIFEST
    f.write_bytes(MANIFEST_TEXT.encode("utf-8"))  # CRLF kept as written
    alpha, src = _sha(k, "base/domain/alpha.md"), _sha(k, "projections/src/content.md")
    assert main([str(k), "--record-hashes", "g"]) == 0
    expected = MANIFEST_TEXT.replace("0" * 64, alpha).replace("1" * 64, src).encode("utf-8")
    assert f.read_bytes() == expected
    assert check(k)["findings"] == []
    capsys.readouterr()


def test_record_hashes_refuses_and_changes_nothing(tmp_path, capsys):
    block = "lifecycle: canonical\nnature: composed\nintent: x\nrefs:\n  - path: /base/domain/alpha.md\n    sha256: " + "0" * 64 + "\n"
    multi = "lifecycle: canonical\nnature: composed\nintent: x\nrefs:\n  - { path: /base/domain/alpha.md,\n      sha256: " + "0" * 64 + " }\n"
    k = _bundle(tmp_path, {
        "block": block, "multi": multi,
        "r": _canonical(f"[{{ path: /base/domain/alpha.md, sha256: {'0' * 64} }}]"),
        "frz": _canonical(f"[{{ path: /base/domain/alpha.md, sha256: {'0' * 64} }}]", nature="composed", extra="frozen: true\n"),
        "gone": _canonical(f"[{{ path: /base/domain/gone.md, sha256: {'0' * 64} }}]", nature="composed"),
    })
    before = {p: p.read_bytes() for p in (k / "projections").rglob(MANIFEST)}
    for slug in ("block", "multi", "r", "frz", "gone", "nowhere"):
        assert main([str(k), "--record-hashes", slug]) == 2, slug
    err = capsys.readouterr().err
    assert "refs[0] /base/domain/alpha.md is not a one-line" in err and "nothing changed" in err
    assert "r is not a composed projection (nature: rendered)" in err
    assert {p: p.read_bytes() for p in (k / "projections").rglob(MANIFEST)} == before


def test_record_hashes_fills_a_placeholder_hash(tmp_path, capsys):
    k = _bundle(tmp_path, {"c": _canonical("[{ path: /base/domain/alpha.md, sha256: TODO }]", nature="composed")})
    assert check(k)["findings"][0]["code"] == "PROJ_BAD_VALUE"
    assert main([str(k), "--record-hashes", "c"]) == 0
    assert check(k)["findings"] == []
    capsys.readouterr()


def test_json_shape_and_exit(tmp_path, capsys):
    k = _bundle(tmp_path, {"m": "lifecycle: canonical\nnature: recomputable\nintent: x\n",
                           "r": _canonical(), "x": {CONTENT: "no manifest\n"}})
    assert main([str(k), "--json"]) == 1
    d = json.loads(capsys.readouterr().out)
    assert set(d) == {"projections", "findings", "not_checked", "to_recompute", "frozen", "notices"}
    assert d["projections"][0] == {"slug": "m", "lifecycle": "canonical", "nature": "recomputable", "frozen": False}
    assert d["findings"] == [{"code": "PROJ_NO_MANIFEST", "level": "ERROR", "slug": "x",
                              "message": "no projection.yaml in projections/x/"}]
    assert d["not_checked"] == ["r"] and d["to_recompute"] == ["m"] and d["frozen"] == []


def test_no_bundle_is_exit_2(tmp_path, capsys):
    assert main([str(tmp_path)]) == 2
    assert "no OKF bundle found" in capsys.readouterr().err


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        from okf_common import run_tests

        sys.exit(run_tests(__file__, [a for a in sys.argv[1:] if a != "--test"]))
    sys.exit(main())
