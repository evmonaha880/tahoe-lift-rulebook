# Models 1 and 2 beside the single wind line

View: the 8 core winters (2018-19 to 2025-26), named-roster lift-days only. 11,905 expected lift-days. Leave-one-winter-out: each model is fitted on the other winters and scored on the one left out; counts are summed.
Every method reads only what is known by about 9-10 am: early_gust, early_spd, avy, temp_base, swe24, swe6, prec24s, new_snow24, month, side, lift. Calls are made at 50% probability (models) or at the fitted line.

| Method (pooled) | Precision | Recall | F1 |
|---|---|---|---|
| Model 1: boosted trees (ceiling) | 0.58 | 0.6 | 0.59 |
| Model 2: tree, depth 3 | 0.618 | 0.551 | 0.583 |
| Single early-gust line (fitted) | 0.548 | 0.715 | 0.621 |
| 25 mph rule on early gust | 0.313 | 0.957 | 0.471 |

## Per winter (F1)

| Winter | Model 1: boosted trees (ceiling) | Model 2: tree, depth 3 | Single early-gust line (fitted) | 25 mph rule on early gust |
|---|---|---|---|---|
| 2018-19 | 0.705 | 0.705 | 0.831 | 0.906 |
| 2019-20 | 0.621 | 0.565 | 0.825 | 0.814 |
| 2020-21 | 0.0 | 0.0 | 0.0 | 0.0 |
| 2021-22 | 0.534 | 0.552 | 0.525 | 0.301 |
| 2022-23 | 0.587 | 0.602 | 0.595 | 0.467 |
| 2023-24 | 0.548 | 0.445 | 0.496 | 0.339 |
| 2024-25 | 0.624 | 0.685 | 0.725 | 0.687 |
| 2025-26 | 0.353 | 0.317 | 0.672 | 0.695 |

## Model 2 as if-then rules (fitted on all winters, for reading only; the scores above come from the left-out folds)

```
|--- early_gust <= 71.00
|   |--- swe24 <= 0.95
|   |   |--- new_snow24 <= 4.05
|   |   |   |--- class: 0
|   |   |--- new_snow24 >  4.05
|   |   |   |--- class: 0
|   |--- swe24 >  0.95
|   |   |--- prec24s <= 4.75
|   |   |   |--- class: 1
|   |   |--- prec24s >  4.75
|   |   |   |--- class: 1
|--- early_gust >  71.00
|   |--- early_gust <= 84.80
|   |   |--- early_gust <= 83.20
|   |   |   |--- class: 1
|   |   |--- early_gust >  83.20
|   |   |   |--- class: 0
|   |--- early_gust >  84.80
|   |   |--- temp_base <= 28.89
|   |   |   |--- class: 1
|   |   |--- temp_base >  28.89
|   |   |   |--- class: 1
```

Rows are lift-days where the roster said the lift was meant to run (or a whole-side closure); the same caveats as docs/RESULTS.md apply (selection, began-on-hold rows held by definition).
