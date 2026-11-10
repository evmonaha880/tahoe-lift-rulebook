# Models 1 and 2 beside the single wind line

View: 10 winters (2016-17 to 2025-26; no estimated wind). 13,465 expected lift-days. Leave-one-winter-out: each model is fitted on the other winters and scored on the one left out; counts are summed.
Every method reads only what is known by about 9-10 am: early_gust, early_spd, avy, temp_base, swe24, swe6, prec24s, new_snow24, month, side, lift. Calls are made at 50% probability (models) or at the fitted line.

| Method (pooled) | Precision | Recall | F1 |
|---|---|---|---|
| Model 1: boosted trees (ceiling) | 0.653 | 0.681 | 0.666 |
| Model 2: tree, depth 3 | 0.654 | 0.591 | 0.621 |
| Single early-gust line (fitted) | 0.612 | 0.736 | 0.668 |
| 25 mph rule on early gust | 0.375 | 0.958 | 0.539 |

## Per winter (F1)

| Winter | Model 1: boosted trees (ceiling) | Model 2: tree, depth 3 | Single early-gust line (fitted) | 25 mph rule on early gust |
|---|---|---|---|---|
| 2016-17 | 0.794 | 0.564 | 0.769 | 0.82 |
| 2017-18 | 0.611 | 0.491 | 0.769 | 0.809 |
| 2018-19 | 0.771 | 0.78 | 0.837 | 0.913 |
| 2019-20 | 0.633 | 0.763 | 0.823 | 0.815 |
| 2020-21 | 0.0 | 0.0 | 0.0 | 0.0 |
| 2021-22 | 0.603 | 0.583 | 0.573 | 0.332 |
| 2022-23 | 0.663 | 0.609 | 0.638 | 0.513 |
| 2023-24 | 0.602 | 0.593 | 0.559 | 0.377 |
| 2024-25 | 0.597 | 0.615 | 0.691 | 0.705 |
| 2025-26 | 0.658 | 0.375 | 0.644 | 0.716 |

## Model 2 as if-then rules (fitted on all winters, for reading only; the scores above come from the left-out folds)

```
|--- early_gust <= 71.00
|   |--- new_snow24 <= 4.05
|   |   |--- early_gust <= 59.45
|   |   |   |--- class: 0
|   |   |--- early_gust >  59.45
|   |   |   |--- class: 0
|   |--- new_snow24 >  4.05
|   |   |--- temp_base <= 29.92
|   |   |   |--- class: 0
|   |   |--- temp_base >  29.92
|   |   |   |--- class: 1
|--- early_gust >  71.00
|   |--- avy <= 3.50
|   |   |--- new_snow24 <= 1.95
|   |   |   |--- class: 1
|   |   |--- new_snow24 >  1.95
|   |   |   |--- class: 1
|   |--- avy >  3.50
|   |   |--- prec24s <= 4.10
|   |   |   |--- class: 1
|   |   |--- prec24s >  4.10
|   |   |   |--- class: 1
```

Rows are lift-days where the roster said the lift was meant to run (or a whole-side closure); the same caveats as docs/RESULTS.md apply (selection, began-on-hold rows held by definition).
