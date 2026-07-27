# China Borders and Administrative Boundaries

Use this reference when a figure involves China, Chinese provinces/cities, South China Sea context, or clipping/masking to China-region boundaries.

## Default recommendation

For China-region meteorological plots, prefer `cnmaps` over generic global boundary datasets. `cnmaps` is suitable for China national/provincial/city boundaries and common scientific plotting operations such as boundary drawing, clipping, raster masking, and whitening.

Use Cartopy Natural Earth boundaries only for quick global context maps, exploratory drafts, or when the user explicitly asks for them.

## Typical layer hierarchy

Use visually subordinate boundary layers. The meteorological data must remain dominant.

Recommended order:

1. Main scalar field, such as precipitation, temperature, anomaly, reflectivity, humidity, vorticity.
2. Optional contour or vector diagnostics.
3. Coastline and national border.
4. Province/city boundary if needed.
5. Station markers, labels, storm centers, fronts, or analysis annotations.
6. Gridlines and labels.

Recommended visual priority:

- National border: slightly darker and thicker than province/city lines.
- Coastline: clear but not visually dominant.
- Province boundary: light gray and thin unless the map is an administrative product.
- City boundary: use only when useful; usually too noisy for research maps.

## South China Sea and inset handling

For China national maps intended for public release, reports, product pages, or formal presentations, check whether a South China Sea inset or relevant maritime boundary context is required by the project's publication rules.

Do not let an inset dominate the data. Keep it small, consistent, and unobtrusive.

When a South China Sea inset is present, the main panel and inset have distinct
domains:

- The **main panel** shows the compact national view: mainland China, Hainan,
  Taiwan, and nearby waters. Its southern limit should normally be about
  `18°N`; do not extend it to `2°N` merely to include the South China Sea
  islands.
- The **inset** alone shows the South China Sea domain, normally about
  `[105, 123, 2, 25]`.
- Do not derive the main-panel extent from the full multi-polygon China
  boundary collection: the remote southern polygons will enlarge the extent,
  shrink the useful mainland map, create whitespace, and duplicate the inset.
- Data and boundaries may use the full China polygon collection for clipping,
  but the main axes must use the compact main-panel extent. The axes extent,
  not merely the clipping polygon, controls the visible geographic domain.

For a conventional PlateCarree national map with an inset, start from
`MAIN_EXTENT = [73, 136, 18, 54]` and adjust only when the requested data or
publication standard requires it. Use `SCS_EXTENT = [105, 123, 2, 25]` only on
the inset. If the main panel visibly contains the same South China Sea islands
as the inset, the layout is wrong.

When the user wants a filled-contour map clipped to China's boundary **and** a South China Sea inset, refer directly to the complete templates:

- **PlateCarree** (simple rectangular grid): `examples/china-clipped-with-scs-inset.py`
- **Lambert Conformal** (curved boundaries, publication-quality): `examples/china-lambert-scs-inset-right.py` (inset bottom-right) and `examples/china-lambert-scs-inset-left.py` (inset bottom-left)

Both Lambert examples demonstrate the full pattern including projection setup, gridline label handling for Lambert (`x_inline=False`, `y_inline=False`, `rotate_labels=False`), data loading, China boundary query, custom sequential colormap, `contourf` + `clip_contours_by_map` + `draw_map`, `ax.inset_axes()` for the SCS overlay, and colorbar auto-aligned via `fig.colorbar(..., ax=ax)`.

Inset placement uses axes-relative coordinates `[left, bottom, width, height]`. Tune these values to avoid covering landmass or labels in the main map. Typical values:
- Bottom-right: `[0.80, 0.08, 0.21, 0.28]`
- Bottom-left:  `[0.02, 0.07, 0.21, 0.28]`

## Clipping and whitening

Use clipping/whitening when a filled meteorological field should be shown only inside a political or study-area boundary.

Rules:

- State clearly when the field has been clipped or masked.
- Do not imply that data outside the boundary are missing unless they were actually masked for scientific reasons.
- For station interpolation maps, consider masking sparse or unsupported areas instead of filling the whole domain.
- Keep the boundary used for clipping consistent with the boundary shown on the map.

## Common mistakes

- Drawing China boundaries from an arbitrary low-resolution global dataset in a formal China-region figure.
- Using a boundary layer that is visibly offset from the gridded data because of CRS/transform mistakes.
- Making administrative boundaries thicker or brighter than the meteorological signal.
- Showing national maps without considering South China Sea/inset requirements.
- Showing the South China Sea islands in both the national main panel and the
  inset, or using the full China multi-polygon bounds as the main-panel extent.
- Cropping out important upstream/downstream synoptic systems just to fit an administrative frame.
- Using a map boundary source without knowing its provenance for public/commercial output.

## Agent behavior

When generating Python code for China-region maps:

- Prefer `cnmaps` for China/admin boundaries.
- Use Cartopy for map projection and axes.
- Keep boundary styling subtle.
- Include a fallback path only if `cnmaps` is unavailable, and label the fallback as less preferred.
- Avoid downloading boundary files at runtime unless the user explicitly asks.
