from io import BytesIO
from psims.transform import mzid, utils

from psims.test.test_data import datafile


def test_mzid_pipe():
    buff = BytesIO()
    path = datafile("xiFDR-CrossLinkExample_single_run.mzid")
    st = mzid.MzIdentMLTranslator(path, buff)
    st.write()

    buff.seek(0)
    test_reader = mzid.MzIdentMLParser(buff)
    ref_reader = st.reader
    ref_reader.reset()

    for tag in ["Peptide", "SpectrumIdentificationResult", "ProteinAmbiguityGroup", "SpectrumIdentificationProtocol"]:
        ref_reader.reset()
        test_reader.reset()

        for ref, test in zip(ref_reader.iterfind(tag, retrieve_refs=False),
                             test_reader.iterfind(tag, retrieve_refs=False)):
            assert utils.differ(ref, test)


if __name__ == '__main__':
    test_mzid_pipe()
