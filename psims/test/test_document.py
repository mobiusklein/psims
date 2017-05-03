from psims import document
from psims.mzid import writer, components

path = "test_document.mzid"


def test_repr_borrow():
    f = writer.MzIdentMLWriter(open(path, 'wb'))

    with f:
        f.controlled_vocabularies()
        assert repr(f.SourceFile) == repr(components.SourceFile)
