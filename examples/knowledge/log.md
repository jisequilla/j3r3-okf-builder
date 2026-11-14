# Bundle history

## 2026-11-14
* **Migration**: 1 decision moved, each to the directory of its type, links rewritten in 6 files, with okf-migrate --move-decisions: `base/decisions/ADR-0001-adopt-kafka.md` → `base/decisions/architecture/ADR-0001-adopt-kafka.md`.

## 2026-11-12
* **Creation**: [DEC-0001: The payments team owns the refund dispute export](/base/decisions/DEC-0001-payments-owns-dispute-export.md), a plain Decision distilled from the fragment [Payments-finance call: who owns the refund dispute export](/fragments/2026-11-12-dispute-export-ownership.md): who answers for the export is not about how a system is built, so it is not an Architecture Decision.
* **Creation**: [Payments-finance call: who owns the refund dispute export](/fragments/2026-11-12-dispute-export-ownership.md), a fictional call captured as a Knowledge Fragment and distilled.

## 2026-11-10
* **Update**: [req-0002](/requests/req-0002/index.md) closed into this bundle by its closing fragment, [Closing of Request req-0002](/fragments/2026-11-10-closing-req-0002.md), approved by human:ana, with `okf_close.py`: its Dispute export promoted, its export columns kept in the instance, its Export cadence carried up.
* **Creation**: [Cadence of the refund dispute export](/base/questions/dispute-export-cadence.md), carried up from req-0002 by its closing fragment, owned by human:lucia, approved by human:ana.
* **Creation**: [Refund dispute export](/base/domain/refund-dispute-export.md), promoted from req-0002 by its closing fragment, approved by human:ana.
* **Creation**: [Closing of Request req-0002](/fragments/2026-11-10-closing-req-0002.md), the closing fragment of [req-0002](/requests/req-0002/index.md), its change set approved by human:ana.

## 2026-11-08
* **Creation**: the instances [req-0001](/requests/req-0001/index.md), a Request about a refund status webhook, and [req-0002](/requests/req-0002/index.md), a Request about a refund dispute export, created with okf-init in `requests/`.
* **Update**: [Domain Profile of Demo Payments](/base/profile.md) declares the kind Request, an operational bundle in `requests/` with the extra state `in-review`.

## 2026-11-06
* **Creation**: the projection `projections/onboarding-brief/`, canonical and composed: a short on-call brief for a new engineer of Demo Payments, composed from [ADR-0001](/base/decisions/architecture/ADR-0001-adopt-kafka.md), the [Payments consumer lag alert](/base/runbooks/consumer-lag-alert.md) and the [Payments dead-letter replay](/base/runbooks/payments-dead-letter-replay.md) with the okf-projection skill; its ref hashes written by `okf_projection.py --record-hashes onboarding-brief`. It is not a concept: okf-lint skips it and `okf_projection.py` checks it.

## 2026-11-04
* **Update**: [ADR-0001](/base/decisions/architecture/ADR-0001-adopt-kafka.md) cites the [payments sync on refund events](/fragments/2026-11-02-refund-events-review.md), which confirms Kafka as the event bus; the fragment's ledger gains that row, so every part of its record has one, and its action item's Concept is `tracker`, like the one of the [finance chat asking for the dispute window](/fragments/2026-10-28-finance-dispute-window-ask.md), whose complete ledger now covers it (no FRAGMENT_UNCITED).
* **Creation**: [Platform chat: the retention of the refunds topic](/fragments/2026-11-03-refund-topic-retention-chat.md), a fictional chat captured as a Fragmento (ingerido: false) from a text export kept beside it, `fragments/2026-11-03-refund-topic-retention-chat.txt`, named with its SHA-256 in `material` so lint checks that the source was not altered after capture.
* **Update**: [Demo Payments](/project.md) is written the way okf_init now writes a project.md: Purpose holds the description, and the sections and rows nobody filled (Scope, Team and ownership, the empty Key links rows) are removed instead of kept as placeholders (SECTION_EMPTY).

## 2026-11-02
* **Creation**: [Finance chat: asking for the refund dispute window](/fragments/2026-10-28-finance-dispute-window-ask.md), a fictional chat captured and distilled with the bundle's local names (type Fragmento, ingerido: true); its action item went to the tracker. Finance's fragments are now the bundle's most used name for a fragment, so the next one is written as a Fragmento.
* **Update**: [Domain Profile of Demo Payments](/base/profile.md) gains the type alias Fragmento (Knowledge Fragment), the value aliases ingerido: true (distillation_status: distilled) and ingerido: false (pending), and the question "Who answers for each runbook?" mapped to Runbook.owner.
* **Creation**: [Finance chat: the refund dispute window](/fragments/2026-11-02-finance-dispute-window.md), a fictional chat captured with the bundle's local names (type Fragmento, ingerido: false), not distilled yet.
* **Creation**: [Payments dead-letter replay](/base/runbooks/payments-dead-letter-replay.md), a fictional runbook owned by team:payments.
* **Creation**: [Domain Profile of Demo Payments](/base/profile.md), the bundle's own Domain Profile: the local type Payments Meeting (extends Knowledge Fragment), the family /base/questions/, the rule distilled-payments-meeting-names-team and the aliases Reunión de pagos and equipo.
* **Creation**: [Payments follow-up: the refunds topic](/fragments/2026-11-02-refund-topic-follow-up.md), a fictional follow-up captured as a Payments Meeting, not distilled yet.
* **Creation**: [Payments sync: refund events on the Kafka bus](/fragments/2026-11-02-refund-events-review.md), a fictional meeting captured as a Knowledge Fragment and distilled; its action item went to the tracker.
* **Creation**: [Retention of refund events](/base/questions/refund-event-retention.md), an Open Question asked in that fragment, owned by human:maria.
* **Migration**: Bundle migrated to profile knowledge/3.0 (12 directories and 0 root concepts moved under base/; links rewritten in 4 files) with okf-migrate.

## 2026-11-01
* **Migration**: profile knowledge/1.0 → knowledge/2.0, the English vocabulary of okf-builder's ADR-0010; `index.md` declares `okf_profile: "knowledge/2.0"`.

## 2026-10-30
* **Initialization**: `knowledge/` structure created with the knowledge/1.0 profile (OKF v0.2).
