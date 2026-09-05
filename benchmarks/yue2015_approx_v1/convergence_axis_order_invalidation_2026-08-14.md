# Invalidation of Yue convergence v1 analyses

The compact v1 convergence analyses under `convergence_pilot_m4_v1/`, `convergence_representative_m4_v1/`, and `convergence_paperscale_m4_v1/` are retained as provenance but are not valid benchmark evidence.

The MCX JNIfTI adapter interpreted JData `_ArrayOrder_: "c"` as NumPy row-major (`C`) order. JData uses `c` for column-major ordering, which must be decoded with NumPy `F` order. Because the Colin27 benchmark grid is `181 x 217 x 181`, exchanging x and z preserved the observed shape and escaped the original cubic-fixture test. It displaced the north-pole field away from the declared source axis and misregistered the field with every tissue mask.

Consequences:

- v1 axis profiles are invalid;
- v1 tissue integrals and their convergence statistics are invalid;
- the reported 14.23% `10^8`-to-`10^9` profile step change is withdrawn;
- no pass/fail or photon-count decision may use the v1 summaries.

The underlying MCX transport executions were not shown to be faulty. The error occurred while decoding and spatially interpreting their JNIfTI fields. Large temporary fields were not retained, so the frozen convergence sequence must be rerun with the corrected adapter. Replacement results must use a new result ID and output directory and must not overwrite these records.
