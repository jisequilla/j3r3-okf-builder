# broken-bundle

Broken on purpose. `knowledge/` is a minimal OKF bundle with exactly one lint
error: `untyped-concept.md` has no `type`.

Step [7] of `make test` (negative control) lints it through the same
`| tail -1` pipe as the real gates and expects exit 1. If that step passes
when lint succeeds, the pipes are hiding failures again.

This README sits beside the bundle, not inside it, so lint never reads it.
`make lint` scans only `knowledge/` and `examples/knowledge`, so it never
reads this fixture either.
