# broken-bundle

Broken on purpose. `knowledge/` is a minimal OKF bundle with exactly one lint
error: `untyped-concept.md` has no `type`.

`okf_lint.py`'s own test `test_broken_bundle_fails_with_no_type` (negative
control) lints it and expects exactly that error and exit 1.

This README sits beside the bundle, not inside it, so lint never reads it.
`just lint` scans only `knowledge/` and `examples/knowledge`, so it never
reads this fixture either.
