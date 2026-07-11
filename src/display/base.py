import abc
import datetime
import io
import logging
import os
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

_BUNDLED_FONT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "DejaVuSans.ttf",
)
_FONT_CACHE = {}


def _get_overlay_font(size=20):
    key = (size,)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    font = None
    if os.path.isfile(_BUNDLED_FONT):
        try:
            font = ImageFont.truetype(_BUNDLED_FONT, size)
        except (OSError, IOError):
            pass
    if font is None:
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def overlay_timestamp(png_bytes):
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    draw = ImageDraw.Draw(img)
    font = _get_overlay_font(20)

    text = datetime.datetime.now().strftime("%-d %b %H:%M")

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    margin = 16
    pad = 6
    pill_w = tw + pad * 2
    pill_h = th + pad * 2
    pill_x = img.width - pill_w - margin
    pill_y = img.height - pill_h - margin

    draw.rounded_rectangle(
        [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
        radius=4,
        fill=(255, 255, 255),
    )
    draw.text((pill_x + pad, pill_y + pad), text, fill=(0, 0, 0), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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