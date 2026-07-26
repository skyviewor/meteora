# Wind Vectors in Atmospheric Cross-Sections

Read this reference whenever a vertical section contains quivers, arrows,
barbs, streamlines, vertical velocity, or circulation.

For horizontal wind barbs, also read `wind-barbs.md`; its unit and increment
rules apply equally to maps and cross-sections.

## Choose the vector product first

Select exactly one interpretation before plotting:

1. **Horizontal wind barbs at section samples**: plot `(u, v)` as conventional
   meteorological barbs and label them as horizontal wind. They do not show
   circulation in the section plane.
2. **Schematic in-plane circulation**: plot along-section horizontal wind
   against a deliberately rescaled vertical component. Disclose the scaling;
   arrow angle is illustrative rather than physical.
3. **Physical trajectory or true inclination**: reconcile coordinate units,
   axes aspect, vertical exaggeration, and velocity units. Prefer trajectory or
   streamline integration when actual parcel paths are the scientific target.

Do not let one arrow silently claim to encode horizontal speed, vertical speed,
direction, and true inclination simultaneously. A useful default is vertical
velocity shading plus schematic circulation arrows.

## Project horizontal wind onto the section

For an angle `theta` measured counterclockwise from east:

```python
along = u * np.cos(theta) + v * np.sin(theta)
normal = -u * np.sin(theta) + v * np.cos(theta)
```

Use `u` for a west-to-east section and `v` for a south-to-north section. Reverse
the sign when the displayed path direction is reversed.

For a meteorological azimuth `phi`, measured clockwise from north:

```python
along = u * np.sin(phi) + v * np.cos(phi)
```

For a curved path, calculate the local tangent at every path point rather than
using one angle for the whole section. State endpoints and display direction.

## Keep omega and w distinct

- ERA5 pressure-level `vertical_velocity` is normally pressure velocity
  `omega = dp/dt` in `Pa s-1`; positive omega indicates descent.
- Geometric vertical velocity `w = dz/dt` is in `m s-1`; positive `w` indicates
  ascent.
- Never label omega as `w` or `m s-1`. Under an explicitly stated hydrostatic
  approximation, convert with `w = -omega / (rho * g)` using a defensible
  density field.
- On a pressure-coordinate section, `(along, omega)` is the native pair. On a
  height-coordinate section, `(along, w)` is the native pair. Verify that the
  displayed arrow points upward for ascent after applying the reversed pressure
  axis.

## Scale vectors deliberately

Horizontal and vertical velocities commonly differ by orders of magnitude, and
the section itself is already vertically exaggerated. Treat axis aspect and
component scaling as separate choices.

For a schematic circulation plot:

```python
vertical_factor = 20.0
vertical_display = vertical * vertical_factor
```

Estimate a starting factor from robust typical magnitudes, then inspect factors
such as 10, 20, and 50. Use the smallest factor that reveals coherent ascent
and descent without making most arrows nearly vertical. Do not hard-code 20 as
a universal physical constant.

Prefer `angles="uv"` for explicitly schematic screen-space direction. Use
`angles="xy"` only when coordinate units, component units, axis aspect, and
scale have been reconciled and documented. Neither choice automatically makes
the displayed angle a true airflow inclination.

## Separate magnitude from direction when useful

When the goal is circulation structure, normalize the display vectors:

```python
magnitude = np.hypot(along, vertical_display)
valid = magnitude > threshold
along_dir = np.where(valid, along / magnitude, np.nan)
vertical_dir = np.where(valid, vertical_display / magnitude, np.nan)
```

State that normalized arrow lengths no longer encode speed. Show magnitude in a
separate scalar layer, such as vertical velocity shading or horizontal wind
speed contours.

Mask weak vectors whose directions are noise-dominated. Determine quiver scale
from a robust percentile rather than one extreme value. If vectors are clipped
or winsorized for display, retain the original data for analysis and disclose
the display-only clipping.

## Thin and label vectors

- Thin horizontal and vertical dimensions independently.
- Target readable spacing at final export size; do not select strides only from
  source-grid dimensions.
- Preserve important gradients without covering the scalar field.
- Add a reference arrow whenever length carries magnitude.
- State what the key represents. When the vertical component is exaggerated,
  use wording such as `10 m s-1 horizontal; omega ×20` rather than implying one
  true two-dimensional speed.
- Put the multiplier, units, normalization, and clipping in the figure itself
  or its caption—not only in terminal output.

## Recommended layer design

For an in-plane circulation section:

- Filled shading: signed `w` or omega with a zero-centered diverging colormap.
- Optional contours: potential temperature, humidity, reflectivity, or another
  scientifically relevant scalar.
- Quivers: `(along, scaled vertical)` with restrained thinning.
- Terrain and underground mask: visible and consistent.
- Annotation: component definition, vertical multiplier, vector key, valid
  time, section direction, and units.

For horizontal-wind-only data:

- Filled shading: `sqrt(u**2 + v**2)` if wind-speed magnitude is useful.
- Barbs: `(u, v)`, explicitly labeled horizontal wind at section samples.
- Do not describe these barbs as vertical circulation.

## Acceptance checks

Before delivery, inspect the exported image and verify:

- The chosen components match section direction.
- Omega/w name, unit, and ascent/descent sign are correct.
- Arrow direction remains correct after pressure-axis inversion.
- Vertical scaling and normalization are visibly disclosed.
- The vector key describes the horizontal reference and vertical multiplier.
- Weak/noisy and extreme vectors do not dominate the plot.
- Vectors are readable at exported size and do not obscure terrain or shading.
- No statement interprets an exaggerated arrow angle as a real parcel slope.
