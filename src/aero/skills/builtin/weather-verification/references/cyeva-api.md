# cyeva API and verification reference

This reference documents the cyeva comparison API used by Aerolytica. The managed runtime
installs cyeva 0.2.x; record the installed version and verify method signatures when the
package version changes.

## Imports and paired preprocessing

```python
import numpy as np
from cyeva import (
    Comparison,
    PrecipitationComparison,
    TemperatureComparison,
    WindComparison,
)

obs = np.asarray(obs, dtype=float)
fcst = np.asarray(fcst, dtype=float)
if obs.shape != fcst.shape:
    raise ValueError("Align observation and forecast before verification")

valid = np.isfinite(obs) & np.isfinite(fcst)
obs_eval = obs[valid]
fcst_eval = fcst[valid]
if obs_eval.size == 0:
    raise ValueError("No valid paired samples")
```

Do coordinate/time alignment before this array conversion. cyeva checks equal, non-empty
lengths and drops paired NaNs, but it does not align xarray/pandas coordinates for the
caller and should not be expected to remove infinity.

## Continuous variables

```python
cmp = Comparison(obs_eval, fcst_eval)
rmse = cmp.calc_rmse()
mae = cmp.calc_mae()
mbe = cmp.calc_mbe()
regression = cmp.calc_linregress_args()
```

Use RMSE, MAE, and MBE as a minimal continuous-variable set. Add correlation/regression
only when association is relevant; high correlation does not imply small error.
`calc_chi_square()` is not a default continuous forecast score and needs an explicit
statistical justification.

## Temperature

```python
cmp = TemperatureComparison(obs_eval, fcst_eval, unit="degC")
summary = cmp.gather_all_factors()
```

`TemperatureComparison` converts supported input units to degrees Celsius. Its gathered
factors include RMSE, MAE, RSS, chi-square, and accuracy within 1°C and 2°C. Prefer
selecting and reporting only metrics justified by the task.

## Precipitation

```python
cmp = PrecipitationComparison(obs_eval, fcst_eval, unit="mm")
ts = cmp.calc_ts(kind="24h", lev="+1")
ets = cmp.calc_ets(kind="24h", lev="+1")
bias = cmp.calc_bias_score(kind="24h", lev="+1")
hit = cmp.calc_hit_ratio(kind="24h", lev="+1")
miss = cmp.calc_miss_ratio(kind="24h", lev="+1")
far = cmp.calc_false_alarm_ratio(kind="24h", lev="+1")
```

Supported `kind` values are `1h`, `3h`, `12h`, and `24h`.

- `lev="0"` means occurrence versus no precipitation.
- `lev="1"` through `"6"` mean an exact, mutually exclusive category.
- `lev="+1"` through `"+6"` mean that category or higher, suitable for threshold
  contingency scores.
- One-hour precipitation has no separate level 6; cyeva maps it to level 5.

Thresholds in millimetres:

| kind | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1h | <0.1 | 0.1–1.9 | 2–4.9 | 5–9.9 | 10–19.9 | >=20 | n/a |
| 3h | <0.1 | 0.1–2.9 | 3–9.9 | 10–19.9 | 20–49.9 | 50–69.9 | >=70 |
| 12h | <0.1 | 0.1–4.9 | 5–14.9 | 15–29.9 | 30–69.9 | 70–139.9 | >=140 |
| 24h | <0.1 | 0.1–9.9 | 10–24.9 | 25–49.9 | 50–99.9 | 100–249.9 | >=250 |

Always put `kind`, `lev`, and the corresponding physical threshold next to TS/ETS/Bias
results.

## Wind

```python
cmp = WindComparison(
    obs_spd=obs_speed,
    fct_spd=fcst_speed,
    obs_dir=obs_direction,
    fct_dir=fcst_direction,
    unit_spd="m/s",
    unit_dir="degree",
)
speed_mae = cmp.calc_mae(kind="speed")
direction_accuracy = cmp.calc_dir_accuracy_ratio(mode="degree", threshold=22.5)
direction_score = cmp.calc_dir_score(dnum=8)
```

Other available methods include `calc_speed_accuracy_ratio(limit=2)`,
`calc_wind_scale_accuracy_ratio(...)`, `calc_wind_scale_stronger_ratio()`,
`calc_wind_scale_weaker_ratio()`, and `calc_speed_score()`.

Direction errors are circular: 359° and 1° differ by 2°, not 358°. Define a calm-wind
threshold before direction verification because direction is unstable or undefined in
calm conditions. cyeva's wind-sector implementation carries an upstream FIXME around
minimal-sector logic, so manually spot-check values around 0°/360° and sector boundaries.

## Metric interpretation

| metric | preferred direction | interpretation |
| --- | --- | --- |
| RMSE | lower | penalizes large errors more strongly |
| MAE | lower | mean absolute error in the variable's unit |
| MBE | zero | signed mean error; positive means forecast high |
| accuracy / hit ratio | higher | definition depends on class/threshold |
| miss / false-alarm ratio | lower | event failure components |
| TS | higher | hits divided by hits, misses, and false alarms |
| ETS | higher | TS adjusted for random hits |
| Bias score | 1 | >1 overforecast events; <1 underforecast events |

## Reproducibility and caveats

- cyeva evaluates deterministic forecasts; it is not a probabilistic ensemble verification
  package.
- Some APIs round returned values. Keep unrounded independent checks when precision matters.
- Empty categories and zero contingency denominators can produce NaN. Report them as
  undefined with the sample/event counts.
- Do not rely on `gather_all_*` as an automatic report: it may include metrics inappropriate
  for the scientific question.
- Record cyeva version, data period, lead-time definition, spatial matching method, units,
  thresholds, and valid-pair counts.
