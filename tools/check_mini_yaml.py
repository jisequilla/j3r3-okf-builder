#!/usr/bin/env python3
"""Differential check of the dependency-free YAML parser against PyYAML.

    python3 tools/check_mini_yaml.py knowledge examples   # every *.md frontmatter
    python3 tools/check_mini_yaml.py --self-test          # inline behaviour cases

Stdlib only. Timestamps are compared as ISO-8601 values: PyYAML turns unquoted
timestamps into datetime objects, while the mini parser keeps them as strings.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugin/okf-builder/skills/okf-standard/scripts"))

from okf_common import _mini_yaml, split_frontmatter  # noqa: E402

try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001
    yaml = None

CASES: list[tuple[str, str, dict]] = [
    ("plain multi-line scalar",
     "description: This dataset contains\n  the full history.\n",
     {"description": "This dataset contains the full history."}),
    ("folded >", "description: >\n  Folded line one\n  line two\n",
     {"description": "Folded line one line two\n"}),
    ("folded >-", "description: >-\n  Folded\n  text\n", {"description": "Folded text"}),
    ("literal |", "body: |\n  line one\n  line two\n", {"body": "line one\nline two\n"}),
    ("literal |-", "body: |-\n  line one\n  line two\n", {"body": "line one\nline two"}),
    ("wrapped list item", "items:\n- item that wraps\n  onto two lines\n",
     {"items": ["item that wraps onto two lines"]}),
    ("flow map and list", "a: { x: 1, y: two }\nb: [1, two, 'three']\n",
     {"a": {"x": 1, "y": "two"}, "b": [1, "two", "three"]}),
    ("nested map", "outer:\n  inner:\n    leaf: v\n  other: 2\n",
     {"outer": {"inner": {"leaf": "v"}, "other": 2}}),
    ("list of maps", "sources:\n- uri: a\n  kind: doc\n- uri: b\n",
     {"sources": [{"uri": "a", "kind": "doc"}, {"uri": "b"}]}),
    ("quoted scalars", "a: \"x: y\"\nb: 'z # w'\n", {"a": "x: y", "b": "z # w"}),
    ("comments", "# head\na: 1  # trailing\nb: true\n", {"a": 1, "b": True}),
    ("multi-line double-quoted with #", "description: \"A long text\n  with a #hashtag inside\"\n",
     {"description": "A long text with a #hashtag inside"}),
    ("multi-line single-quoted with #", "a: 'one\n  two #x'\nb: 1\n", {"a": "one two #x", "b": 1}),
    ("quoted line that looks like a comment", "a: \"one\n  # two\"\n", {"a": "one # two"}),
    ("multi-line quoted list item", "items:\n- \"one\n  two #x\"\n- b\n", {"items": ["one two #x", "b"]}),
    ("folded > keeps leading blank line", "a: >\n\n  x\n  y\n", {"a": "\nx y\n"}),
    ("folded >- keeps leading blank lines", "a: >-\n\n\n  x\n", {"a": "\n\nx"}),
    ("literal | keeps more-indented blank line", "a: |\n  x\n    \n  y\n", {"a": "x\n  \ny\n"}),
    ("folded > keeps more-indented blank line", "a: >\n  x\n    \n  y\n", {"a": "x\n  \ny\n"}),
    ("folded > around a more-indented line", "a: >\n  x\n   y\n  z\n  w\n", {"a": "x\n y\nz w\n"}),
    ("block scalar at end of text", "a: |\n  x", {"a": "x"}),
    ("tab after the block indent is content", "a: |\n  \tx\n", {"a": "\tx\n"}),
    ("single-quoted ''", "a: 'it''s'\n", {"a": "it's"}),
    ("multi-line single-quoted ''", "a: 'it''s\n  ok'\n", {"a": "it's ok"}),
    ("double-quoted \\\"", "a: \"x\\\"y\"\n", {"a": "x\"y"}),
    ("double-quoted \\t", "a: \"tab\\there\"\n", {"a": "tab\there"}),
    ("double-quoted \\n", "a: \"nl\\nhere\"\n", {"a": "nl\nhere"}),
    ("double-quoted \\\\", "a: \"back\\\\slash\"\n", {"a": "back\\slash"}),
    ("double-quoted \\/ \\r \\0", "a: \"s\\/l\\rr\\0z\"\n", {"a": "s/l\rr\0z"}),
    ("double-quoted \\uXXXX", "a: \"\\u00e9\"\n", {"a": "é"}),
    ("double-quoted \\\" before a comment", "a: \"x\\\" # y\"  # c\n", {"a": "x\" # y"}),
    ("literal tab inside double quotes", "a: \"x\ty\"\n", {"a": "x\ty"}),
]

# (text, substring the ValueError message must contain)
UNSUPPORTED: list[tuple[str, str]] = [
    ("a: |+\n  x\n", "bloque"), ("a: |2\n  x\n", "bloque"), ("a: >+\n  x\n", "bloque"),
    ("a: >2\n  x\n", "bloque"), ("a: |-2\n  x\n", "bloque"),
    ("---\na: 1\n", "multidocumento"), ("a: 1\n...\n", "multidocumento"),
    ("a: &x 1\n", "anclas"), ("a: &x\n  b: 1\n", "anclas"), ("a: !!str 1\n", "tags"), ("a: *x\n", "alias"),
    ("a: \"one\n  two\nb: 1\n", "sin cerrar"), ("a: 'one\n  two\n", "sin cerrar"), ("a: [1,\n  2\n", "sin cerrar"),
    ("a: \"one\\\n  two\"\n", "salto de línea escapado"),
    ("a: \"\\x41\"\n", "\\x"), ("a: \"\\e\"\n", "\\e"), ("a: \"\\U0001F600\"\n", "\\U"),
    ("a: \"\\N\"\n", "\\N"), ("a: \"\\_\"\n", "\\_"), ("a: \"\\ud800\"\n", "surrogate"), ("a: \"\\u12\"\n", "\\u"),
    ("a: one\n\ttwo\n", "tab"), ("a:\n\tb: 1\n", "tab"), ("a: \"one\n\ttwo\"\n", "tab"),
    ("a: |\n  x\n\t\n  y\n", "tab"), ("a: |\n    \n  x\n", "solo espacios"),
    ("a: {x: 1,\n  y: 2}\n", "flujo"),
    ("a: \"x\" y\n  z\n", "comilla de cierre"), ("a: \"x\" y\n", "comilla de cierre"), ("a: 'x\n", "sin cerrar"),
    ("a: ['x' y]\n", "comilla de cierre"),
]


def _norm(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    return v


def _norm_mini(mini: Any, ref: Any) -> Any:
    """Normalise mini-parser strings that PyYAML read as timestamps."""
    if isinstance(ref, (datetime, date)) and isinstance(mini, str):
        try:
            parsed = (datetime if isinstance(ref, datetime) else date).fromisoformat(
                mini.replace("Z", "+00:00") if isinstance(ref, datetime) else mini
            )
            return parsed.isoformat()
        except ValueError:
            return mini
    if isinstance(ref, dict) and isinstance(mini, dict):
        return {k: _norm_mini(x, ref.get(k)) for k, x in mini.items()}
    if isinstance(ref, list) and isinstance(mini, list):
        return [_norm_mini(x, r) for x, r in zip(mini, ref)] + mini[len(ref):]
    return mini


def _diff(a: Any, b: Any, path: str = "") -> str | None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a or k not in b:
                return f"{path}{k}"
            d = _diff(a[k], b[k], f"{path}{k}.")
            if d is not None:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            d = _diff(x, y, f"{path}[{i}].")
            if d is not None:
                return d
        return None
    return None if type(a) is type(b) and a == b else (path.rstrip(".") or "<root>")


def compare(text: str) -> tuple[str | None, Any, Any]:
    """Return (problem, mini, ref); problem is None when both parsers agree."""
    try:
        ref = yaml.safe_load(text)
    except Exception as e:  # noqa: BLE001
        return f"PyYAML error: {type(e).__name__}: {e}", None, None
    ref = ref if isinstance(ref, dict) else {}
    try:
        mini = _mini_yaml(text)
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}", None, ref
    mini, ref = _norm_mini(mini, ref), _norm(ref)
    key = _diff(mini, ref)
    return (None if key is None else f"key {key}"), mini, ref


def self_test() -> int:
    for name, text, expected in CASES:
        try:
            got = _mini_yaml(text)
        except Exception as e:  # noqa: BLE001
            got = f"{type(e).__name__}: {e}"
        if _diff(got, expected) is not None:
            print(f"FAIL self-test [{name}]: mini={got!r} expected={expected!r}")
            return 1
        if yaml is not None and _diff(yaml.safe_load(text), expected) is not None:
            print(f"FAIL self-test [{name}]: PyYAML={yaml.safe_load(text)!r} expected={expected!r}")
            return 1
    for text, needle in UNSUPPORTED:
        try:
            got = _mini_yaml(text)
        except ValueError as e:
            if needle in str(e):
                continue
            print(f"FAIL self-test [unsupported]: {text!r} raised {e!r}, which does not name {needle!r}")
            return 1
        print(f"FAIL self-test [unsupported]: no ValueError for {text!r} (got {got!r})")
        return 1
    print(f"self-test OK ({len(CASES)} cases, {len(UNSUPPORTED)} unsupported"
          f"{', checked against PyYAML' if yaml else ''})")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if yaml is None:
        print("skipped: PyYAML not installed")
        return 0
    if not argv:
        print("usage: check_mini_yaml.py PATH... | --self-test")
        return 2
    n = 0
    for root in argv:
        p = Path(root)
        for f in sorted([p] if p.is_file() else p.rglob("*.md")):
            fm, _ = split_frontmatter(f.read_text(encoding="utf-8"))
            if fm is None:
                continue
            problem, mini, ref = compare(fm)
            n += 1
            if problem is not None:
                detail = f"\n  mini:   {mini!r}\n  PyYAML: {ref!r}" if problem.startswith("key ") else ""
                print(f"MISMATCH {f}: {problem}{detail}")
                return 1
    print(f"OK: {n} frontmatters match PyYAML")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
