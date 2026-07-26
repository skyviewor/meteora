---
name: era5-cds
description: Use when requesting, validating, downloading, or troubleshooting ERA5 data from the Copernicus Climate Data Store (CDS), including hourly or monthly ERA5 datasets, pressure-level variables, availability errors, and CDS request parameters.
---

# ERA5 CDS

Use this skill for all ERA5 requests sent to CDS, especially when choosing an
hourly dataset, a pressure-level variable, an exact time, or diagnosing a CDS
submission error.

## Request rules

- Use a pressure-level dataset and provide `pressure_level` for high-air
  variables such as `potential_vorticity`. Do not use a pressure level for
  single-level variables.
- For an hourly request for one date, preserve the complete date tuple:
  `year`, `month`, `day`, and the requested `time` list. A selected time must
  not silently remove the requested day.
- Use monthly-means datasets only for monthly products; they do not accept a
  day-level workflow.

## Availability and failures

- Do not state or assume a fixed "five-day" ERA5 publication delay. Dataset
  availability differs between products and can change over time. Treat the
  CDS response or availability check as the authority.
- If a historical date that should plainly exist returns a generic "data not
  available yet" / `400 invalid request` response, suspect malformed request
  parameters first. Verify the dataset, variable, pressure level, day, time,
  and output options before changing the requested date.
- A `400 invalid request` is not transient: do not automatically retry it or
  keep falling back to arbitrary older dates. Return the actionable validation
  error instead.
- Retry only genuinely transient failures such as connection errors,
  temporary server errors, or rate limiting.

## User-facing communication

- Explain the exact dataset, variable, level, UTC time, and geographic area
  before submitting a download.
- When CDS rejects a request, distinguish an invalid request from a real
  availability delay. Do not claim that an old historical date is unpublished
  without verifying the request itself.
