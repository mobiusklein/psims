import pytest

from psims import document
from psims.mzid import writer, components
from .utils import output_path



def test_repr_borrow(output_path):
    f = writer.MzIdentMLWriter(open(output_path, 'wb'))

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
