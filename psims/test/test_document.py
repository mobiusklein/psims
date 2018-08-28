import pytest

from io import BytesIO

from psims import document
from psims.mzid import writer, components
from .utils import output_path



def test_repr_borrow():
    buffer = BytesIO()
    f = writer.MzIdentMLWriter(buffer)

    with f:
        f.controlled_vocabularies()
        assert repr(f.SourceFile) == repr(components.SourceFile)
    f.close()


def test_referential_integrity():
    ctx = document.DocumentContext()
    ctx["Spam"][1] = document.id_maker("Spam", 1)
    assert ctx['Spam'][1] == "SPAM_1"
    with pytest.warns(document.ReferentialIntegrityWarning):
        assert ctx['Spam'][2] == "SPAM_2"
    with pytest.warns(document.ReferentialIntegrityWarning):
        assert ctx['Spam']['With Purple Eggs'] == 'With Purple Eggs'


def test_xmlwriter(output_path):
    f = writer.MzIdentMLWriter(output_path)
    with f:
        pass
    f.close()
    try:
        f.format()
        with open(output_path, 'rb') as fh:
            print(fh.readline())
    except OSError:
        pass

    buffer = BytesIO()
    f = writer.MzIdentMLWriter(buffer)
    with f:
        f.write("Spam")
    f.format()
    f.close()
    with open(output_path, 'rb') as fh:
        print(fh.readline())
