# Time Series and Verification Plots

Use this reference for meteorological time series, station comparisons, model verification curves, ensemble plots, and accumulated variables.

## Time axis

Rules:

- State UTC, local time, or Beijing Time clearly.
- Use consistent tick formatting.
- Avoid overcrowded timestamps.
- For forecasts, distinguish initialization time, valid time, and lead time.
- For accumulated variables, show the accumulation interval.

## Variable display conventions

Common choices:

- Temperature, pressure, wind speed: line chart.
- Precipitation amount: bar chart or step-like accumulated curve.
- Accumulated precipitation: cumulative line with clear reset/window logic.
- Wind direction: special handling because it is circular.
- Visibility: consider log scale only if clearly labeled.

## Multiple variables

Rules:

- Avoid dual y-axes unless necessary.
- If using dual axes, label both units clearly and avoid implying false correlation.
- Prefer separate aligned panels when variables differ strongly.
- Use line styles and markers, not color alone.

## Observations vs forecasts

Rules:

- Distinguish observed, analysis, nowcast, forecast, and reanalysis.
- Use consistent line style across figures.
- Include sample count or missing-data handling when relevant.
- Do not join long gaps without marking missing values.
- For averages, state the averaging region and whether missing values were skipped.

## Ensemble and uncertainty

Rules:

- Use median/mean plus percentile bands when showing ensembles.
- Keep uncertainty shading transparent and subordinate.
- State ensemble size and percentile range.

## Verification plots

Rules:

- Scatter plots should include 1:1 line.
- Dense scatter should use density/hexbin or transparency.
- Taylor diagrams should define standard deviation normalization and reference dataset.
- Boxplots must define whiskers and outliers.
- Skill scores should state baseline/reference.

## Maximum, minimum, and event annotations

Do not place every point label with a fixed upward offset. An extreme often lies
near an axes edge, so `xytext=(0, 10)` can collide with the title, frame, or
legend. Use this sequence:

1. Mark the selected point explicitly and reserve a small data-free annotation
   band beyond the extreme. For a two-line label, normally add 12-20% of the
   data range above a maximum or below a minimum. This is preferable to placing
   the label over a dense part of the series. Do not enlarge the whole canvas
   merely to make room for one label.
2. Try the data-free side of the point first: above a maximum and below a
   minimum. Near the right edge, extend text left with `ha="right"`; near the
   left edge, extend it right with `ha="left"`. Fall back to other quadrants
   only when the preferred label does not fit.
3. Use `textcoords="offset points"` so the visual separation is stable across
   date ranges and units. Prefer a short two-line label and a subtle opaque or
   semi-opaque text box over a long sentence.
4. Keep the legend away from the annotated extreme. If the legend and label
   want the same corner, move the legend or try another annotation quadrant;
   never draw one over the other.
5. After `fig.canvas.draw()`, compare the annotation's rendered bounding box
   with the axes and legend bounding boxes, and count plotted data points
   covered by the box. Score every candidate rather than accepting the first
   one that fits. Prefer, in order: inside the axes, no legend collision, the
   fewest covered points, then the shortest leader.

For a single extreme, this compact candidate-placement pattern is preferred:

```python
import numpy as np


def annotate_extreme(
    ax, x, y, text, *, data_x, data_y, kind="maximum",
    color="#d62728", legend=None,
):
    ax.scatter([x], [y], s=28, color=color, zorder=5)

    # Reserve a narrow, data-free band for a short two-line label.
    ymin, ymax = ax.get_ylim()
    span = ymax - ymin
    if kind == "maximum":
        ax.set_ylim(ymin, max(ymax, y + 0.18 * span))
    else:
        ax.set_ylim(min(ymin, y - 0.18 * span), ymax)

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    xfrac = (ax.convert_xunits(x) - xmin) / (xmax - xmin)
    yfrac = (y - ymin) / (ymax - ymin)

    horizontal = [(-10, "right"), (10, "left")] if xfrac > 0.5 else [
        (10, "left"), (-10, "right")
    ]
    # Outward from the data range first, inward only as a fallback.
    vertical = (
        [(5, "bottom"), (-10, "top")]
        if kind == "maximum"
        else [(-5, "top"), (10, "bottom")]
    )
    candidates = [
        (dx, dy, ha, va)
        for dy, va in vertical
        for dx, ha in horizontal
    ]
    candidates += [
        (2 * dx, 2 * dy, ha, va) for dx, dy, ha, va in candidates
    ]

    best = None
    point_pixels = ax.transData.transform(
        np.column_stack([
            ax.convert_xunits(data_x),
            np.asarray(data_y, dtype=float),
        ])
    )
    for rank, (dx, dy, ha, va) in enumerate(candidates):
        annotation = ax.annotate(
            text,
            xy=(x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            color=color,
            fontsize=8,
            arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8},
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85},
            zorder=6,
        )
        ax.figure.canvas.draw()
        renderer = ax.figure.canvas.get_renderer()
        label_box = annotation.get_window_extent(renderer)
        axes_box = ax.get_window_extent(renderer)
        legend_box = legend.get_window_extent(renderer) if legend is not None else None
        inside = (
            label_box.x0 >= axes_box.x0
            and label_box.x1 <= axes_box.x1
            and label_box.y0 >= axes_box.y0
            and label_box.y1 <= axes_box.y1
        )
        legend_overlap = legend_box is not None and label_box.overlaps(legend_box)
        covered = np.count_nonzero(
            (point_pixels[:, 0] >= label_box.x0)
            & (point_pixels[:, 0] <= label_box.x1)
            & (point_pixels[:, 1] >= label_box.y0)
            & (point_pixels[:, 1] <= label_box.y1)
        )
        score = (
            (0 if inside else 100_000)
            + (10_000 if legend_overlap else 0)
            + 100 * covered
            + rank
        )
        if best is None or score < best[0]:
            if best is not None:
                best[1].remove()
            best = (score, annotation)
        else:
            annotation.remove()
    return best[1]
```

Call the helper only after the axes limits and legend are established. Keep the
annotation inside the data axes; do not use the title margin as overflow space.
Pass all plotted `data_x` and `data_y` values so the helper can avoid hiding
observations. A label that technically fits but covers many marks is not valid.
For many labels, do not annotate every point. Select only scientifically
meaningful events or use a dedicated label-placement library with deterministic
settings.

## Common mistakes

- Mixing UTC and local time on the same figure.
- Not stating precipitation accumulation windows.
- Overusing dual y-axes.
- Hiding missing data by interpolation.
- Reporting correlation without bias/error context.
- Giving an extreme label a fixed upward offset without checking the top edge.
- Letting an annotation overlap the title, legend, or dense data cluster.
- Accepting the first in-bounds annotation without measuring covered data marks.
