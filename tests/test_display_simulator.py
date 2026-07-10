import pytest
import os
import io
from PIL import Image


def _read_image(path):
    with open(path, "rb") as f:
        return Image.open(io.BytesIO(f.read()))


def test_simulator_writes_png(temp_outdir, sample_png):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)
    display.show(sample_png)
    files = sorted(os.listdir(temp_outdir))
    assert len(files) == 1
    assert files[0] == "eink-0001.png"
    img = _read_image(os.path.join(temp_outdir, files[0]))
    assert img.size == (1600, 1200)


def test_simulator_clear_does_not_write(temp_outdir, caplog):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)
    display.clear()
    assert os.listdir(temp_outdir) == []


def test_simulator_incrementing_filenames(temp_outdir, sample_png):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)
    display.show(sample_png)
    display.show(sample_png)
    files = sorted(os.listdir(temp_outdir))
    assert len(files) == 2
    assert files[0] == "eink-0001.png"
    assert files[1] == "eink-0002.png"


def test_simulator_resolution():
    from src.display import create_display
    display = create_display("simulator", outdir="/tmp")
    assert display.resolution == (1600, 1200)


def test_create_display_unknown():
    from src.display import create_display
    with pytest.raises(ValueError, match="Unknown display driver"):
        create_display("nonexistent")


def test_create_display_inky_impression_not_available():
    from src.display import DRIVERS
    assert "simulator" in DRIVERS


def test_blend_palette():
    from src.display.inky_impression import _blend_palette
    pal = _blend_palette(0.5)
    assert len(pal) == 24
    assert pal[0:3] == [28, 24, 28]
    assert pal[3:6] == [255, 255, 255]


def test_fit_exact_size(temp_outdir):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)

    buf = io.BytesIO()
    Image.new("RGB", (1600, 1200), (0, 128, 0)).save(buf, format="PNG")
    png = buf.getvalue()

    display.show(png)
    img = _read_image(os.path.join(temp_outdir, "eink-0001.png"))
    assert img.size == (1600, 1200)
    assert img.getpixel((0, 0)) == (0, 128, 0)


def test_fit_undersized_centered(temp_outdir):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)

    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (0, 128, 0)).save(buf, format="PNG")
    png = buf.getvalue()

    display.show(png)
    img = _read_image(os.path.join(temp_outdir, "eink-0001.png"))
    assert img.size == (1600, 1200)
    assert img.getpixel((0, 0)) == (255, 255, 255)
    assert img.getpixel((400, 300)) == (0, 128, 0)


def test_fit_oversized_width_cropped_centered(temp_outdir):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)

    buf = io.BytesIO()
    Image.new("RGB", (1920, 1080), (0, 128, 0)).save(buf, format="PNG")
    png = buf.getvalue()

    display.show(png)
    img = _read_image(os.path.join(temp_outdir, "eink-0001.png"))
    assert img.size == (1600, 1200)
    assert img.getpixel((0, 0)) == (255, 255, 255)
    assert img.getpixel((0, 600)) == (0, 128, 0)
    assert img.getpixel((800, 0)) == (255, 255, 255)


def test_fit_oversized_both_cropped(temp_outdir):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)

    buf = io.BytesIO()
    Image.new("RGB", (2000, 1500), (0, 128, 0)).save(buf, format="PNG")
    png = buf.getvalue()

    display.show(png)
    img = _read_image(os.path.join(temp_outdir, "eink-0001.png"))
    assert img.size == (1600, 1200)
    assert img.getpixel((0, 0)) == (0, 128, 0)
    assert img.getpixel((1599, 1199)) == (0, 128, 0)


def test_fit_oversized_height_only(temp_outdir):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)

    buf = io.BytesIO()
    Image.new("RGB", (800, 1500), (0, 128, 0)).save(buf, format="PNG")
    png = buf.getvalue()

    display.show(png)
    img = _read_image(os.path.join(temp_outdir, "eink-0001.png"))
    assert img.size == (1600, 1200)
    assert img.getpixel((0, 0)) == (255, 255, 255)
    assert img.getpixel((400, 0)) == (0, 128, 0)
    assert img.getpixel((400, 1199)) == (0, 128, 0)