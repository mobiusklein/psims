from io import BytesIO
from psims.transform import mzml, utils

from psims.test.test_data import datafile


def test_mzml_pipe():
    buff = BytesIO()
    path = datafile("small.mzML")
    st = mzml.MzMLTransformer(path, buff)
    st.write()
    buff.seek(0)
    test_reader = mzml.MzMLParser(buff)
    ref_reader = st.reader
    ref_reader.reset()

    for ref_spec, test_spec in zip(ref_reader, test_reader):
        assert utils.differ(ref_spec, test_spec)

    ref_reader.reset()
    test_reader.reset()
    for ref_spec, test_spec in zip(ref_reader.iterfind("fileDescription"),
                                   test_reader.iterfind("fileDescription")):
        assert utils.differ(ref_spec, test_spec)


if __name__ == '__main__':
    test_mzml_pipe()
