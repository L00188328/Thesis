# F1 Amended Run Plan

Protocol v1.0.8 retains one discarded warm-up and two measured runs:

- `F1-warmup` — discarded rehearsal;
- `F1-r01` — measured;
- `F1-r02` — measured.

`F1-r03` remains in the unchanged historical broker key manifest with status **planned but not executed after protocol amendment**. Its keys must not be reused. The failure mechanism, 600-second window, one-second availability probe, five-second progress collection, 600-event workload and integrity criteria remain unchanged.

Planned primary evidence directories are `raw/F1-simulated-zonal-failure/warm-up/`, `run-01/` and `run-02/`.
