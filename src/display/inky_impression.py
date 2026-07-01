import io
import logging
from PIL import Image
from .base import BaseDisplay

log = logging.getLogger(__name__)


class InkyImpression(BaseDisplay):
    def __init__(self, rotation=0):
        from inky.auto import auto
        self._inky = auto()
        self._inky.rotation = rotation
        log.info("Inky Impression initialised: %s (rotation=%s)", self._inky.resolution, rotation)

    @property
    def resolution(self):
        return self._inky.resolution

    def show(self, png_bytes):
        img = Image.open(io.BytesIO(png_bytes))
        if img.mode not in ("P", "PA"):
            img = img.convert("P", palette=Image.ADAPTIVE, colors=7)
        self._inky.set_image(img)
        self._inky.set_border(self._inky.WHITE)
        self._inky.show()
        log.info("Inky Impression updated (%s)", self._inky.resolution)

    def clear(self):
        w, h = self.resolution
        blank = Image.new("P", (w, h), 0)
        self._inky.set_image(blank)
        self._inky.set_border(self._inky.WHITE)
        self._inky.show()
        log.info("Inky Impression cleared")