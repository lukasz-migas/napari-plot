"""Override text visual to fix label cropping"""

from napari._vispy.overlays.text import VispyTextOverlay as _VispyTextOverlay


class VispyTextOverlay(_VispyTextOverlay):
    """Overwrite text position"""

    def __init__(self, *, viewer, overlay, font_info, parent=None) -> None:
        self._box_padding: tuple[int, int] | None = None
        super().__init__(viewer=viewer, overlay=overlay, font_info=font_info, parent=parent)

    @property
    def box_padding(self) -> tuple[int, int] | None:
        """Horizontal and vertical padding per side, or None for the canvas default."""
        return self._box_padding

    @box_padding.setter
    def box_padding(self, padding: tuple[int, int] | None) -> None:
        if padding != self._box_padding:
            self._box_padding = padding
            self._on_position_change()

    def _on_box_change(self) -> None:
        super()._on_box_change()
        if self._box_padding is not None and self.box.parent is not None:
            horizontal, vertical = self._box_padding
            width, height = self.x_size + 2 * horizontal, self.y_size + 2 * vertical
            if width <= 0 or height <= 0:
                self.box.parent = None
                return
            self.box.width, self.box.height = width, height

    def _on_position_change(self, event=None):
        """Change position of text visual.

        This is necessary to account for the offsets caused by the x/y-axis offsets.
        """
        super()._on_position_change(event)
        if not self.node.canvas:
            return
        self.y_size = max(self.y_size, self._rendered_height())

        position = self.overlay.position
        x_offset, y_offset = 10, 5
        if self._box_padding is not None:
            horizontal, vertical = self._box_padding
            x_offset, y_offset = max(x_offset, horizontal), max(y_offset, vertical)
        # the parent is the plot view box, which excludes the axes and padding and clips its children
        canvas_size = list(self.node.parent.size)

        if "left" in position:
            x = x_offset
        elif "right" in position:
            x = canvas_size[0] - self.x_size - x_offset
        else:
            x = (canvas_size[0] - self.x_size) / 2
        if "top" in position:
            y = y_offset
        elif "bottom" in position:
            y = canvas_size[1] - self.y_size - y_offset
        else:
            y = (canvas_size[1] - self.y_size) / 2
        self.node.transform.translate = [max(0, x), max(0, y), 0, 0]
        self._on_box_change()

    def _rendered_height(self) -> float:
        """Height of the text as vispy lays it out, in screen pixels.

        napari measures text with Qt font metrics, but vispy spaces lines by ``line_height`` times the height of the
        font's tallest glyphs (accented capitals and descenders), so multi-line text is taller than measured and
        overflows its box. This repeats vispy's vertical layout (``vispy.visuals.text.text._text_to_vbo``).
        """
        font = getattr(self.node, "_font", None)
        if font is None:
            return 0.0
        text = self.node.text
        n_lines = (text if isinstance(text, str) else "\n".join(text)).count("\n") + 1
        ascender = descender = 0.0
        for char in "ÅÉÑŐjgpqy":
            glyph = font[char]
            top = glyph["offset"][1] / font.ratio
            ascender = max(ascender, top)
            descender = min(descender, top - glyph["size"][1] + 2 * font.slop)
        glyph_height = ascender - descender
        height = (n_lines - 1) * glyph_height * self.node.line_height + glyph_height
        # glyph units are stored at the font's low-res size; vispy draws them at font_size points (96 dpi reference)
        return height / font._lowres_size * self.node.font_size * self.node._vispy_dpi_ratio
