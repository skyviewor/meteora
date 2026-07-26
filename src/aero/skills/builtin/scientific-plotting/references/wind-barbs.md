# Unit-Safe Wind Barbs

Read this reference before every Matplotlib `Axes.barbs` or `pyplot.barbs`
call.

## Matplotlib does not know the wind unit

`barbs` calculates magnitude from the supplied `U` and `V` numbers and then
decomposes that number with `barb_increments`. It performs no `m s-1`/knot
conversion and does not inspect xarray unit metadata.

Its defaults are:

```python
{"half": 5, "full": 10, "flag": 50}
```

Those numbers reproduce the familiar `5/10/50` knot convention only when the
input components are in knots. Passing ERA5 `u` and `v` in `m s-1` to the
defaults instead makes them mean `5/10/50 m s-1`, which is not the Chinese
domestic public-meteorological encoding.

## Choose one encoding explicitly

For Chinese domestic public-meteorological charts using `m s-1` components:

```python
barbs = ax.barbs(
    x,
    y,
    u_ms,
    v_ms,
    barb_increments={"half": 2, "full": 4, "flag": 20},
)
```

This encodes a short barb as `2 m s-1`, a long barb as `4 m s-1`, and a
triangle as `20 m s-1`.

For an international aviation-style `5/10/50 kt` display, convert both
components—not only the scalar speed—and retain Matplotlib's defaults:

```python
MS_TO_KT = 1.9438444924406
barbs = ax.barbs(x, y, u_ms * MS_TO_KT, v_ms * MS_TO_KT)
```

Label the figure or legend with the selected unit and convention. Do not both
convert to knots and set `2/4/20` increments.

## Do not mix flag conventions

Matplotlib natively has one `flag` increment and one flag polygon style per
`barbs` collection. `flagcolor` changes its fill color; `fill_empty` controls
the calm-wind circle, not a second flag class.

The verified Chinese public-meteorological rule is one triangle at `20 m s-1`.
Do not claim that native Matplotlib automatically implements a separate hollow
`20 m s-1` flag and solid `50 m s-1` flag. If a product specification requires
both, implement and test custom glyph drawing or separate collections, and cite
that product's standard.

## Control rounding consciously

Matplotlib defaults to `rounding=True`, which rounds magnitude to the nearest
half-barb increment. With `half=2`, the effective quantization is `2 m s-1`;
very small winds may become the calm circle. Use `rounding=False` only when the
product specification calls for truncation, and disclose the choice when exact
threshold behavior matters.

## Validate with synthetic speeds

Before trusting a new style, render a small legend panel with known magnitudes,
for example `0, 2, 4, 6, 20, 24, 40 m s-1`. Verify the decompositions visually
and, when possible, in tests. This catches unit conversion, rounding, and flag
errors before real data obscure them.

Also verify:

- Source `u` and `v` units from metadata.
- Both components use the same conversion.
- The caption states `m s-1` or `kt`.
- Thinning does not change values, only sampled locations.
- Any colorbar encodes its own scalar and does not silently imply barb units.
