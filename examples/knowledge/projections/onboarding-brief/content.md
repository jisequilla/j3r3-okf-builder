# On-call brief: Demo Payments

## The bus

Payment events travel on Kafka ([ADR-0001](/base/decisions/ADR-0001-adopt-kafka.md)). The payments service needs 7-day retention of its events.

## When an alert fires

| Signal | Runbook | What you do |
|---|---|---|
| Alert `KafkaConsumerLagHigh`: the payments consumer group is over 10k messages of lag | [Payments consumer lag alert](/base/runbooks/consumer-lag-alert.md) | Follow the runbook |
| Messages on `payments.dlq` after a consumer failure | [Payments dead-letter replay](/base/runbooks/payments-dead-letter-replay.md) | Read the error header of the first parked message; confirm the failed consumer is fixed and deployed; replay `payments.dlq` into `payments` from its oldest offset; watch the lag until it is back under 10k messages |

## Escalation

If the dead-letter replay fails twice, escalate to Payments on-call.
