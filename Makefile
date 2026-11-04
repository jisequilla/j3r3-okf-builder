# pipefail makes every `lint ... | tail -1` gate fail when lint fails.
# The flags live in SHELL because GNU make 3.81 (macOS) ignores .SHELLFLAGS.
SHELL := /bin/bash -eo pipefail
.SHELLFLAGS := -c
PLUGIN=plugin/okf-builder
S=$(PLUGIN)/skills/okf-standard/scripts
EX ?= examples/knowledge
.PHONY: plugin lint test dogfood copilot m365 all check-links secrets
plugin:
	cd $(PLUGIN) && zip -qr ../../okf-builder.plugin . -x "*.DS_Store" -x "*__pycache__*"
	@echo "→ okf-builder.plugin"
lint:
	uv run -q $(S)/okf_lint.py knowledge --strict
	uv run -q $(S)/okf_lint.py examples/knowledge
# gitleaks is the thorough secret scanner (okf-lint's SECRET_IN_BUNDLE is a quick check); a leak exits non-zero.
secrets:
	@if command -v gitleaks >/dev/null 2>&1; then \
		for d in knowledge examples/knowledge; do echo "gitleaks dir $$d"; gitleaks dir "$$d" --no-banner --redact || exit 1; done; \
	else echo "secrets: gitleaks is not on PATH, scan skipped (https://github.com/gitleaks/gitleaks)"; fi
test:
	@echo "[1] inline tests of each script (uv run --with pytest <script> --test)"
	uv run -q --with pytest $(S)/okf_init.py --test
	uv run -q --with pytest $(S)/okf_index.py --test
	uv run -q --with pytest $(S)/okf_lint.py --test
	uv run -q --with pytest $(S)/okf_profile.py --test
	uv run -q --with pytest $(S)/okf_migrate.py --test
	@echo "[2] init 0.2 (profile knowledge/3.0) + index + lint --strict"
	rm -rf /tmp/okf-test && uv run -q $(S)/okf_init.py --root /tmp/okf-test --title T --description D --actor human:test >/dev/null
	uv run -q $(S)/okf_index.py /tmp/okf-test/knowledge --check && uv run -q $(S)/okf_lint.py /tmp/okf-test/knowledge --strict | tail -1
	test -f /tmp/okf-test/knowledge/project.md && test -d /tmp/okf-test/knowledge/base/decisions && test -d /tmp/okf-test/knowledge/base/policies && test -d /tmp/okf-test/knowledge/base/questions && grep -q 'knowledge/3.0' /tmp/okf-test/knowledge/index.md && test -d /tmp/okf-test/knowledge/fragments && test -f /tmp/okf-test/knowledge/projections/.gitkeep && test ! -e /tmp/okf-test/knowledge/decisions
	@echo "[3] init 0.1 + lint --strict"
	rm -rf /tmp/okf-test1 && uv run -q $(S)/okf_init.py --root /tmp/okf-test1 --title T --description D --actor human:test --okf-version 0.1 >/dev/null
	uv run -q $(S)/okf_lint.py /tmp/okf-test1/knowledge --strict | tail -1
	@echo "[4] Google fixtures: spec-only lint"
	uv run -q $(S)/okf_lint.py examples/fixtures/google-crypto-bitcoin-v0.1 --no-profile --strict | tail -1
	uv run -q $(S)/okf_lint.py examples/fixtures/google-acme-retail-v0.2 --no-profile --strict | tail -1
	@echo "[5] migration 0.1→0.2 and round-trip 0.2→0.1→0.2"
	rm -rf /tmp/okf-m1 /tmp/okf-m2 /tmp/okf-m3
	uv run -q $(S)/okf_migrate.py examples/fixtures/google-crypto-bitcoin-v0.1 --to 0.2 --out /tmp/okf-m1 >/dev/null && uv run -q $(S)/okf_lint.py /tmp/okf-m1 --no-profile --strict | tail -1
	grep -q '\*\*Migration\*\*' /tmp/okf-m1/log.md
	uv run -q $(S)/okf_migrate.py examples/fixtures/google-acme-retail-v0.2 --to 0.1 --keep-extensions --out /tmp/okf-m2 >/dev/null && uv run -q $(S)/okf_lint.py /tmp/okf-m2 --no-profile | tail -1
	uv run -q $(S)/okf_migrate.py /tmp/okf-m2 --to 0.2 --out /tmp/okf-m3 --force >/dev/null && uv run -q $(S)/okf_lint.py /tmp/okf-m3 --no-profile --strict | tail -1
	@echo "[5b] profile migration knowledge/2.0→3.0 of the fixture examples/fixtures/knowledge-2.0 (2 known warnings: 0 errors)"
	rm -rf /tmp/okf-p3 && uv run -q $(S)/okf_migrate.py examples/fixtures/knowledge-2.0 --profile knowledge/3.0 --out /tmp/okf-p3 >/dev/null
	uv run -q $(S)/okf_lint.py /tmp/okf-p3 | tail -1 | grep ' 0 errors'
	test -d /tmp/okf-p3/base/decisions && test ! -e /tmp/okf-p3/decisions && grep -q 'knowledge/3.0' /tmp/okf-p3/index.md && grep -q '\*\*Migration\*\*' /tmp/okf-p3/log.md
	@echo "[6] M365 export: within the companion limit, each exported skill self-contained, and its okf_migrate.py migrating examples/fixtures/knowledge-2.0"
	python3 tools/export_m365.py >/dev/null
	rm -rf /tmp/okf-m365 && uv run -q dist/m365/package/skills/okf-init/scripts/okf_init.py --root /tmp/okf-m365 --title T --description D --actor human:test >/dev/null
	uv run -q dist/m365/package/skills/okf-init/scripts/okf_lint.py /tmp/okf-m365/knowledge --strict | tail -1
	rm -rf /tmp/okf-m365p3 && uv run -q dist/m365/package/skills/okf-migrate/scripts/okf_migrate.py examples/fixtures/knowledge-2.0 --profile knowledge/3.0 --out /tmp/okf-m365p3 >/dev/null
	uv run -q dist/m365/package/skills/okf-migrate/scripts/okf_lint.py /tmp/okf-m365p3 | tail -1 | grep ' 0 errors'
	for d in dist/m365/package/skills/*/scripts; do test ! -f $$d/okf_lint.py || test -f $$d/okf_profile.py || { echo "$$d: okf_lint.py without okf_profile.py"; exit 1; }; done
	for s in okf-capture okf-fragment okf-distill; do grep -q 'scripts/okf_migrate.py' dist/m365/package/skills/$$s/SKILL.md && test -f dist/m365/package/skills/$$s/scripts/okf_migrate.py || { echo "$$s: names okf_migrate.py but does not ship it"; exit 1; }; done
	rm -rf /tmp/okf-m365q && cp -R /tmp/okf-m365/knowledge /tmp/okf-m365q
	printf -- '---\ntype: Knowledge Fragment\ntitle: M\ndescription: M.\nparticipants: [Alice]\ndistillation_status: done\ngenerated: { by: human:test, at: 2026-11-02T00:00:00Z }\n---\n\n# Record\n\nText.\n' > /tmp/okf-m365q/fragments/2026-11-02-meeting.md
	printf -- '---\ntype: Open Question\ntitle: Q\ndescription: Q.\nowner: human:test\nquestion_status: closed\nasked_in: /fragments/2026-11-02-meeting.md\ngenerated: { by: human:test, at: 2026-11-02T00:00:00Z }\n---\n\n# Question\n\nWho?\n' > /tmp/okf-m365q/base/questions/who.md
	printf -- '---\ntype: Open Question\ntitle: A\ndescription: A.\nowner: human:test\nquestion_status: answered\nasked_in: /fragments/2026-11-02-meeting.md\ngenerated: { by: human:test, at: 2026-11-02T00:00:00Z }\n---\n\n# Question\n\nWhom?\n' > /tmp/okf-m365q/base/questions/whom.md
	uv run -q dist/m365/package/skills/okf-lint/scripts/okf_lint.py /tmp/okf-m365q --json > /tmp/okf-m365q.json || test $$? -eq 1
	python3 -c "import json; c={i['code'] for i in json.load(open('/tmp/okf-m365q.json'))['findings']}; w={'FRAGMENT_NO_FIELD','BAD_ACTOR','BAD_DISTILLATION_STATUS','BAD_QUESTION_STATUS','QUESTION_NO_ANSWER'}; assert w <= c, c; print('exported okf-lint reports', ', '.join(sorted(w)))"
	@echo "[7] canonical copies match the source; the built-in Domain Profile matches §4 and is inlined byte for byte in each exported okf_profile.py; M365 agent within its limits and matching tools/m365-agent.json"
	uv run -q $(S)/okf_profile.py --check-builtin standard/OKF-STANDARD.md
	python3 -c "import ast,glob,sys; src=open('$(PLUGIN)/skills/okf-standard/profiles/knowledge-3.0.md','rb').read(); fs=sorted(glob.glob('dist/m365/*/skills/*/scripts/okf_profile.py')); assert fs, 'no exported okf_profile.py'; bad=[f for f in fs if [n.value.value.encode('utf-8') for n in ast.parse(open(f,encoding='utf-8').read()).body if isinstance(n,ast.AnnAssign) and getattr(n.target,'id','')=='BUILTIN_TEXT' and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)] != [src]]; assert not bad, 'inlined built-in profile differs from the source: ' + ', '.join(bad); print(len(fs), 'exported okf_profile.py inline the built-in profile byte for byte')"
	diff -rq templates $(PLUGIN)/skills/okf-standard/templates
	diff -q standard/OKF-STANDARD.md $(PLUGIN)/skills/okf-standard/references/OKF-STANDARD.md
	diff -q standard/OKF-COMPATIBILITY.md $(PLUGIN)/skills/okf-standard/references/OKF-COMPATIBILITY.md
	test -f dist/m365/okf-knowledge-architect-m365.zip
	python3 -c "import json; d=json.load(open('dist/m365/agent-package/declarativeAgent.json')); c=json.load(open('tools/m365-agent.json')); assert len(d['instructions']) <= 8000 and len(d['agent_skills']) <= 8, d['name']; assert [s['folder'] for s in d['agent_skills']] == ['./skills/' + k for k in c['agent_skills']], 'agent_skills differ from tools/m365-agent.json'; print('agent', len(d['instructions']), 'chars,', len(d['agent_skills']), 'M365 skills')"
	@echo "[8] this repo's bundles are on knowledge/3.0; the 2.0 fixture equals examples/knowledge at 00e510e, before its migration"
	for b in knowledge examples/knowledge; do uv run -q $(S)/okf_lint.py $$b --json | python3 -c "import json,sys; assert not json.load(sys.stdin)['profile_outdated'], '$$b: profile outdated'"; done
	rm -rf /tmp/okf-fx && mkdir -p /tmp/okf-fx && git archive 00e510e examples/knowledge | tar -x -C /tmp/okf-fx
	diff -r /tmp/okf-fx/examples/knowledge examples/fixtures/knowledge-2.0
	$(MAKE) -s dogfood
	@echo "OK"
dogfood:
	@echo "[9] dogfood state of $(EX): only its 4 known warnings; every fragment is a Knowledge Fragment with a distillation_status, aliases resolved; the mapped question Runbook.owner has exactly one gap"
	uv run -q $(S)/okf_lint.py $(EX) --json | python3 -c "import json,sys; c=sorted(f['code'] for f in json.load(sys.stdin)['findings']); assert c == ['BROKEN_LINK', 'FRAGMENT_UNCITED', 'STALE', 'VERIFIED_STALE'], c; print('lint codes', c)"
	uv run -q $(S)/okf_lint.py $(EX) --profiles --json | uv run -q --with pyyaml python -c "import json,sys; from pathlib import Path; sys.path.insert(0,'$(S)'); import okf_profile as p, okf_common as c; q=[x for x in json.load(sys.stdin)['questions'] if x.get('field') == 'Runbook.owner']; assert len(q) == 1, 'no question mapped to Runbook.owner in --profiles'; b=Path('$(EX)'); r=p.load_profile(b); docs=[(d.rel, p.resolve_aliases(r, d.frontmatter)) for d in (c.load_doc(b, f) for f in sorted(b.glob('[bf]*/**/*.md'))) if d.frontmatter]; frags=[(rel, fm) for rel, fm in docs if rel.startswith('fragments/') and not rel.endswith(('index.md', 'log.md'))]; bad=[rel for rel, fm in frags if not p.is_a(r, str(fm.get('type')), 'Knowledge Fragment') or 'distillation_status' not in fm]; assert not bad, 'not read as a Knowledge Fragment with a distillation_status: ' + ', '.join(bad); runbooks=[(rel, fm) for rel, fm in docs if p.is_a(r, str(fm.get('type')), 'Runbook')]; gap=[rel for rel, fm in runbooks if fm.get('owner') in (None, '', [], {})]; assert gap == ['base/runbooks/consumer-lag-alert.md'], gap; print(len(frags), 'fragments read as Knowledge Fragments;', q[0]['question'], '->', len(runbooks), 'runbooks, gap', gap)"
copilot:
	python3 tools/export_copilot.py --zip
	@echo "→ dist/copilot (copy to the root of the target repo) · dist/okf-copilot-pack.zip"
m365:
	python3 tools/export_m365.py
	@echo "→ dist/m365/okf-builder-m365.zip (M365 Cowork plugin) · dist/m365/skills/*.zip (Copilot Studio / Agent Builder)"
all: test plugin copilot m365
check-links:
	@test "$$(readlink .claude/skills)" = "../plugin/okf-builder/skills" && test "$$(readlink .agents/skills)" = "../plugin/okf-builder/skills" && echo "link packages .claude/skills and .agents/skills OK" || (echo "broken symlinks: ln -sfn ../plugin/okf-builder/skills .claude/skills .agents/skills"; exit 1)
