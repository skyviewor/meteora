# Meteorological Maps

Use this reference for map projections, map layers, contours, wind vectors, precipitation maps, radar/satellite maps, and vertical cross-sections.

## Projection rules

Choose projection by domain:

- China/East Asia: Lambert Conformal or PlateCarree depending on purpose.
- Mid-latitude regional maps: Lambert Conformal is often appropriate.
- Polar maps: Polar Stereographic.
- Global maps: Robinson, Mollweide, or another global projection suitable for the message.
- Quick lon-lat gridded diagnostics: PlateCarree is acceptable.

Always distinguish map projection from data CRS. For longitude-latitude data in Cartopy, use `transform=ccrs.PlateCarree()` even when the map axes use another projection.

## Coordinate checks

- Confirm longitude and latitude coordinate names, order, and units.
- Confirm whether longitude is `0..360` or `-180..180`; convert only when needed for the requested region.
- Show the map extent that matches the user's requested region.

## Display domain and clipping domain

Decide the map's semantic domain before choosing its extent or applying a clip:

- For a regional synoptic map (East Asia, Europe, global, etc.), plot the field
  across the requested regional domain. Administrative boundaries are overlays;
  do not clip the field to one country.
- For a country/province thematic map, clip or mask the field to that
  administrative geometry and fit the axes extent to the same geometry, with a
  small deliberate margin.
- Do not use a broad regional `set_extent(...)` together with
  `clip_contours_by_map(...)` for one country merely to leave the surrounding
  region blank. This creates misleading empty space and is not a layout problem.
- White regions must have a clear meaning: outside the requested administrative
  domain, missing/masked data, or an intentional no-data category. If the plotted
  field occupies only a small part of the axes, verify the extent, mask, and clip
  before adjusting `figsize`, subplot margins, or export cropping.
- For a national China map with a South China Sea inset, treat duplication as a
  domain error, not as ordinary canvas whitespace. The main axes should normally
  stop near 18°N (`[73, 136, 18, 54]` is a useful PlateCarree default), while the
  inset alone covers approximately `[105, 123, 2, 25]`. If the remote South China
  Sea islands are visible in both panels, correct the two extents before doing
  any Figure-size calibration.
- After the domain is correct, derive the canvas aspect from the **rendered
  GeoAxes**, not from the downloaded grid's longitude/latitude spans and not
  from a landscape default. Fixed-aspect GeoAxes cannot stretch to fill an
  incompatible canvas. In particular, `lon_span / lat_span` is not a reliable
  rendered panel ratio: Cartopy projection geometry and the actual
  `set_extent(...)` determine the axes box, while titles, tick labels, colorbars,
  and insets determine how much of the Figure remains available.
- Reserve title and horizontal-colorbar space vertically. Never add arbitrary
  side width such as `panel_width + 0.8`; that constant repeatedly creates
  symmetric left/right whitespace.

For a one-panel map, start with a conservative canvas, render once, and correct
the Figure width from the measured main-axes occupancy. This is layout
calibration, not pixel cropping:

```python
fig, ax = plt.subplots(
    figsize=(6.4, 5.0),
    layout="compressed",
    subplot_kw={"projection": ccrs.PlateCarree()},
)

# Add the map, extent, ticks, title, inset, and layout-aware colorbar first.
# Then measure the actual GeoAxes box after Cartopy and the layout engine run.
fig.canvas.draw()
target_axes_width_fraction = 0.82
actual_axes_width_fraction = ax.get_position().width

if actual_axes_width_fraction < target_axes_width_fraction:
    width, height = fig.get_size_inches()
    corrected_width = width * (
        actual_axes_width_fraction / target_axes_width_fraction
    )
    fig.set_size_inches(corrected_width, height, forward=True)
    fig.canvas.draw()
```

Use a target around `0.78..0.84`, leaving room for y tick labels while avoiding
large symmetric side margins. Apply at most one correction during normal
generation; if the result remains outside that range, inspect the extent,
layout owner, and decoration placement instead of looping blindly. Do not
change the height in this correction because it is already reserving the
suptitle, x tick labels, and horizontal colorbar. Run the normal canvas-bound
checks after the correction and inspect the exported raster.

For multi-panel figures, use the aspect-aware grid method in the main skill
instead of independently resizing each axes. For non-PlateCarree projections,
the same rendered-occupancy calibration is safer than hand-computing a
projection ratio. Do not solve whitespace with `bbox_inches="tight"`.

```python
# East Asia PV map: retain the complete field and overlay boundaries.
ax.contourf(lon, lat, pv, transform=ccrs.PlateCarree(), extend="both")
draw_maps(country_boundaries, ax=ax)
ax.set_extent([100, 150, 10, 55], crs=ccrs.PlateCarree())

# China-only thematic map without a South China Sea inset: clip and fit the view
# to the requested China geometry. With an inset, use the separate main/inset
# extents described above instead of the full multi-polygon bounds.
cs = ax.contourf(lon, lat, pv, transform=ccrs.PlateCarree(), extend="both")
clip_contours_by_map(cs, china_map, ax=ax)
west, south, east, north = china_map.get_extent()
ax.set_extent([west, east, south, north], crs=ccrs.PlateCarree())
```

## Global fill maps and the cyclic-point seam

When plotting a **global filled-contour map** with `contourf` or `pcolormesh` where the longitude coordinate spans 0° to 360° (or -180° to 180°), a narrow **white line (gap)** appears at the 0°/360° meridian boundary. This is caused by the longitude array not wrapping — the last column at 360° does not connect back to the first column at 0°.

### Solution: `cartopy.util.add_cyclic_point`

Always call `add_cyclic_point` before plotting global fill maps. It appends the first longitude (wrapped to 360°) as a new column, closing the seam.

```python
import cartopy.crs as ccrs
from cartopy.util import add_cyclic_point
import matplotlib.pyplot as plt
import xarray as xr

ds = xr.open_dataset("data.nc")
field = ds["var"]          # shape: (time, lat, lon), lon 0..360

data_wrapped, lon_wrapped = add_cyclic_point(field.values, coord=ds["lon"].values)

fig = plt.figure()
ax = plt.axes(projection=ccrs.Robinson())
ax.set_global()
cf = ax.contourf(lon_wrapped, ds["lat"].values, data_wrapped,
                 transform=ccrs.PlateCarree())
```

### When `add_cyclic_point` is needed

- **Global fill map** (`contourf` or `pcolormesh`) with global extent → **always**.
- Global contour-only map (`contour`, not filled) → the seam is usually invisible, but using it is still safe.
- **Regional map** with extent well within the data range → **not needed**.
- `imshow` on a PlateCarree axis → not applicable (use `contourf`/`pcolormesh` instead).

### Additional note for xarray data

`add_cyclic_point` expects raw numpy arrays. The longitude coordinate (1-D) must be passed as `coord=...`, and the data array should be the numpy `.values`. For data with a time dimension, pass a 2-D slice (e.g. `field.isel(time=0).values`).

## Layering rules

A clean meteorological map has a clear primary variable.

Common combinations:

- Precipitation fill + administrative boundary + optional station markers.
- 500 hPa geopotential height contours + 850 hPa wind vectors.
- Wind speed fill + wind vectors or barbs.
- Vorticity/divergence fill + geopotential height contours.
- Moisture flux divergence fill + moisture flux vectors.
- Satellite/radar raster + boundary overlay + storm annotations.

Avoid stacking more than three scientific layers unless there is a strong reason.

## Contours

Use contours for fields where structure matters more than smooth color impression:

- Geopotential height
- Sea-level pressure
- Temperature threshold lines
- 0 °C line
- Specific humidity or equivalent potential temperature when used diagnostically

Rules:

- Use meaningful intervals.
- Label only enough contours to interpret values.
- Use subtle colors unless the contour is the main variable.
- Emphasize key contours intentionally, such as 588 dagpm, 0 °C, or 1010 hPa.

## Wind vectors and barbs

Wind arrows and barbs must be thinned.

Rules:

- Do not draw every grid point on high-resolution fields.
- Use a vector key, such as 10 m/s.
- Keep arrow color readable against the background.
- Use barbs for weather-map style or station-like wind display.
- Use streamlines for qualitative flow structure, not precise point-by-point values unless supported by color/labels.

### Wind barb increments (Chinese convention)

Read `wind-barbs.md` before every Matplotlib wind-barb plot. Matplotlib treats
the supplied components and `barb_increments` as unitless numbers; it does not
convert units automatically.

| Symbol | Speed (m/s) |
|--------|-------------|
| Short barb | 2 |
| Long barb | 4 |
| Triangle flag | 20 |

Matplotlib's defaults (`half=5, full=10, flag=50`) reproduce the common knot
convention only when `U` and `V` are supplied in knots. When wind components
are in `m/s` and the user expects Chinese domestic public-meteorological
charting, **always** set:

```python
ax.barbs(lons, lats, u, v, barb_increments={"half": 2, "full": 4, "flag": 20})
```

Limitations:

- Matplotlib native `barbs` has only one flag increment/style per collection.
  Do not claim it automatically distinguishes hollow `20 m/s` and solid
  `50 m/s` flags. A product requiring two flag classes needs custom,
  specification-tested glyph drawing.

## Precipitation maps

Rules:

- State accumulation window.
- Use discrete, interpretable thresholds.
- Make no-rain or trace values white/transparent or visually weak.
- Use fixed levels across comparisons and animations.
- Avoid over-smoothing convective precipitation.

## Radar maps

Rules:

- Label dBZ and product type.
- Use dBZ-specific levels.
- Preserve convective structure unless smoothing is explicitly part of processing.
- Mark interpolated, nowcast, AI-filled, or QC-modified frames honestly.
- Keep animation color levels fixed.

## Satellite maps

Rules:

- State satellite, sensor/channel, product, and time when available.
- Visible imagery should not be used for nighttime cloud analysis unless the product supports it.
- Infrared brightness temperature should state unit and channel.
- Enhanced colors are acceptable, but do not overinterpret artificial color boundaries.

## Vertical cross-sections

Rules:

- Reverse pressure axis: high pressure near bottom, low pressure near top.
- Show terrain/masked underground region when crossing topography.
- State cross-section endpoints and coordinate path.
- If vectors are plotted in cross-section, clarify horizontal/vertical scaling and units.
- Provide a plan-view locator map when the section path is not obvious.

## Station interpolation maps

Rules:

- Show station points or state station count.
- State interpolation method and resolution.
- Mask unsupported sparse regions where needed.
- Do not present interpolated fields as direct observations.
- Consider representativeness errors in mountains, deserts, coastlines, and sparse western China regions.

## Common mistakes

- Wrong Cartopy `transform`, causing data/boundary misalignment.
- Dense arrows, dense contour labels, or dense station labels.
- Projection distortion ignored in global/high-latitude plots.
- Figure extent crops important synoptic context.
- Boundary layers visually dominate the meteorological signal.
- **Global fill map white-line seam**: forgetting `add_cyclic_point` on global `contourf`/`pcolormesh`. See "Global fill maps and the cyclic-point seam" above.
