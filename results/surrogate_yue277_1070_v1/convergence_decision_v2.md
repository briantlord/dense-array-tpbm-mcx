# Yue-derived 1070-nm surrogate convergence decision

**Decision date:** 2026-08-14

**Geometry:** `surrogate_yue277_1070_v1` (`e36fb1e6111c02c343020350719e4b39de34830d9b42b0b352e87a09b8aad9b6`)

**Initial result:** `regional_convergence_v1/results.json` (`e88dc1634d46646e5c2c2b99237baa82ab16a0dcabeacd22a22b88f991e7c033`)

**Controlling result:** `regional_convergence_v2/results.json` (`637d3daaa4fbbf8fe6009dea23dec1b4bd57b424699eb48ad52973d3dfb55db4`)

## Decision

The initial five-region, three-seed sequence through `10^7` photons failed the frozen compound criterion in the posterior, right-temporal, and superior profiles. That negative result is retained unchanged. The versioned extension added only a `10^8` tier and reused the checksum-recorded lower tiers.

Every region passes the `10^7`-to-`10^8` transition. Across the five regions, maximum tissue-integral CV is 0.115% to 0.299%, maximum tissue-integral step change is 0.049% to 0.837%, median valid-depth profile CV is 1.57% to 5.38%, and median profile step change is 1.15% to 7.69%. These are below the prespecified 5% integral and 10% profile limits.

Freeze `10^8` photons per emitter for the first complete `surrogate_yue277_1070_basis_v1` basis. The prepared plan contains 277 unique emitters and 277 deterministic unique seeds. Its index checksum is `40329f46b248f6d1e2a74016db51f6dad32d2245dee58fc08f59c0cd1d358ac3`.

The measured median at the selected tier projects to approximately 242 minutes for 277 sequential runs on this M4 Pro. This is a planning estimate, not a completion record. No full-basis MCX field has been executed by this decision.

## Interpretation boundary

This decision validates Monte Carlo sampling for the provisional Yue-derived spatial surrogate and current provisional central optical scenario. It does not validate target-helmet geometry, radiometry, beam shape, registration, production optical properties, biological dose, or efficacy. Any change to anatomy, optical scenario, source profile, or geometry requires a new transport basis and an appropriate convergence check.
