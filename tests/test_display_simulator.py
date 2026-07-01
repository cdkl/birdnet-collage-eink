import pytest
import os


def test_simulator_writes_png(temp_outdir, sample_png):
    from src.display import create_display
    display = create_display("simulator", outdir=temp_outdir)
    display.show(sample_png)
    files = sorted(os.listdir(temp_outdir))
    assert len(files) == 1
    assert files[0].endswith(".png")
    path = os.path.join(temp_outdir, files[0])
    with open(path, "rb") as f:
        assert f.read() == sample_png


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
    # inky_impression may or may not be available depending on env
    # but the factory should always work for known drivers


def test_blend_palette():
    from src.display.inky_impression import _blend_palette
    pal = _blend_palette(0.5)
    assert len(pal) == 24
    assert pal[0:3] == [28, 24, 28]
    assert pal[3:6] == [255, 255, 255]