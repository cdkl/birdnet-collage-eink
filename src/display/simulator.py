import io
import os
import logging
from PIL import Image
from .base import BaseDisplay, _fit_to_display

log = logging.getLogger(__name__)


class Simulator(BaseDisplay):
    def __init__(self, outdir="/tmp/eink-sim", saturation=None):
        super().__init__()
        self._outdir = outdir
        os.makedirs(outdir, exist_ok=True)
        self._count = 0

    @property
    def resolution(self):
        return (1600, 1200)

    def show(self, png_bytes):
        w, h = self.resolution
        img = Image.open(io.BytesIO(png_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = _fit_to_display(img, w, h)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        fitted = buf.getvalue()

        self._count += 1
        path = os.path.join(self._outdir, f"eink-{self._count:04d}.png")
        with open(path, "wb") as f:
            f.write(fitted)
        log.info("Simulator wrote %s (%d bytes)", path, len(fitted))
        self.last_quantized_bytes = fitted

    def clear(self):
        log.info("Simulator clear (no-op)")