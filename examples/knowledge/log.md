# Bundle history

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
