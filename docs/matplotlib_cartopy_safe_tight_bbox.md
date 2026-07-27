# Matplotlib / Cartopy 安全实现 `bbox_inches="tight"` 的方法

## 1. 问题背景

在使用 Matplotlib 与 Cartopy 绘制地图时，常见的保存方式是：

```python
fig.savefig(
    "output.png",
    dpi=300,
    bbox_inches="tight",
)
```

`bbox_inches="tight"` 可以自动裁掉画布四周的空白，但在部分 Matplotlib / Cartopy 版本组合或复杂地图图层下，可能出现异常裁剪，例如：

- 地图主体被完全裁掉；
- `contourf` 图层消失；
- 最终图片只剩下 colorbar；
- 经纬度标签、标题或图例被错误裁切；
- 输出尺寸异常小。

这通常不是 `contourf` 本身的问题，而是 Cartopy 的 `GeoAxes` 在计算 tight bounding box 时出现异常。

`bbox_inches="tight"` 会在保存阶段重新遍历图中的 Artist，并计算一个包含全部对象的边界。Cartopy 的地图轴涉及投影变换、地图边界、Gridliner、Feature 等复杂对象，某些情况下 `GeoAxes.get_tightbbox()` 可能返回错误、过小或不完整的范围。

---

## 2. 核心解决思路

不要让 `savefig` 在保存阶段重新自动猜测地图边界，而是采用以下流程：

1. 先让 Figure 完整渲染；
2. 获取渲染完成后的真实边界；
3. 手动合并地图轴、colorbar、标题、图例和经纬度标签；
4. 将计算好的固定 `Bbox` 传给 `savefig`。

关键区别：

```python
bbox_inches="tight"
```

是让 Matplotlib 自动计算边界，而：

```python
bbox_inches=calculated_bbox
```

是使用已经计算好的固定边界。

后者更加稳定和可控。

---

# 3. 推荐方案一：手动计算安全裁剪范围

## 3.1 完整实现

```python
from matplotlib.transforms import Bbox


def savefig_cartopy_tight(
    fig,
    filename,
    *,
    axes=None,
    extra_artists=None,
    dpi=300,
    pad_inches=0.05,
    **savefig_kwargs,
):
    """稳定保存 Cartopy 图件，避免 tight bbox 错误裁剪 GeoAxes。"""

    # Cartopy 的投影路径、地图边界和标签通常需要真正渲染后
    # 才能得到稳定的像素边界。
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    if axes is None:
        axes = fig.axes

    boxes = []

    for ax in axes:
        if not ax.get_visible():
            continue

        # 使用渲染后的轴窗口范围。
        # 对 Cartopy GeoAxes 来说，这通常比 get_tightbbox 更稳定。
        box = ax.get_window_extent(renderer)

        if box is not None and box.width > 0 and box.height > 0:
            boxes.append(box)

    if extra_artists:
        for artist in extra_artists:
            if artist is None or not artist.get_visible():
                continue

            box = artist.get_window_extent(renderer)

            if box is not None and box.width > 0 and box.height > 0:
                boxes.append(box)

    if not boxes:
        raise RuntimeError("没有找到有效的绘图边界")

    # 合并所有边界。当前单位为显示像素。
    bbox_pixels = Bbox.union(boxes)

    # savefig 的 bbox_inches 需要 Figure 英寸坐标。
    bbox_inches = bbox_pixels.transformed(
        fig.dpi_scale_trans.inverted()
    )

    # 增加固定留白。
    bbox_inches = Bbox.from_extents(
        bbox_inches.x0 - pad_inches,
        bbox_inches.y0 - pad_inches,
        bbox_inches.x1 + pad_inches,
        bbox_inches.y1 + pad_inches,
    )

    fig.savefig(
        filename,
        dpi=dpi,
        bbox_inches=bbox_inches,
        **savefig_kwargs,
    )
```

## 3.2 使用示例

```python
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

projection = ccrs.PlateCarree()

fig, ax = plt.subplots(
    figsize=(12, 8),
    subplot_kw={"projection": projection},
)

cf = ax.contourf(
    lon,
    lat,
    data,
    levels=20,
    transform=ccrs.PlateCarree(),
)

ax.coastlines()

cbar = fig.colorbar(
    cf,
    ax=ax,
    orientation="horizontal",
    pad=0.05,
)

title = ax.set_title("Temperature")

savefig_cartopy_tight(
    fig,
    "temperature.png",
    axes=[ax, cbar.ax],
    extra_artists=[title],
    dpi=300,
    pad_inches=0.03,
    facecolor="white",
)
```

---

# 4. 更完善的边界策略

单纯使用：

```python
ax.get_window_extent(renderer)
```

虽然稳定，但它只包含 Axes 本身的矩形区域，不一定包括伸出轴区域的对象，例如：

- 标题；
- 经纬度标签；
- 图例；
- 注释；
- colorbar 标签；
- Gridliner 标签。

更合理的策略是：

- Cartopy 地图轴使用 `get_window_extent()`；
- 普通 Matplotlib Axes 使用 `get_tightbbox()`；
- 标题、图例和 Gridliner 标签显式加入。

```python
from cartopy.mpl.geoaxes import GeoAxes
from matplotlib.transforms import Bbox


def get_safe_axes_bbox(ax, renderer):
    if isinstance(ax, GeoAxes):
        bbox = ax.get_window_extent(renderer)

        title = ax.title
        if title.get_visible() and title.get_text():
            title_bbox = title.get_window_extent(renderer)
            bbox = Bbox.union([bbox, title_bbox])

        return bbox

    return ax.get_tightbbox(renderer)
```

然后将保存函数中的：

```python
box = ax.get_window_extent(renderer)
```

替换成：

```python
box = get_safe_axes_bbox(ax, renderer)
```

这样可以让：

- 地图区域避免触发 Cartopy 的异常 tight bbox；
- colorbar 等普通 Axes 仍然获得紧凑边界；
- 标题不会被遗漏。

---

# 5. Gridliner 经纬度标签的处理

当使用：

```python
gl = ax.gridlines(
    draw_labels=True,
    x_inline=False,
    y_inline=False,
)
```

经纬度标签通常会伸出地图轴，因此必须显式纳入裁剪区域。

```python
fig.canvas.draw()

gridliner_artists = [
    *gl.xlabel_artists,
    *gl.ylabel_artists,
]

savefig_cartopy_tight(
    fig,
    "map.png",
    axes=[ax, cbar.ax],
    extra_artists=[
        ax.title,
        *gridliner_artists,
    ],
    dpi=300,
)
```

为兼容不同 Cartopy 版本，可以写得更稳妥：

```python
extra_artists = [ax.title]

if hasattr(gl, "xlabel_artists"):
    extra_artists.extend(gl.xlabel_artists)

if hasattr(gl, "ylabel_artists"):
    extra_artists.extend(gl.ylabel_artists)
```

---

# 6. 推荐方案二：栅格图片保存后按像素裁剪

如果最终输出格式是 PNG、WebP 或 JPEG，而不要求保留 PDF / SVG 的矢量特性，那么最可靠的方法是：

```text
正常保存完整画布
        ↓
读取最终图片
        ↓
按真实像素内容裁掉空白
```

这种方式完全绕过 Matplotlib 和 Cartopy 的 Artist 边界计算，因此不会发生地图被裁掉、只剩 colorbar 的问题。

## 6.1 基于白色背景裁剪

```python
from io import BytesIO
from PIL import Image, ImageChops


def savefig_autocrop_png(
    fig,
    filename,
    *,
    dpi=300,
    padding=10,
    background=(255, 255, 255),
    **savefig_kwargs,
):
    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=dpi,
        facecolor="white",
        **savefig_kwargs,
    )

    buffer.seek(0)
    image = Image.open(buffer).convert("RGB")

    background_image = Image.new(
        "RGB",
        image.size,
        background,
    )

    diff = ImageChops.difference(
        image,
        background_image,
    )

    bbox = diff.getbbox()

    if bbox is None:
        image.save(filename)
        return

    left, top, right, bottom = bbox

    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)

    cropped = image.crop((left, top, right, bottom))
    cropped.save(filename)
```

使用：

```python
savefig_autocrop_png(
    fig,
    "map.png",
    dpi=300,
    padding=15,
)
```

## 6.2 基于透明通道裁剪

透明通道裁剪通常比识别白色背景更可靠。

```python
from io import BytesIO
from PIL import Image


def savefig_autocrop_transparent(
    fig,
    filename,
    *,
    dpi=300,
    padding=10,
    background="white",
):
    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=dpi,
        transparent=True,
    )

    buffer.seek(0)
    image = Image.open(buffer).convert("RGBA")

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()

    if bbox is None:
        image.save(filename)
        return

    left, top, right, bottom = bbox

    bbox = (
        max(0, left - padding),
        max(0, top - padding),
        min(image.width, right + padding),
        min(image.height, bottom + padding),
    )

    cropped = image.crop(bbox)

    if background is not None:
        output = Image.new(
            "RGBA",
            cropped.size,
            background,
        )
        output.alpha_composite(cropped)
        output = output.convert("RGB")
    else:
        output = cropped

    output.save(filename)
```

使用：

```python
savefig_autocrop_transparent(
    fig,
    "map.png",
    dpi=300,
    padding=15,
    background="white",
)
```

如果希望保留透明背景：

```python
savefig_autocrop_transparent(
    fig,
    "map.png",
    dpi=300,
    padding=15,
    background=None,
)
```

---

# 7. PNG 与 WebP 的输出

如果最终需要 WebP，可以在裁剪后直接保存为 WebP。

```python
cropped.save(
    "map.webp",
    format="WEBP",
    quality=90,
    method=6,
)
```

无损 WebP：

```python
cropped.save(
    "map.webp",
    format="WEBP",
    lossless=True,
    method=6,
)
```

对于气象填色图、等值线图、雷达图和彩色分级图：

- 色块边界清晰、文字较多时，可优先使用 PNG 或无损 WebP；
- 图片尺寸较大且允许轻微损失时，可以使用有损 WebP；
- 需要重点检查 colorbar 刻度和小字号文字是否模糊。

---

# 8. `constrained_layout` 的作用

可以同时使用：

```python
fig, ax = plt.subplots(
    figsize=(12, 8),
    subplot_kw={"projection": projection},
    layout="constrained",
)
```

`constrained_layout` 可以改善：

- 地图轴与 colorbar 的间距；
- 标题与轴的间距；
- 多子图之间的布局；
- colorbar 占用空间的分配。

但它解决的是 Figure 内部布局，不负责自动裁掉 Figure 外部白边。

推荐组合：

```text
constrained_layout + 手动 Bbox 裁剪
```

或者：

```text
constrained_layout + 保存后像素裁剪
```

不建议叠加多套自动逻辑：

```python
plt.tight_layout()
fig.set_constrained_layout(True)
bbox_inches="tight"
```

---

# 9. 推荐的实际使用策略

## 9.1 输出 PNG / WebP

推荐：

```text
正常渲染
    ↓
正常保存，不使用 bbox_inches="tight"
    ↓
使用 Pillow 根据 alpha 通道裁剪
```

优点：

- 稳定性最高；
- 不受 Cartopy 投影类型影响；
- 不受 `GeoAxes.get_tightbbox()` 影响；
- 不需要反复调整 `figsize`；
- 地图、标题、colorbar、Gridliner 都按最终像素统一处理。

## 9.2 输出 PDF / SVG

推荐：

```text
fig.canvas.draw()
    ↓
地图轴使用 get_window_extent()
    ↓
普通轴使用 get_tightbbox()
    ↓
显式加入标题、图例和 Gridliner
    ↓
合并成固定 Bbox
    ↓
传给 savefig
```

PDF 和 SVG 需要保留矢量信息，不适合用 Pillow 二次裁剪。

---

# 10. 最精简的可复用版本

如果项目主要生成 PNG，可以直接保留下面这个函数：

```python
from io import BytesIO
from PIL import Image


def save_cartopy_png(
    fig,
    filename,
    *,
    dpi=300,
    padding=10,
    background="white",
):
    """稳定保存 Cartopy PNG，并自动裁掉空白。"""

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=dpi,
        transparent=True,
    )

    buffer.seek(0)
    image = Image.open(buffer).convert("RGBA")

    bbox = image.getchannel("A").getbbox()

    if bbox is not None:
        left, top, right, bottom = bbox

        bbox = (
            max(0, left - padding),
            max(0, top - padding),
            min(image.width, right + padding),
            min(image.height, bottom + padding),
        )

        image = image.crop(bbox)

    if background is not None:
        output = Image.new(
            "RGBA",
            image.size,
            background,
        )
        output.alpha_composite(image)
        image = output.convert("RGB")

    image.save(filename)
```

使用：

```python
fig.canvas.draw()

save_cartopy_png(
    fig,
    "result.png",
    dpi=300,
    padding=12,
)
```

---

# 11. 最终结论

对于 Matplotlib / Cartopy 地图，不建议把：

```python
bbox_inches="tight"
```

作为无条件使用的默认方案。

更可靠的选择是：

## 栅格图

```text
保存完整画布 + Pillow 按 alpha 通道裁剪
```

## 矢量图

```text
渲染后手动计算并合并 Bbox
```

这两种方法都能实现接近 `bbox_inches="tight"` 的效果，同时避免 Cartopy 地图主体被错误裁掉、最终只剩 colorbar 的问题。
