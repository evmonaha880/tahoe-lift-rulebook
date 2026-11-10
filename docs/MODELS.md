# Models 1 and 2 beside the single wind line

View: the 8 core winters (2018-19 to 2025-26). 12,406 expected lift-days. Leave-one-winter-out: each model is fitted on the other winters and scored on the one left out; counts are summed.
Every method reads only what is known by about 9-10 am: early_gust, early_spd, avy, temp_base, swe24, swe6, prec24s, new_snow24, month, side, lift. Calls are made at 50% probability (models) or at the fitted line.

| Method (pooled) | Precision | Recall | F1 |
|---|---|---|---|
| Model 1: boosted trees (ceiling) | 0.617 | 0.665 | 0.64 |
| Model 2: tree, depth 3 | 0.643 | 0.646 | 0.644 |
| Single early-gust line (fitted) | 0.591 | 0.736 | 0.655 |
| 25 mph rule on early gust | 0.344 | 0.959 | 0.507 |

## Per winter (F1)

| Winter | Model 1: boosted trees (ceiling) | Model 2: tree, depth 3 | Single early-gust line (fitted) | 25 mph rule on early gust |
|---|---|---|---|---|
| 2018-19 | 0.774 | 0.769 | 0.837 | 0.913 |
| 2019-20 | 0.68 | 0.775 | 0.823 | 0.815 |
| 2020-21 | 0.0 | 0.0 | 0.0 | 0.0 |
| 2021-22 | 0.583 | 0.602 | 0.573 | 0.332 |
| 2022-23 | 0.648 | 0.647 | 0.638 | 0.513 |
| 2023-24 | 0.581 | 0.577 | 0.569 | 0.377 |
| 2024-25 | 0.64 | 0.557 | 0.709 | 0.705 |
| 2025-26 | 0.47 | 0.671 | 0.644 | 0.716 |

## Model 2 as if-then rules (fitted on all winters, for reading only; the scores above come from the left-out folds)

```
|--- early_gust <= 71.00
|   |--- swe24 <= 0.95
|   |   |--- new_snow24 <= 1.65
|   |   |   |--- class: 0
|   |   |--- new_snow24 >  1.65
|   |   |   |--- class: 0
|   |--- swe24 >  0.95
|   |   |--- prec24s <= 4.75
|   |   |   |--- class: 1
|   |   |--- prec24s >  4.75
|   |   |   |--- class: 1
|--- early_gust >  71.00
|   |--- avy <= 3.50
|   |   |--- early_gust <= 84.80
|   |   |   |--- class: 1
|   |   |--- early_gust >  84.80
|   |   |   |--- class: 1
|   |--- avy >  3.50
|   |   |--- prec24s <= 4.10
|   |   |   |--- class: 1
|   |   |--- prec24s >  4.10
|   |   |   |--- class: 1
```

Rows are lift-days where the roster said the lift was meant to run (or a whole-side closure); the same caveats as docs/RESULTS.md apply (selection, began-on-hold rows held by definition).
