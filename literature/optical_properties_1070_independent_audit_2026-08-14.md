# Independent 1070-nm quantity, unit, and wavelength audit

**Audit:** `provisional_1070_independent_quantity_unit_wavelength_v1`

**Mechanical result:** **PASS**

**Scientific/production result:** **BLOCKED**

## What passed

A second implementation reconstructed the provisional central table from the saved source CSV transcriptions rather than from the scenario generator. It separately re-evaluated the Bashkatov fat and skull scattering formulas, checked every `mua`/`musp`/`mus` quantity label and conversion, recomputed `mus = musp/(1-g)`, checked required wavelength labels, and resolved every field-provenance record ID. All 12 central tissue rows and all 14 declared sensitivity variants passed those checks.

| ID | Tissue | Evidence class | Result |
|---:|---|---|:---:|
| 0 | background_air | `model_convention` | PASS |
| 1 | cerebrospinal_fluid | `water_proxy_plus_neighboring_1064_assumption` | PASS |
| 2 | gray_matter | `exact_table_plus_fixed_inverse_inputs` | PASS |
| 3 | white_matter | `exact_table_plus_fixed_inverse_inputs` | PASS |
| 4 | fat | `graph_plus_spectral_model_and_assumptions` | PASS |
| 5 | muscles | `exact_bulk_tissue_surrogate_plus_assumptions` | PASS |
| 6 | skin_and_muscles | `exact_bulk_composite_surrogate_plus_assumptions` | PASS |
| 7 | skull | `graph_plus_spectral_model_and_assumptions` | PASS |
| 9 | fat_2 | `shared_fat_proxy_assumption` | PASS |
| 10 | dura | `exact_table_plus_fixed_inverse_inputs` | PASS |
| 11 | marrow | `exact_tibial_surrogate_plus_assumptions` | PASS |
| 12 | vessels | `graph_digitized_blood_binding_plus_n_assumption` | PASS |

## What did not pass scientifically

- Bashkatov and Friebel central graph points remain single-operator digitizations, not independently redigitized values.
- CSF scattering and anisotropy are unchanged neighboring-1064 simulation assumptions; the absorption and refractive index are water proxies.
- The muscle, composite skin-and-muscle, marrow, vessel, and fat_2 bindings contain unresolved atlas-to-measurement surrogate assumptions.
- Most tissue refractive indices and several anisotropy values are fixed inverse-model or project assumptions rather than 1070-nm measurements.
- The all-TBD production table remains authoritative and no nominal scenario is frozen.

This is therefore a completed independent quantity/unit/wavelength audit of the saved provisional implementation, not a second-person validation of every plotted source value and not approval of `nominal_1070_v1`. The provisional files remain appropriate for bounded sensitivity work only.

## Audit boundary

The audit can detect transcription-to-implementation errors, formula/unit mistakes, quantity swaps, mislabeled neighboring wavelengths, and broken provenance links. It cannot decide that a bulk upper-arm measurement is isolated cranial muscle, that tibial frozen marrow is cranial marrow, or that a fixed refractive index is measured. Those are scientific model choices and remain explicit sensitivity axes.
