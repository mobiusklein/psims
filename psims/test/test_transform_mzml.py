import itertools
from psims.transform import mzml, utils

from psims.test.test_data import datafile
from psims.test.utils import UnclosableBuffer

def test_mzml_pipe():
    buff = UnclosableBuffer()
    path = datafile("small.mzML")
    st = mzml.MzMLTransformer(path, buff)
    st.write()
    buff.seek(0)
    test_reader = mzml.MzMLParser(buff)
    ref_reader = st.reader
    ref_reader.reset()

    for ref_spec, test_spec in itertools.zip_longest(ref_reader, test_reader):
        assert utils.differ(ref_spec, test_spec)

    ref_reader.reset()
    test_reader.reset()
    for ref_spec, test_spec in itertools.zip_longest(ref_reader.iterfind("fileDescription"),
                                                     test_reader.iterfind("fileDescription")):
        assert utils.differ(ref_spec, test_spec)
    super(UnclosableBuffer, buff).close()


def transform(spectrum):
    peaks_above_mean = (spectrum['intensity array'] > spectrum['intensity array'].mean()).sum()
    spectrum['peaks above mean intensity'] = peaks_above_mean
    spectrum['peaks below mean intensity'] = {'name': 'peaks below mean intensity', 'value': spectrum['intensity array'].size - peaks_above_mean, 'type': 'xsd:integer'}
    return spectrum


def test_mzml_pipe_transformed():
    buff = UnclosableBuffer()
    path = datafile("small.mzML")
    st = mzml.MzMLTransformer(path, buff, transform, "custom transform")
    st.write()
    buff.close()

    buff.seek(0)
    test_reader = mzml.MzMLParser(buff)
    ref_reader = st.reader
    ref_reader.reset()

    for ref_spec, test_spec in itertools.zip_longest(ref_reader, test_reader):
        assert test_spec['peaks above mean intensity']
    super(UnclosableBuffer, buff).close()


if __name__ == '__main__':
    test_mzml_pipe()
