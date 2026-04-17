# Probability-Weighted ECL

## What changed

The impairment engine no longer treats macro scenarios only as a sensitivity layer.
It now supports a final probability-weighted ECL that combines the existing
`base`, `adverse` and `severe` scenarios into one impairment measure.

## Sensitivity analysis versus weighted provision

The previous design was useful for stress analysis:

- calculate one base ECL
- shock PD and LGD under adverse and severe scenarios
- compare totals side by side

That is still helpful for management analysis, but it is not the same as a final
forward-looking accounting provision.

The updated design now does both:

- keeps the per-scenario ECL decomposition for analysis and audit
- produces one `final_ecl_weighted` by applying explicit scenario probabilities

## Scenario configuration

The default scenario set remains:

- `base`
- `adverse`
- `severe`

Each scenario now carries:

- macro shifts
- PD multiplier
- LGD multiplier
- probability weight

Default weights are currently:

- base: `0.60`
- adverse: `0.30`
- severe: `0.10`

If custom weights do not sum to 1, the engine normalizes them and records that
normalization in the scenario audit output.

## Outputs

The engine now produces:

- `ecl_base`
- `ecl_adverse`
- `ecl_severe`
- `final_ecl_weighted`

For audit and traceability, it also keeps:

- `ecl_12m_<scenario>`
- `ecl_lifetime_<scenario>`
- scenario weights used
- PD and LGD multipliers used
- macro snapshot reference date, when available

The legacy `final_ecl` field is preserved as an alias of `final_ecl_weighted`
so downstream portfolio outputs keep working.

## Why this is conceptually closer to CMN 4.966 and IFRS 9

Probability-weighted ECL is a better forward-looking approximation because it
does not assume that only one macro path matters. Instead, it combines multiple
reasonable and supportable scenarios into the final impairment amount.

In practical terms, this improves the design in two ways:

- it separates scenario analysis from final provisioning logic
- it makes the impairment output more consistent with a forward-looking expected-loss view

The implementation remains intentionally simple for this project:

- scenarios are still discrete
- overlays remain transparent
- there is no full econometric scenario generation layer

That keeps the engine modular and explainable while moving it materially closer
to a defensible multi-scenario impairment framework.
