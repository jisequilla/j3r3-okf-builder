# Changelog

## [0.11.0](https://github.com/jisequilla/j3r3-okf-builder/compare/v0.10.0...v0.11.0) (2026-11-25)


### ⚠ BREAKING CHANGES

* okf-056 follow-ups: a local type extending Open Question is one, --dir names a path with nothing to index, and §4's prefixes are checked (okf-056.8, .12, .13, .16) ([#129](https://github.com/jisequilla/j3r3-okf-builder/issues/129))
* a value alias's from and to read local names, it keeps the type unless to gives one, and a from that can never hold is invalid (okf-056.15) ([#128](https://github.com/jisequilla/j3r3-okf-builder/issues/128))
* every script reads a link as CommonMark defines it, images included, and LINK_RE is gone (okf-056.9) ([#127](https://github.com/jisequilla/j3r3-okf-builder/issues/127))
* okf-index groups concepts by the type each stands for, and every check reads a local name of the type key (okf-056.11, okf-056.14) ([#126](https://github.com/jisequilla/j3r3-okf-builder/issues/126))
* a concept written with a local name of the type key and a local type name is read as the type it stands for (okf-056.10) ([#125](https://github.com/jisequilla/j3r3-okf-builder/issues/125))
* the standard gains the type Decision that Architecture Decision extends, a prefix per decision type and the fields decision_id and formerly (okf-056.1) ([#115](https://github.com/jisequilla/j3r3-okf-builder/issues/115))

### Features

* carried questions and conflicts, the closing fragment in the parent, and a pending fragment as a loose end of a closed instance (ADR-0039) ([#95](https://github.com/jisequilla/j3r3-okf-builder/issues/95)) ([3ecd434](https://github.com/jisequilla/j3r3-okf-builder/commit/3ecd434e0d5c43ca37e85665dce0ab97c70544c7))
* domain and operational bundles in the standard and in lint (ADR-0038) ([#89](https://github.com/jisequilla/j3r3-okf-builder/issues/89)) ([d6957d1](https://github.com/jisequilla/j3r3-okf-builder/commit/d6957d170122ddaf4a7b37087c10d8228d446f85))
* lint accepts the file-name prefix each decision type declares, and reports a decision named with another type's prefix (okf-056.2) ([#116](https://github.com/jisequilla/j3r3-okf-builder/issues/116)) ([a90dbc5](https://github.com/jisequilla/j3r3-okf-builder/commit/a90dbc5d39db577ef566db67afe73ab528a5222c))
* okf_close.py and okf-distill's closing mode close an operational instance into its parent, outside the Microsoft 365 package ([#102](https://github.com/jisequilla/j3r3-okf-builder/issues/102)) ([66eed95](https://github.com/jisequilla/j3r3-okf-builder/commit/66eed959b962cbc3a1c068f14eaf41d123aef956))
* okf_viewer.py --answers checks the page's stored answers against the bundle, okf-review runs a verification round with it, and the Microsoft 365 package and the Copilot pack carry a note in its place (okf-1lj.3) ([#134](https://github.com/jisequilla/j3r3-okf-builder/issues/134)) ([292597f](https://github.com/jisequilla/j3r3-okf-builder/commit/292597fde1600e67958864d9c084789e35cfc5ea))
* okf_viewer.py builds the Knowledge Viewer's page and data from any knowledge/ directory, with its template in the plugin and out of the Microsoft 365 and Copilot packages (okf-1lj.2) ([#133](https://github.com/jisequilla/j3r3-okf-builder/issues/133)) ([6cd3416](https://github.com/jisequilla/j3r3-okf-builder/commit/6cd341652c539d53861fb68492486c4be441d012))
* okf-index lists each kind's instances with their state in the kind directory's index (okf-3vg.3) ([#101](https://github.com/jisequilla/j3r3-okf-builder/issues/101)) ([e759f5d](https://github.com/jisequilla/j3r3-okf-builder/commit/e759f5d85007ca0401863732c1e02acad0697c7b))
* okf-index, the Obsidian setup and okf-init treat every type that is a Decision as a decision, in base/decisions/ and its subfolders (okf-056.3) ([#117](https://github.com/jisequilla/j3r3-okf-builder/issues/117)) ([6c7dd92](https://github.com/jisequilla/j3r3-okf-builder/commit/6c7dd92b53c844d3dbfe7407d70b473f64902d4a))
* okf-init creates an operational instance of a kind (ADR-0039) ([#99](https://github.com/jisequilla/j3r3-okf-builder/issues/99)) ([0bcbc53](https://github.com/jisequilla/j3r3-okf-builder/commit/0bcbc533319f8b0630c4bd00fa81a1183a3e9e2a))
* the audit reports a concept edited after its instance closed, and the example bundle gains the kind Request with an open and a closed instance ([#107](https://github.com/jisequilla/j3r3-okf-builder/issues/107)) ([d7c6dc6](https://github.com/jisequilla/j3r3-okf-builder/commit/d7c6dc6133a00fea8a4ca476fe510f7f2737c10a))
* the skills capture, distill and review any kind of decision with a template for a plain Decision, and the example bundle moves to the new decisions layout (okf-056.5) ([#120](https://github.com/jisequilla/j3r3-okf-builder/issues/120)) ([865490b](https://github.com/jisequilla/j3r3-okf-builder/commit/865490ba9241eafef551d4fbd04142ed68b687ef))
* the standard gains the type Decision that Architecture Decision extends, a prefix per decision type and the fields decision_id and formerly (okf-056.1) ([#115](https://github.com/jisequilla/j3r3-okf-builder/issues/115)) ([54ff9d0](https://github.com/jisequilla/j3r3-okf-builder/commit/54ff9d0669dcdac973b73135efc3f7ab75cc87d5))


### Bug Fixes

* a concept written with a local name of the type key and a local type name is read as the type it stands for (okf-056.10) ([#125](https://github.com/jisequilla/j3r3-okf-builder/issues/125)) ([ec78629](https://github.com/jisequilla/j3r3-okf-builder/commit/ec786295c1c98f135395c02a2cef9fd6c0f3271b))
* a value alias's from and to read local names, it keeps the type unless to gives one, and a from that can never hold is invalid (okf-056.15) ([#128](https://github.com/jisequilla/j3r3-okf-builder/issues/128)) ([e15fe09](https://github.com/jisequilla/j3r3-okf-builder/commit/e15fe09a5e8a5cee0f92264c328bd815da8aba4c))
* every script reads a link as CommonMark defines it, images included, and LINK_RE is gone (okf-056.9) ([#127](https://github.com/jisequilla/j3r3-okf-builder/issues/127)) ([fbd780c](https://github.com/jisequilla/j3r3-okf-builder/commit/fbd780cb519d09595ae38c94b0ba9c0c834998bc))
* lint reads an aliased open question of a closed instance as a loose end, and the standard says what okf-migrate does with .okfignore'd paths and who writes a closing (okf-3vg.17) ([#109](https://github.com/jisequilla/j3r3-okf-builder/issues/109)) ([2b23f56](https://github.com/jisequilla/j3r3-okf-builder/commit/2b23f568466b10ea85cd45392cabe2030395a386))
* okf-056 follow-ups: a local type extending Open Question is one, --dir names a path with nothing to index, and §4's prefixes are checked (okf-056.8, .12, .13, .16) ([#129](https://github.com/jisequilla/j3r3-okf-builder/issues/129)) ([a779541](https://github.com/jisequilla/j3r3-okf-builder/commit/a779541147d1da4dc38bdc9f52df6b1c1f959f94))
* okf-index groups concepts by the type each stands for, and every check reads a local name of the type key (okf-056.11, okf-056.14) ([#126](https://github.com/jisequilla/j3r3-okf-builder/issues/126)) ([554975f](https://github.com/jisequilla/j3r3-okf-builder/commit/554975f5c538fc0494511669fb90827fadfaca47))
* okf-index leaves .okfignore'd paths, nested bundles and non-OKF directories alone, as lint does (okf-4j8) ([#96](https://github.com/jisequilla/j3r3-okf-builder/issues/96)) ([b01deb2](https://github.com/jisequilla/j3r3-okf-builder/commit/b01deb2ca2e4dbdd1b27e146296127e46b256671))
* okf-migrate adds one .okfignore entry per moved directory a glob-first entry matches, and okf_close names the state key to remove from a closed domain parent (okf-3vg.18, okf-3vg.20) ([#130](https://github.com/jisequilla/j3r3-okf-builder/issues/130)) ([274dfec](https://github.com/jisequilla/j3r3-okf-builder/commit/274dfec6a35e275a029b47eb9d9205cdf01d3de3))
* the plugin's text, the build and the repo's context files cite the renumbered decisions by their new identifiers (okf-056.7) ([#123](https://github.com/jisequilla/j3r3-okf-builder/issues/123)) ([2f71f1c](https://github.com/jisequilla/j3r3-okf-builder/commit/2f71f1ccf1bbc10f73ec0822b50756e00a274a33))
