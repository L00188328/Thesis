# F1 Amended Run Plan and Execution Status

Protocol v1.0.8 retains one discarded warm-up and two measured runs:

- `F1-warmup` — discarded rehearsal;
- `F1-r01` — measured;
- `F1-r02` — measured.

`F1-r03` remains in the unchanged historical broker key manifest with status **planned but not executed after protocol amendment**. Its keys must not be reused. The failure mechanism, 600-second window, one-second availability probe, five-second progress collection, 600-event workload and integrity criteria remain unchanged.

Planned primary evidence directories are `raw/F1-simulated-zonal-failure/warm-up/`, `run-01/` and `run-02/`.

Execution completed on 2026-08-30 under protocol v1.0.8. The discarded warm-up, `F1-r01`, and `F1-r02` all completed their fixed windows, integrity gates, recovery gates, and sanitised evidence export. `F1-r03` was not executed. See `results.md` and `exported/`.
