import os
import logging
from .base import BaseDisplay

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
        self._count += 1
        path = os.path.join(self._outdir, f"eink-{self._count:04d}.png")
        with open(path, "wb") as f:
            f.write(png_bytes)
        log.info("Simulator wrote %s (%d bytes)", path, len(png_bytes))
        self.last_quantized_bytes = png_bytes

    def clear(self):
        log.info("Simulator clear (no-op)")