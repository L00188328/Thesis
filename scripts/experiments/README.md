# Azure experiment tools

These scripts implement methodology version 1.0.8 without creating Azure resources. The pinned runtime is built with:

```bash
docker compose --profile tools build experiment-tools
docker compose --profile tools run --rm --no-deps experiment-tools unittest discover -s tests -v
```

Primary modules:

- `availability_probe`: fixed-interval GraphQL availability and latency CSV.
- `workload_freshness`: five-second GraphQL progress/freshness rows for both controlled shipments.
- `controlled_workload`: deterministic keyed event publisher and expected/published event ledgers.
- `partition_key_manifest`: deterministic key selection plus broker-observed partition verification.
- `kafka_consumer_progress`: read-only committed/end offset, lag, and assignment evidence.
- `integrity_report`: PostgreSQL history/current-state verification against the expected ledger.
- `timeline`: append-only UTC fault/recovery timeline.
- `summarize_probes`: availability and successful-request latency summary.
- `host_preflight`: controlled external-laptop metadata without credentials or raw public IPs.
- `evidence_export`: redacted export of supported UTF-8 evidence; rejects images/binary files that cannot be proven safe by text sanitisation.
- `estimate_azure_burn` and `create_freeze`: cost and protocol-freeze artifacts.

Kafka arguments default to local plaintext Redpanda. For Event Hubs, set `KAFKA_SECURITY_PROTOCOL=SASL_SSL`, `KAFKA_SASL_MECHANISM=PLAIN`, `KAFKA_SASL_USERNAME='$ConnectionString'`, and pass the namespace connection string only through `KAFKA_SASL_PASSWORD`.

Set `DATABASE_URL` only through the process environment or a mounted secret when running `integrity_report`; database credentials are not accepted as command-line arguments. Tool and collector exception details pass through the common redactor before they are written to evidence. Export only the `evidence_export` destination, never its unredacted source. Binary and screenshot evidence must be independently reviewed and sanitised because the exporter deliberately rejects it.

The Azure fault scripts under `azure/` are inert until explicitly invoked with an authenticated Azure CLI. They record the command timestamp and use only the frozen node-pool stop/start mechanisms.
