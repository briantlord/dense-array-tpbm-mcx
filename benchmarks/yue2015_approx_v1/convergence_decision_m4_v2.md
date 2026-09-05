# Corrected Yue representative convergence decision

**Decision date:** 2026-08-14

**Protocol:** `configs/yue2015_convergence_acceptance_v1.json` (`0ff4ed4ea218d0bc4eba50b4c48ea313abff2fda5aec3effc5d29205f8156ac9`)

**Controlling result:** `convergence_paperscale_m4_v2/results.json` (`c44e014c2c8eb5cb134f0eb228cc2aebc0fe5adf1d25afe5987f44397dfd5445`)

**Decoder evidence:** JData `_ArrayOrder_: "c"` is decoded as column-major/NumPy `F` order; rectangular and row-major fixtures are regression-tested.

## Decision

The corrected north-pole representative sequence passes every frozen tissue-integral and valid-depth profile threshold at both final transitions:

| Transition | Maximum tissue-integral CV | Maximum tissue-integral step change | Median profile CV | Median profile step change | Compound result |
|---|---:|---:|---:|---:|---|
| `10^7` to `10^8` | 0.00098 | 0.00051 | 0.01284 | 0.02229 | pass |
| `10^8` to `10^9` | 0.00023 | 0.00085 | 0.00667 | 0.00703 | pass |

`10^8` photons per source is therefore the **minimum passing representative candidate** under the frozen protocol. The `10^9` tier provides a paper-count cross-check and also passes. This is not yet a final multisource photon-count selection: digitized Yue comparisons, source-density behavior, and an aggregate-versus-basis check remain open.

## Consequences

- Withdraw the v1 convergence pass/fail findings documented in `convergence_axis_order_invalidation_2026-08-14.md`.
- Use `10^8` photons per source for the first multisource benchmark comparison, not `10^9`, unless a later versioned multisource convergence result requires escalation.
- Do not treat representative convergence as reproduction of Yue Figures 2, 4, 5, or 6.
- Complete the frozen two-pass digitization and benchmark discrepancy analysis before closing the benchmark gate.
