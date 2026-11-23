"""Paint VisPy plot geometry to Qt's vector output devices."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

import numpy as np
from qtpy.QtCore import QMarginsF, QPointF, QRect, QRectF, QSize, QSizeF, Qt
from qtpy.QtGui import QColor, QFont, QImage, QPageSize, QPainter, QPainterPath, QPdfWriter, QPen, QPolygonF, QTransform
from qtpy.QtSvg import QSvgGenerator
from vispy.color import ColorArray
from vispy.scene.widgets import Grid
from vispy.visuals import AxisVisual, CompoundVisual, ImageVisual, LineVisual, MarkersVisual, MeshVisual, TextVisual

from napari_plot._vispy.overlays.grid_lines import _GridLines
from napari_plot._vispy.visuals.infline import _BatchedInfiniteLineVisual
from napari_plot._vispy.visuals.region import _BatchedLinearRegionVisual
from napari_plot.layers import Line, Rectangles

if TYPE_CHECKING:
    from vispy.scene import Node
    from vispy.visuals.transforms import BaseTransform

    from napari_plot._vispy.canvas import VispyCanvas


def _color(value: object) -> QColor:
    rgba = np.asarray(getattr(value, "rgba", value), dtype=float).reshape(-1, 4)[0]
    return QColor.fromRgbF(*np.clip(rgba, 0, 1))


def _stroke(
    painter: QPainter,
    data: np.ndarray,
    color: object,
    width: float,
    *,
    closed: bool = False,
    dashes: tuple[float, ...] | None = None,
) -> None:
    if not len(data) or not np.isfinite(data).all() or width <= 0:
        return
    pen = QPen(_color(color))
    pen.setWidthF(width)
    if dashes is not None:
        pen.setDashPattern(dashes)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    polygon = QPolygonF([QPointF(*point) for point in data])
    if closed:
        painter.drawPolygon(polygon)
    else:
        painter.drawPolyline(polygon)


def _line(painter: QPainter, visual: LineVisual, transform: BaseTransform, dashes: tuple[float, ...] | None) -> None:
    if visual.pos is None or len(visual.pos) < 2 or visual.width <= 0:
        return
    points = transform.map(visual.pos)[:, :2]
    colors = ColorArray(visual.color).rgba
    connect = visual._interpret_connect()
    if isinstance(connect, str) and connect == "strip" and len(colors) == 1:
        valid = np.isfinite(points).all(axis=1)
        edges = np.flatnonzero(np.diff(np.r_[False, valid, False]))
        for start, stop in edges.reshape(-1, 2):
            _stroke(painter, points[start:stop], colors[0], visual.width, dashes=dashes)
        return
    if isinstance(connect, str):
        step = 2 if connect == "segments" else 1
        left = np.arange(0, len(points) - 1, step)
        connect = np.column_stack((left, left + 1))
    for start, stop in connect:
        _stroke(
            painter, points[[start, stop]], colors[start] if len(colors) > 1 else colors[0], visual.width, dashes=dashes
        )


def _mesh(painter: QPainter, visual: MeshVisual, transform: BaseTransform) -> None:
    mesh = visual.mesh_data
    vertices = mesh.get_vertices(indexed="faces")
    if vertices is None or not len(vertices):
        return
    points = transform.map(vertices.reshape(-1, vertices.shape[-1]))[:, :2].reshape(-1, 3, 2)
    if mesh.has_face_color():
        colors = mesh.get_face_colors()
    elif mesh.has_vertex_color():
        colors = mesh.get_vertex_colors(indexed="faces").mean(axis=1)
    else:
        colors = np.tile(visual.color.rgba, (len(points), 1))
    paths = {}
    for triangle, rgba in zip(points, colors, strict=True):
        if np.isfinite(triangle).all():
            key = tuple(rgba)
            path = paths.get(key)
            if path is None:
                path = paths[key] = QPainterPath()
                path.setFillRule(Qt.FillRule.WindingFill)
            path.addPolygon(QPolygonF([QPointF(*point) for point in triangle]))
            path.closeSubpath()
    for rgba, path in paths.items():
        painter.fillPath(path, _color(rgba))


def _markers(painter: QPainter, visual: MarkersVisual, transform: BaseTransform) -> None:
    data = visual._data
    if data is None or not len(data):
        return
    positions = transform.map(data["a_position"])[:, :2]
    sizes = data["a_size"]
    widths = data["a_edgewidth"]
    if visual.scaling != "fixed":
        offsets = data["a_position"].copy()
        offsets[:, 0] += sizes
        scales = np.linalg.norm(transform.map(offsets)[:, :2] - positions, axis=1)
        widths = widths * np.divide(scales, sizes, where=sizes > 0, out=np.zeros_like(scales))
        sizes = scales
    minimum, maximum = visual.canvas_size_limits or (None, None)
    if minimum is not None or maximum is not None:
        sizes = np.clip(sizes, minimum, maximum)
    for point, row, size, width, symbol in zip(positions, data, sizes, widths, visual.symbol, strict=True):
        if size <= 0 or not np.isfinite((*point, size, width)).all():
            continue
        x, y = point
        radius = float(size) / 2
        pen = QPen(_color(row["a_fg_color"]))
        pen.setWidthF(float(width))
        painter.setPen(pen if pen.widthF() > 0 else Qt.PenStyle.NoPen)
        painter.setBrush(_color(row["a_bg_color"]))
        bounds = QRectF(x - radius, y - radius, 2 * radius, 2 * radius)
        if symbol == "square":
            painter.drawRect(bounds)
        elif symbol == "diamond":
            painter.drawPolygon(
                QPolygonF(
                    [QPointF(x - radius, y), QPointF(x, y - radius), QPointF(x + radius, y), QPointF(x, y + radius)]
                )
            )
        elif symbol in ("triangle_up", "triangle_down"):
            direction = 1 if symbol == "triangle_up" else -1
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(x, y - direction * radius),
                        QPointF(x + radius, y + direction * radius),
                        QPointF(x - radius, y + direction * radius),
                    ]
                )
            )
        else:
            painter.drawEllipse(bounds)


def _text(painter: QPainter, visual: TextVisual, transform: BaseTransform) -> None:
    if not len(visual.text) or visual.font_size <= 0:
        return
    text = [visual.text] if isinstance(visual.text, str) else visual.text
    positions = transform.map(visual.pos)[:, :2]
    rotations = np.atleast_1d(visual.rotation)
    colors = visual.color.rgba
    anchor_x, anchor_y = visual.anchors
    font = QFont(visual.face)
    font.setPixelSize(max(1, round(visual.font_size * 96 / 72)))
    font.setBold(visual.bold)
    font.setItalic(visual.italic)
    painter.setFont(font)
    metrics = painter.fontMetrics()
    for index, label in enumerate(text):
        point = positions[min(index, len(positions) - 1)]
        if not np.isfinite(point).all():
            continue
        painter.save()
        painter.translate(*point)
        painter.rotate(float(rotations[min(index, len(rotations) - 1)]))
        painter.setPen(_color(colors[min(index, len(colors) - 1)]))
        lines = label.split("\n")
        height = metrics.height() * len(lines)
        offset_y = {"top": 0, "middle": -height / 2, "bottom": -height}.get(anchor_y, 0) + metrics.ascent()
        for line in lines:
            width = metrics.horizontalAdvance(line)
            offset_x = {"left": 0, "center": -width / 2, "right": -width}.get(anchor_x, 0)
            painter.drawText(QPointF(offset_x, offset_y), line)
            offset_y += metrics.height()
        painter.restore()


def _image(painter: QPainter, visual: ImageVisual, transform: BaseTransform) -> None:
    data = visual._data
    if data is None or not data.size:
        return
    height, width = data.shape[:2]
    if data.ndim == 2:
        lower, upper = (np.nanmin(data), np.nanmax(data)) if visual.clim == "auto" else visual.clim
        values = np.clip((data.astype(float) - lower) / (upper - lower or 1), 0, 1)
        rgba = visual.cmap.map(np.nan_to_num(values).ravel() ** visual.gamma).reshape(height, width, 4)
        rgba[~np.isfinite(values), 3] = 0
    else:
        rgba = data.astype(float)
        if np.issubdtype(data.dtype, np.integer):
            rgba /= np.iinfo(data.dtype).max
        if rgba.shape[2] == 3:
            rgba = np.dstack((rgba, np.ones((height, width))))
    rgba = np.ascontiguousarray(np.rint(np.clip(rgba, 0, 1) * 255), dtype=np.uint8)
    image = QImage(rgba.data, width, height, rgba.strides[0], QImage.Format.Format_RGBA8888)
    origin, x, y = transform.map(np.array([[0, 0], [width, 0], [0, height]], dtype=float))[:, :2]
    if not np.isfinite((origin, x, y)).all():
        return
    xx, xy = (x - origin) / width
    yx, yy = (y - origin) / height
    painter.save()
    painter.setTransform(QTransform(xx, xy, yx, yy, *origin), combine=True)
    painter.drawImage(QPointF(), image)
    painter.restore()


def _infinite(
    painter: QPainter,
    visual: _BatchedInfiniteLineVisual | _BatchedLinearRegionVisual,
    transform: BaseTransform,
    clip: QRectF,
) -> None:
    # Keep the unrestricted coordinate within the visible area even on a log axis.
    sample = transform.imap([clip.center().x(), clip.center().y()])[:2]
    for values, orientation, rgba in zip(visual.pos, visual.orientation, visual.color, strict=True):
        dimension = int(orientation >= 0.5)
        points = np.tile(sample, (2, 1))
        points[:, dimension] = values
        bounds = sorted(transform.map(points)[:, dimension])
        if not np.isfinite(bounds).all():
            continue
        a, b = bounds
        if isinstance(visual, _BatchedLinearRegionVisual):
            rect = (
                QRectF(a, clip.top(), b - a, clip.height())
                if dimension == 0
                else QRectF(clip.left(), a, clip.width(), b - a)
            )
            painter.fillRect(rect, _color(rgba))
        else:
            pen = QPen(_color(rgba))
            pen.setWidthF(visual.line_width)
            if visual.dash_pattern and visual.line_width > 0:
                pen.setDashPattern([part / visual.line_width for part in visual.dash_pattern])
            painter.setPen(pen)
            if dimension == 0:
                painter.drawLine(QPointF(a, clip.top()), QPointF(a, clip.bottom()))
            else:
                painter.drawLine(QPointF(clip.left(), a), QPointF(clip.right(), a))


def _draw_visual(
    painter: QPainter,
    visual: object,
    transform: BaseTransform,
    clip: QRectF,
    dashes: tuple[float, ...] | None = None,
) -> None:
    if not visual.visible:
        return
    if isinstance(visual, LineVisual):
        if isinstance(visual, _GridLines) and visual._prepare_draw(visual) is False:
            return
        _line(painter, visual, transform, dashes)
    elif isinstance(visual, MeshVisual):
        _mesh(painter, visual, transform)
    elif isinstance(visual, MarkersVisual):
        _markers(painter, visual, transform)
    elif isinstance(visual, TextVisual):
        _text(painter, visual, transform)
    elif isinstance(visual, ImageVisual):
        _image(painter, visual, transform)
    elif isinstance(visual, (_BatchedInfiniteLineVisual, _BatchedLinearRegionVisual)):
        _infinite(painter, visual, transform, clip)
    elif isinstance(visual, CompoundVisual):
        if isinstance(visual, AxisVisual):
            if visual.pos is None:
                return
            # The geometry is computed on demand by VisPy just before drawing.
            visual._axis_label_vis.rotation = visual._rotation_angle
            visual._update_subvisuals()
        for child in visual._subvisuals:
            _draw_visual(painter, child, transform, clip)


def _draw_scene(painter: QPainter, canvas: VispyCanvas) -> None:
    target = canvas._scene_canvas.central_widget
    clips = {}
    for cell in canvas._cells:
        inner = cell.view.inner_rect
        position = cell.view.node_transform(target).map([inner.left, inner.bottom])[:2]
        clips[id(cell.data_scene)] = QRectF(*position, *inner.size)
    view_rect = QRectF(0, 0, *canvas._scene_canvas.size)
    layers = {id(visual.node): layer for layer, visual in canvas.layer_to_visual.items()}

    def draw(node: Node, clip: QRectF) -> None:
        if not node.visible:
            return
        painter.save()
        try:
            if id(node) in clips:
                clip = clips[id(node)]
                painter.setClipRect(clip)
            painter.setOpacity(painter.opacity() * getattr(node, "opacity", 1.0))
            transform = node.node_transform(target)
            layer = layers.get(id(node))
            if isinstance(layer, Rectangles) and layer.show_rectangles:
                colors = np.broadcast_to(layer.outline_color, (len(layer.data), 4))
                for (x, y, height, width), rgba in zip(layer.data, colors, strict=True):
                    hx, hy = width / 2, height / 2
                    points = np.array([(x - hx, y - hy), (x + hx, y - hy), (x + hx, y + hy), (x - hx, y + hy)])
                    _stroke(painter, transform.map(points)[:, :2], rgba, layer.outline_width, closed=True)
            _draw_visual(painter, node, transform, clip, layer.dashes if isinstance(layer, Line) else None)
            for child in sorted(node.children, key=lambda child: child.order):
                draw(child, clip)
        finally:
            painter.restore()

    painter.fillRect(view_rect, _color(canvas._scene_canvas.bgcolor))
    draw(target, view_rect)


def _layout_widgets(node: Node) -> None:
    """Resolve pending VisPy grid layouts without a framebuffer draw."""
    if not node.visible:
        return
    if isinstance(node, Grid):
        node._update_child_widget_dim()
    for child in node.children:
        _layout_widgets(child)


def export_vector(canvas: VispyCanvas, path: Path, dpi: int | None) -> None:
    """Write the current displayed plot geometries to an SVG or PDF file."""
    with NamedTemporaryFile(dir=path.parent, suffix=path.suffix, delete=False) as output:
        temporary_path = Path(output.name)
    scene_canvas = canvas._scene_canvas
    root = scene_canvas.central_widget
    old_root_size = root.size
    try:
        root.size = scene_canvas.size
        _layout_widgets(root)
        _paint_file(canvas, temporary_path, dpi or 96)
        temporary_path.replace(path)
    finally:
        if root.size != old_root_size:
            root.size = old_root_size
            _layout_widgets(root)
        with suppress(FileNotFoundError):
            temporary_path.unlink()


def _paint_file(canvas: VispyCanvas, path: Path, resolution: int) -> None:
    height, width = canvas.size
    if path.suffix.lower() == ".svg":
        version = getattr(QSvgGenerator, "SvgVersion", None)
        device = QSvgGenerator(version.Svg11) if version is not None else QSvgGenerator()
        device.setFileName(str(path))
        device.setSize(QSize(round(width * resolution / 96), round(height * resolution / 96)))
        device.setViewBox(QRect(0, 0, width, height))
        device.setResolution(resolution)
    else:
        device = QPdfWriter(str(path))
        device.setResolution(resolution)
        device.setPageSize(QPageSize(QSizeF(width * 25.4 / 96, height * 25.4 / 96), QPageSize.Unit.Millimeter))
        device.setPageMargins(QMarginsF(0, 0, 0, 0))

    painter = QPainter()
    if not painter.begin(device):
        raise OSError(f"Could not open {path} for vector export.")
    try:
        if path.suffix.lower() == ".pdf":
            painter.scale(resolution / 96, resolution / 96)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        _draw_scene(painter, canvas)
    finally:
        painter.end()
