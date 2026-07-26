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
