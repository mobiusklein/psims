import io
import os
import tempfile
import gzip

import pytest

fixtured_files = []


def identity(x, y):
    return x

compression_openers = [open, gzip.GzipFile, identity]


class UnclosableBuffer(io.BytesIO):

    def close(self):
        return


@pytest.fixture(scope='function', params=compression_openers)
def compressor(request):
    return request.param


@pytest.fixture(scope='function')
def output_path(request):
    fd, path = tempfile.mkstemp()
    fixtured_files.append(path)

    def fin():
        os.close(fd)
        try:
            os.remove(path)
        except OSError as e:
            print(e, fd)
    request.addfinalizer(fin)
    return path


test_root = os.path.abspath(os.path.dirname(__file__))


def find_test_file(name):
    return os.path.join(test_root, name)


@pytest.fixture(scope="session", autouse=True)
def remove_all_temp_files(request):
    def clean_files():
        for f in fixtured_files:
            try:
                os.remove(f)
            except Exception as e:
                print(e)
    request.addfinalizer(clean_files)
