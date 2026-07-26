# Atmospheric Vertical Cross-Sections

Use these rules for latitude-pressure, longitude-pressure, distance-pressure,
and height-coordinate atmospheric sections.

For an ERA5 north-south pressure section, start from
`../examples/era5-meridional-pressure-cross-section.py`. Preserve its
coordinate-based selection, order-independent terrain interpolation, shared
terrain mask/fill, pressure-axis assertion, and diagnostic output.

When plotting arrows, barbs, vertical velocity, or circulation, also read
`cross-section-wind-vectors.md`. It defines projection, omega/w semantics,
scaling, normalization, thinning, vector keys, and disclosure requirements.

## Define the section before downloading

- State endpoints or the fixed longitude/latitude and traversal direction.
- Select pressure levels dense enough to resolve the requested structure.
  Prefer available standard levels and preserve their coordinate values; do not
  use a few widely spaced levels merely to reduce request count.
- For ERA5, batch all required pressure levels with the same variables, time,
  and area in one pressure-level request. Request surface fields separately.
- Inspect coordinate names, order, units, ranges, NaNs, and grid alignment
  before calculations. Select each dataset by coordinate
  (`.sel(..., method="nearest")`), not by reusing another dataset's integer
  index.

## Use scientifically valid vector components

Choose the vector meaning explicitly:

- Zonal section: use zonal wind `u` as the along-section component.
- Meridional section: use meridional wind `v` as the along-section component.
- Arbitrary path: project `(u, v)` onto the path tangent.
- In-plane circulation vectors require along-section wind plus vertical
  velocity (`omega` on pressure coordinates or `w` on height coordinates).
  State units and any visual scale factor because horizontal and vertical
  components have different units and magnitudes.
- `(u, v)` barbs at cross-section sample points represent horizontal wind only.
  They are acceptable if explicitly labeled as horizontal wind barbs, but must
  not be described as in-plane vertical circulation.

Horizontal wind speed shading may use `sqrt(u**2 + v**2)`, with a clearly
labeled `m s-1` colorbar.

## Orient pressure coordinates correctly

Show high pressure at the bottom and low pressure at the top. Set the final
limits in the intended order:

```python
ax.set_ylim(1050, 400)
```

Do not call `invert_yaxis()` and then overwrite it with ascending `set_ylim`.
After all axis operations, assert:

```python
assert ax.get_ylim()[0] > ax.get_ylim()[1]
```

Use a logarithmic pressure axis when scientifically useful, and disclose it.

## Derive and draw terrain robustly

Convert geopotential to geopotential height with `height = z / 9.80665`; verify
whether the source `z` is in `m2 s-2` before conversion.

To derive terrain pressure from pressure-level geopotential height:

1. At each horizontal position, retain finite `(height, pressure)` pairs.
2. Sort pairs by height before interpolation; never assume the stored pressure
   dimension is ascending or descending.
3. Interpolate `log(pressure)` as a function of height.
4. Handle terrain below the lowest or above the highest available level
   explicitly rather than silently assigning a plot boundary.

Create one `underground` mask from `level_height < terrain_height`. Apply it to
every pressure-level field, then fill the matching region from terrain pressure
to the high-pressure plot boundary in an opaque terrain color. A white masked
region without visible terrain fill is a failed plot.

## Interpolate without inventing structure

- Prefer log-pressure interpolation for pressure-coordinate vertical
  refinement.
- Do not extrapolate through terrain or across missing columns.
- Disclose vertical and path interpolation. Never imply interpolated levels
  were directly downloaded.
- Avoid contours from too few vertical levels; add source levels or use
  restrained, documented interpolation.

## Mandatory acceptance checks

Inspect both calculated arrays and the exported image:

- Pressure ticks decrease upward; 1000 hPa is below 400 hPa.
- Terrain is visible and coincides with masked underground cells.
- No unexplained blank wedge or central void remains.
- Section direction, location/endpoints, valid time and time zone are stated.
- Vector legend/label identifies components, units, thinning, and scale.
- Colorbar identifies the scalar variable and unit.
- A few terrain-pressure and mask fractions are numerically plausible.
- Open the saved image and reject it if axis orientation, terrain, vectors, or
  primary data are visually inconsistent.
