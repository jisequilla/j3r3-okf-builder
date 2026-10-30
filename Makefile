PLUGIN=plugin/okf-builder
S=$(PLUGIN)/skills/okf-standard/scripts
.PHONY: plugin lint test copilot m365 all check-links
plugin:
	cd $(PLUGIN) && zip -qr ../../okf-builder.plugin . -x "*.DS_Store" -x "*__pycache__*"
	@echo "→ okf-builder.plugin"
lint:
	python3 $(S)/okf_lint.py knowledge --strict
	python3 $(S)/okf_lint.py examples/knowledge
test:
	@echo "[1] init 0.2 + index + lint --strict"
	rm -rf /tmp/okf-test && python3 $(S)/okf_init.py --root /tmp/okf-test --title T --description D --actor human:test >/dev/null
	python3 $(S)/okf_index.py /tmp/okf-test/knowledge --check && python3 $(S)/okf_lint.py /tmp/okf-test/knowledge --strict | tail -1
	test -f /tmp/okf-test/knowledge/project.md && test -d /tmp/okf-test/knowledge/decisions && test -d /tmp/okf-test/knowledge/policies && grep -q 'knowledge/2.0' /tmp/okf-test/knowledge/index.md
	@echo "[2] init 0.1 + lint --strict"
	rm -rf /tmp/okf-test1 && python3 $(S)/okf_init.py --root /tmp/okf-test1 --title T --description D --actor human:test --okf-version 0.1 >/dev/null
	python3 $(S)/okf_lint.py /tmp/okf-test1/knowledge --strict | tail -1
	@echo "[3] fixtures Google: lint solo spec"
	python3 $(S)/okf_lint.py examples/fixtures/google-crypto-bitcoin-v0.1 --no-profile --strict | tail -1
	python3 $(S)/okf_lint.py examples/fixtures/google-acme-retail-v0.2 --no-profile --strict | tail -1
	@echo "[4] migración 0.1→0.2 y round-trip 0.2→0.1→0.2"
	rm -rf /tmp/okf-m1 /tmp/okf-m2 /tmp/okf-m3
	python3 $(S)/okf_migrate.py examples/fixtures/google-crypto-bitcoin-v0.1 --to 0.2 --out /tmp/okf-m1 >/dev/null && python3 $(S)/okf_lint.py /tmp/okf-m1 --no-profile --strict | tail -1
	python3 $(S)/okf_migrate.py examples/fixtures/google-acme-retail-v0.2 --to 0.1 --keep-extensions --out /tmp/okf-m2 >/dev/null && python3 $(S)/okf_lint.py /tmp/okf-m2 --no-profile | tail -1
	python3 $(S)/okf_migrate.py /tmp/okf-m2 --to 0.2 --out /tmp/okf-m3 --force >/dev/null && python3 $(S)/okf_lint.py /tmp/okf-m3 --no-profile --strict | tail -1
	@echo "[5] [1]-[4] sin PyYAML (OKF_NO_PYYAML=1)"
	rm -rf /tmp/okf-ny-test && OKF_NO_PYYAML=1 python3 $(S)/okf_init.py --root /tmp/okf-ny-test --title T --description D --actor human:test >/dev/null
	OKF_NO_PYYAML=1 python3 $(S)/okf_index.py /tmp/okf-ny-test/knowledge --check && OKF_NO_PYYAML=1 python3 $(S)/okf_lint.py /tmp/okf-ny-test/knowledge --strict | tail -1
	test -f /tmp/okf-ny-test/knowledge/project.md && test -d /tmp/okf-ny-test/knowledge/decisions && test -d /tmp/okf-ny-test/knowledge/policies && grep -q 'knowledge/2.0' /tmp/okf-ny-test/knowledge/index.md
	rm -rf /tmp/okf-ny-test1 && OKF_NO_PYYAML=1 python3 $(S)/okf_init.py --root /tmp/okf-ny-test1 --title T --description D --actor human:test --okf-version 0.1 >/dev/null
	OKF_NO_PYYAML=1 python3 $(S)/okf_lint.py /tmp/okf-ny-test1/knowledge --strict | tail -1
	OKF_NO_PYYAML=1 python3 $(S)/okf_lint.py examples/fixtures/google-crypto-bitcoin-v0.1 --no-profile --strict | tail -1
	OKF_NO_PYYAML=1 python3 $(S)/okf_lint.py examples/fixtures/google-acme-retail-v0.2 --no-profile --strict | tail -1
	rm -rf /tmp/okf-ny-m1 /tmp/okf-ny-m2 /tmp/okf-ny-m3
	OKF_NO_PYYAML=1 python3 $(S)/okf_migrate.py examples/fixtures/google-crypto-bitcoin-v0.1 --to 0.2 --out /tmp/okf-ny-m1 >/dev/null && OKF_NO_PYYAML=1 python3 $(S)/okf_lint.py /tmp/okf-ny-m1 --no-profile --strict | tail -1
	OKF_NO_PYYAML=1 python3 $(S)/okf_migrate.py examples/fixtures/google-acme-retail-v0.2 --to 0.1 --keep-extensions --out /tmp/okf-ny-m2 >/dev/null && OKF_NO_PYYAML=1 python3 $(S)/okf_lint.py /tmp/okf-ny-m2 --no-profile | tail -1
	OKF_NO_PYYAML=1 python3 $(S)/okf_migrate.py /tmp/okf-ny-m2 --to 0.2 --out /tmp/okf-ny-m3 --force >/dev/null && OKF_NO_PYYAML=1 python3 $(S)/okf_lint.py /tmp/okf-ny-m3 --no-profile --strict | tail -1
	@echo "[6] parser reducido frente a PyYAML"
	python3 tools/check_mini_yaml.py --self-test
	python3 tools/check_mini_yaml.py knowledge examples
	@echo "OK"
copilot:
	python3 tools/export_copilot.py --zip
	@echo "→ dist/copilot (copiar a la raíz del repo destino) · dist/okf-copilot-pack.zip"
m365:
	python3 tools/export_m365.py
	@echo "→ dist/m365/okf-builder-m365.zip (plugin Cowork M365) · dist/m365/skills/*.zip (Copilot Studio / Agent Builder)"
all: test plugin copilot m365
check-links:
	@test "$$(readlink .claude/skills)" = "../plugin/okf-builder/skills" && test "$$(readlink .agents/skills)" = "../plugin/okf-builder/skills" && echo "proyecciones .claude/skills y .agents/skills OK" || (echo "symlinks rotos: ln -sfn ../plugin/okf-builder/skills .claude/skills .agents/skills"; exit 1)
