---
name: weather-verification
description: Use for 气象准确率测评、预报检验、预报与观测对比、模式评估, or deterministic weather forecast verification with cyeva, including RMSE, MAE, MBE, temperature accuracy, precipitation TS/ETS/Bias, and wind speed or direction scores.
---

# Weather Verification with cyeva

Use `cyeva` as the metric implementation for deterministic meteorological forecast
verification. Treat alignment and quality control as part of the result, not as optional
preprocessing.

## Required workflow

1. Establish the verification definition before calculating:
   - variable and units;
   - observation and forecast sources;
   - valid time, lead time, station/grid identity, and aggregation period;
   - spatial/temporal pooling or stratification;
   - for precipitation, accumulation duration and category/threshold.
   Ask a short clarification only when an unresolved choice would materially change the
   result.
2. Inspect both datasets and align them by valid time plus station or grid location. Never
   flatten two independently ordered arrays and compare them by position.
3. Harmonize units, coordinates, calendars, time zones, accumulation windows, and spatial
   resolution. Regridding or interpolation must be disclosed.
4. Build one paired validity mask over observation and forecast. Remove NaN and infinity
   together, then report original count, matched count, rejected count, and coverage.
5. Select the cyeva comparison class and a small, justified metric set:
   - general continuous fields: `Comparison`, normally RMSE, MAE, and MBE;
   - temperature: `TemperatureComparison`, including within-1°C/within-2°C accuracy when
     useful;
   - precipitation: `PrecipitationComparison`, using the correct accumulation duration and
     exact category or cumulative threshold;
   - wind: `WindComparison`, evaluating speed and circular direction separately.
6. Stratify by lead time and, when relevant, station, region, season, or intensity. State
   whether a reported aggregate is pooled over all pairs or averaged across groups.
7. Independently spot-check at least one continuous metric or contingency-table count with
   NumPy. Investigate NaN or zero-division results instead of silently replacing them.
8. Deliver a compact table, sample/QC summary, metric interpretation, and limitations. Do
   not label a single score as overall “accuracy.”

Before writing evaluation code, read
[`references/cyeva-api.md`](references/cyeva-api.md) for exact methods, precipitation
levels, metric directions, and known limitations.

## Runtime and plotting

- First test `import cyeva` and record `cyeva.__version__` when available. cyeva is beta, so
  preserve the version used in reproducible output.
- If it is missing, follow `conda-helper`: install it only into Aero's managed interpreter
  with `~/.aero/runtime/envs/aero-agent/bin/python -m pip install -U cyeva`. Never modify
  the user's Conda base environment.
- If the request includes a figure, also use `scientific-plotting`. Plots complement the
  numeric verification table; they do not replace it.

## Hard rules

- Do not compare unmatched timestamps, stations, grids, levels, or accumulation periods.
- Do not mix units or infer precipitation duration from the value magnitude.
- Preserve signed MBE: positive means the forecast is higher than the observation.
- For wind direction, use circular differences and define handling of calm winds.
- Report threshold definitions beside categorical precipitation scores.
- Keep sample count beside every subgroup score; tiny groups must be flagged.
