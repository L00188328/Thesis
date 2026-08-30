# G1/G2 Amended Run Plan

Protocol v1.0.8 retains one discarded warm-up and two measured runs for each regional configuration:

- `G1-warmup`, `G1-r01`, `G1-r02`;
- `G2-warmup`, `G2-r01`, `G2-r02`.

`G1-r03` and `G2-r03` remain in the unchanged historical broker key manifest with status **planned but not executed after protocol amendment**. Their keys must not be reused. The G1/G2 Region A failure mechanism, G1 activation action, Front Door settings, 600-second window, probe/progress cadences, 600-event workload and integrity criteria remain unchanged.

Planned primary evidence directories are `raw/G1-active-passive/{warm-up,run-01,run-02}/` and `raw/G2-active-active/{warm-up,run-01,run-02}/`.
