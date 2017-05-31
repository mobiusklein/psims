from psims import document
from psims.mzid import writer, components
from .utils import output_path


def test_repr_borrow(output_path):
    f = writer.MzIdentMLWriter(open(output_path, 'wb'))

    with f:
        f.controlled_vocabularies()
        assert repr(f.SourceFile) == repr(components.SourceFile)
