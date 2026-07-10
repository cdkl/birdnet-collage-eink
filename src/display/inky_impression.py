import io
import logging
from PIL import Image
from .base import BaseDisplay, _fit_to_display

log = logging.getLogger(__name__)

_SATURATED = [
    [57, 48, 57],
    [255, 255, 255],
    [58, 91, 70],
    [61, 59, 94],
    [156, 72, 75],
    [208, 190, 71],
    [177, 106, 73],
]

_DESATURATED = [
    [0, 0, 0],
    [255, 255, 255],
    [0, 255, 0],
    [0, 0, 255],
    [255, 0, 0],
    [255, 255, 0],
    [255, 140, 0],
]


def _blend_palette(saturation):
    palette = []
    for i in range(7):
        rs, gs, bs = [c * saturation for c in _SATURATED[i]]
        rd, gd, bd = [c * (1.0 - saturation) for c in _DESATURATED[i]]
        palette += [int(rs + rd), int(gs + gd), int(bs + bd)]
    palette += [255, 255, 255]
    return palette


class InkyImpression(BaseDisplay):
    def __init__(self, rotation=0, saturation=0.5):
        super().__init__()
        from inky.auto import auto
        self._inky = auto()
        self._inky.rotation = rotation
        self._saturation = saturation
        log.info(
            "Inky Impression initialised: %s (rotation=%s, saturation=%s)",
            self._inky.resolution, rotation, saturation,
        )

    @property
    def resolution(self):
        return self._inky.resolution

    @property
    def saturation(self):
        return self._saturation

    @saturation.setter
    def saturation(self, value):
        self._saturation = value

    def show(self, png_bytes):
        w, h = self.resolution
        img = Image.open(io.BytesIO(png_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = _fit_to_display(img, w, h)
        palette = _blend_palette(self.saturation)
        pal_img = Image.new("P", (1, 1))
        pal_img.putpalette(palette + [0, 0, 0] * 248)
        img = img.quantize(palette=pal_img, dither=Image.Dither.NONE)
        self._inky.set_image(img)
        self._inky.set_border(self._inky.WHITE)
        self._inky.show()
        log.info("Inky Impression updated (%s)", self._inky.resolution)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.last_quantized_bytes = buf.getvalue()

    def clear(self):
        w, h = self.resolution
        blank = Image.new("P", (w, h), 0)
        self._inky.set_image(blank)
        self._inky.set_border(self._inky.WHITE)
        self._inky.show()
        log.info("Inky Impression cleared")
