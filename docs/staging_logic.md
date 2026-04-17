# Staging Logic

## Overview

The staging engine now assigns Stage 1, Stage 2 and Stage 3 using only
information observable at the measurement date.

The field `default_12m` remains in the project because it is still needed as the
future outcome label for PD model training, calibration and validation. It is no
longer used as an operational staging trigger.

This change removes look-ahead bias from the staging layer and makes the engine
closer to the prudential and accounting logic expected under CMN 4.966 and IFRS 9.

## Observable staging triggers

### Stage 1

Stage 1 is assigned when there is no evidence of significant increase in credit
risk and no observed sign that the exposure is already credit-impaired.

### Stage 2

Stage 2 represents significant increase in credit risk. The engine now promotes
an exposure to Stage 2 when at least one observable trigger is present:

- `dpd >= 30`
- `watchlist_flag == 1`, when the field exists
- material PD deterioration versus origination, requiring both:
  - relative increase above `stage2_pd_relative_multiplier`
  - absolute increase above `stage2_pd_absolute_increase`

Using both relative and absolute PD thresholds avoids overstating SICR for
accounts that started with very low origination PD.

### Stage 3

Stage 3 represents observed default or credit-impaired status at the reporting date.
The engine now assigns Stage 3 when at least one of the following triggers is present:

- `dpd >= 90`
- `problem_asset_flag == 1`, when the field exists
- `restructured_flag == 1`, when the field exists
- `financial_distress_flag == 1`, when the field exists

Stage 3 always overrides Stage 2, and Stage 2 always overrides Stage 1.

## Configurable thresholds

The staging thresholds are now explicit in `config.py`:

- `STAGE2_DPD_THRESHOLD`
- `STAGE3_DPD_THRESHOLD`
- `STAGE2_PD_RELATIVE_MULTIPLIER`
- `STAGE2_PD_ABSOLUTE_INCREASE`

This keeps the rule transparent and easy to calibrate without changing code.

## Synthetic support fields

To let the synthetic engine exercise observable staging logic without future leakage,
the synthetic portfolio generator now creates optional support fields:

- `watchlist_flag`
- `restructured_flag`
- `financial_distress_flag`
- `problem_asset_flag`

These fields are derived from contemporaneous account and borrower conditions,
such as delinquency, leverage proxies, utilization and score weakness.
They do not use realized future default.

## Why this is closer to regulatory logic

The updated approach is more defensible because it separates two distinct concepts:

- future default realization, which belongs to model development and validation
- observed deterioration at the measurement date, which belongs to stage allocation

This better matches the spirit of CMN 4.966:

- Stage 2 should capture significant increase in credit risk using reasonable,
  supportable and documentable evidence
- Stage 3 should reflect observed credit impairment or problem asset status

The implementation remains intentionally simple for this project, but the rule
is now materially closer to a prudential staging framework than the previous
version that relied on `default_12m`.
