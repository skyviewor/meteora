"""Plot an ERA5 meridional pressure cross-section with terrain and wind barbs.

The barbs show horizontal (u, v) wind at each latitude-pressure sample. They do
not represent in-plane vertical circulation because this example has no omega.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import xarray as xr

matplotlib.use("Agg")
import matplotlib.pyplot as plt

GRAVITY = 9.80665


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pressure-file", type=Path, required=True)
    parser.add_argument("--surface-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--longitude", type=float, default=90.0)
    parser.add_argument("--time-index", type=int, default=0)
    parser.add_argument("--title-time", default="")
    return parser.parse_args()


def select_section(dataset: xr.Dataset, longitude: float, time_index: int) -> xr.Dataset:
    section = dataset.sel(longitude=longitude, method="nearest")
    if "valid_time" in section.dims:
        section = section.isel(valid_time=time_index)
    return section


def interpolate_terrain_pressure(
    level_height_m: np.ndarray,
    pressure_hpa: np.ndarray,
    terrain_height_m: np.ndarray,
) -> np.ndarray:
    """Interpolate log-pressure by height without assuming level order."""
    terrain_pressure = np.full(terrain_height_m.shape, np.nan, dtype=float)
    for column in range(terrain_height_m.size):
        heights = np.asarray(level_height_m[:, column], dtype=float)
        pressures = np.asarray(pressure_hpa, dtype=float)
        valid = np.isfinite(heights) & np.isfinite(pressures) & (pressures > 0)
        heights = heights[valid]
        log_pressures = np.log(pressures[valid])
        if heights.size < 2 or not np.isfinite(terrain_height_m[column]):
            continue

        order = np.argsort(heights)
        heights = heights[order]
        log_pressures = log_pressures[order]
        target = float(terrain_height_m[column])

        if target < heights[0]:
            pair = slice(0, 2)
        elif target > heights[-1]:
            pair = slice(-2, None)
        else:
            terrain_pressure[column] = np.exp(np.interp(target, heights, log_pressures))
            continue

        slope = (log_pressures[pair][1] - log_pressures[pair][0]) / (
            heights[pair][1] - heights[pair][0]
        )
        terrain_pressure[column] = np.exp(
            log_pressures[pair][0] + slope * (target - heights[pair][0])
        )
    return terrain_pressure


def main() -> None:
    args = parse_args()
    pressure = xr.open_dataset(args.pressure_file)
    surface = xr.open_dataset(args.surface_file)

    pressure_section = select_section(pressure, args.longitude, args.time_index)
    surface_section = select_section(surface, args.longitude, args.time_index)
    surface_section = surface_section.interp(latitude=pressure_section.latitude)

    levels = pressure_section.pressure_level.values.astype(float)
    latitudes = pressure_section.latitude.values.astype(float)
    u_wind = pressure_section["u"].values.astype(float)
    v_wind = pressure_section["v"].values.astype(float)
    level_height = pressure_section["z"].values.astype(float) / GRAVITY
    terrain_height = surface_section["z"].values.astype(float) / GRAVITY

    terrain_pressure = interpolate_terrain_pressure(level_height, levels, terrain_height)
    plot_bottom = max(1050.0, float(np.nanmax(levels)) + 25.0)
    plot_top = float(np.nanmin(levels))
    terrain_pressure = np.clip(terrain_pressure, plot_top, plot_bottom)

    underground = level_height < terrain_height[np.newaxis, :]
    speed = np.ma.array(np.hypot(u_wind, v_wind), mask=underground)
    u_masked = np.ma.array(u_wind, mask=underground)
    v_masked = np.ma.array(v_wind, mask=underground)

    fig, ax = plt.subplots(figsize=(8.2, 5.2), layout="constrained")
    finite_speed = speed.compressed()
    color_max = max(10.0, float(np.ceil(np.nanpercentile(finite_speed, 98) / 2) * 2))
    color_levels = np.linspace(0.0, color_max, 13)
    filled = ax.contourf(
        latitudes,
        levels,
        speed,
        levels=color_levels,
        cmap="YlGnBu",
        extend="max",
    )

    latitude_stride = max(1, len(latitudes) // 18)
    level_stride = max(1, len(levels) // 8)
    latitude_grid, pressure_grid = np.meshgrid(latitudes, levels)
    ax.barbs(
        latitude_grid[::level_stride, ::latitude_stride],
        pressure_grid[::level_stride, ::latitude_stride],
        u_masked[::level_stride, ::latitude_stride],
        v_masked[::level_stride, ::latitude_stride],
        length=5,
        linewidth=0.55,
        color="#202020",
        barb_increments={"half": 2, "full": 4, "flag": 20},
        zorder=4,
    )

    ax.fill_between(
        latitudes,
        terrain_pressure,
        plot_bottom,
        color="black",
        alpha=0.92,
        label="ERA5 surface geopotential terrain",
        zorder=5,
    )
    ax.plot(latitudes, terrain_pressure, color="black", linewidth=0.8, zorder=6)

    ax.set_ylim(plot_bottom, plot_top)
    assert ax.get_ylim()[0] > ax.get_ylim()[1]
    ax.set_xlim(float(np.nanmin(latitudes)), float(np.nanmax(latitudes)))
    ax.set_xlabel("Latitude (°N)")
    ax.set_ylabel("Pressure (hPa)")
    actual_longitude = float(pressure_section.longitude.values)
    title = f"ERA5 meridional pressure cross-section along {actual_longitude:.2f}°E"
    if args.title_time:
        title += f"\n{args.title_time}"
    ax.set_title(title)
    ax.grid(linestyle="--", linewidth=0.4, alpha=0.35)
    ax.legend(loc="upper right", fontsize=8)

    colorbar = fig.colorbar(filled, ax=ax, pad=0.02)
    colorbar.set_label("Horizontal wind speed (m s$^{-1}$)")
    ax.text(
        0.01,
        0.015,
        "Barbs: horizontal wind components (u, v); not vertical circulation",
        transform=ax.transAxes,
        fontsize=7.5,
        color="white",
        bbox={"facecolor": "black", "alpha": 0.65, "pad": 2, "edgecolor": "none"},
        zorder=7,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=120, facecolor="white")
    plt.close(fig)

    masked_fraction = underground.mean(axis=0)
    print(f"section_longitude={actual_longitude:.2f}")
    print(
        f"terrain_pressure_hpa={np.nanmin(terrain_pressure):.1f}..{np.nanmax(terrain_pressure):.1f}"
    )
    print(
        f"underground_fraction={np.nanmin(masked_fraction):.2f}..{np.nanmax(masked_fraction):.2f}"
    )
    print(f"saved={args.output} bytes={args.output.stat().st_size}")


if __name__ == "__main__":
    main()
