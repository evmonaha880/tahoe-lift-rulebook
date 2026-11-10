# Models 1 and 2 beside the single wind line

View: all 11 winters (2015-16 to 2025-26; 2015-16 wind is an estimate, 2016-18 wind is hourly from one station). 13,878 expected lift-days. Leave-one-winter-out: each model is fitted on the other winters and scored on the one left out; counts are summed.
Every method reads only what is known by about 9-10 am: early_gust, early_spd, avy, temp_base, swe24, swe6, prec24s, new_snow24, month, side, lift. Calls are made at 50% probability (models) or at the fitted line.

| Method (pooled) | Precision | Recall | F1 |
|---|---|---|---|
| Model 1: boosted trees (ceiling) | 0.646 | 0.693 | 0.669 |
| Model 2: tree, depth 3 | 0.648 | 0.67 | 0.659 |
| Single early-gust line (fitted) | 0.623 | 0.73 | 0.672 |
| 25 mph rule on early gust | 0.388 | 0.958 | 0.552 |

## Per winter (F1)

| Winter | Model 1: boosted trees (ceiling) | Model 2: tree, depth 3 | Single early-gust line (fitted) | 25 mph rule on early gust |
|---|---|---|---|---|
| 2015-16 | 0.769 | 0.658 | 0.702 | 0.864 |
| 2016-17 | 0.813 | 0.765 | 0.774 | 0.82 |
| 2017-18 | 0.586 | 0.633 | 0.741 | 0.809 |
| 2018-19 | 0.766 | 0.81 | 0.837 | 0.913 |
| 2019-20 | 0.66 | 0.706 | 0.823 | 0.815 |
| 2020-21 | 0.0 | 0.0 | 0.0 | 0.0 |
| 2021-22 | 0.559 | 0.575 | 0.573 | 0.332 |
| 2022-23 | 0.661 | 0.637 | 0.638 | 0.513 |
| 2023-24 | 0.596 | 0.589 | 0.569 | 0.377 |
| 2024-25 | 0.607 | 0.578 | 0.709 | 0.705 |
| 2025-26 | 0.573 | 0.667 | 0.644 | 0.716 |

## Model 2 as if-then rules (fitted on all winters, for reading only; the scores above come from the left-out folds)

```
|--- early_spd <= 56.85
|   |--- new_snow24 <= 4.05
|   |   |--- early_gust <= 59.45
|   |   |   |--- class: 0
|   |   |--- early_gust >  59.45
|   |   |   |--- class: 0
|   |--- new_snow24 >  4.05
|   |   |--- temp_base <= 25.20
|   |   |   |--- class: 0
|   |   |--- temp_base >  25.20
|   |   |   |--- class: 1
|--- early_spd >  56.85
|   |--- avy <= 3.50
|   |   |--- early_gust <= 86.05
|   |   |   |--- class: 1
|   |   |--- early_gust >  86.05
|   |   |   |--- class: 1
|   |--- avy >  3.50
|   |   |--- prec24s <= 4.10
|   |   |   |--- class: 1
|   |   |--- prec24s >  4.10
|   |   |   |--- class: 1
```

Rows are lift-days where the roster said the lift was meant to run (or a whole-side closure); the same caveats as docs/RESULTS.md apply (selection, began-on-hold rows held by definition).
