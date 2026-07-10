import pytest
import tempfile
import os
import io
from PIL import Image


def _make_png(width, height, color=(255, 0, 0)):
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


SAMPLE_PNG = _make_png(1, 1)


@pytest.fixture
def sample_png():
    return SAMPLE_PNG


@pytest.fixture
def temp_cache():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def temp_outdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def etag_file(temp_cache):
    return os.path.join(temp_cache, "last-etag.txt")