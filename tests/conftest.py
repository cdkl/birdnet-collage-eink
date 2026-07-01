import pytest
import tempfile
import os
import json

SAMPLE_PNG = (
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
)


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