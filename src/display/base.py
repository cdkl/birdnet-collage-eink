import abc
import io
from PIL import Image


def _fit_to_display(img, target_w, target_h):
    if img.size == (target_w, target_h):
        return img

    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size

    if w > target_w or h > target_h:
        left = (w - target_w) // 2 if w > target_w else 0
        top = (h - target_h) // 2 if h > target_h else 0
        right = left + target_w if w > target_w else w
        bottom = top + target_h if h > target_h else h
        img = img.crop((left, top, right, bottom))

    if img.size != (target_w, target_h):
        canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
        x = (target_w - img.width) // 2
        y = (target_h - img.height) // 2
        canvas.paste(img, (x, y))
        img = canvas

    return img


class BaseDisplay(abc.ABC):
    def __init__(self):
        self.last_quantized_bytes = None

    @property
    @abc.abstractmethod
    def resolution(self):
        pass

    @abc.abstractmethod
    def show(self, png_bytes):
        pass

    @abc.abstractmethod
    def clear(self):
        pass