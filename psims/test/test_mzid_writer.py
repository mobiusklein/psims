from psims.mzid import MzIdentMLWriter
from pyteomics import mzid
from lxml import etree

from psims.test import mzid_data
from psims.test.utils import output_path as output_path


def test_write(output_path):
    software = mzid_data.software
    spectra_data = mzid_data.spectra_data
    search_database = mzid_data.search_database
    spectrum_identification_list = mzid_data.spectrum_identification_list

    proteins = mzid_data.proteins
    peptides = mzid_data.peptides
    peptide_evidence = mzid_data.peptide_evidence

    protocol = mzid_data.protocol
    analysis = mzid_data.analysis
    source_file = mzid_data.source_file

    f = MzIdentMLWriter(open(output_path, 'wb'))
    with f:
        f.controlled_vocabularies()
        f.providence(software=software)
        f.register("SpectraData", spectra_data['id'])
        f.register("SearchDatabase", search_database['id'])
        f.register("SpectrumIdentificationList", spectrum_identification_list["id"])

        f._sequence_collection(proteins, peptides, peptide_evidence)

        with f.analysis_protocol_collection():
            f.spectrum_identification_protocol(**protocol)
        with f.analysis_collection():
            f.SpectrumIdentification(*analysis).write(f)
        with f.data_collection():
            f.inputs(source_file, search_database, spectra_data)
            with f.analysis_data():
                f.spectrum_identification_list(**spectrum_identification_list)

    try:
        f.format()
    except OSError:
        pass

    reader = mzid.read(output_path)
    n_peptide_evidence = len(peptide_evidence)
    assert n_peptide_evidence == len(list(reader.iterfind("PeptideEvidence")))
