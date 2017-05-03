from psims.mzid import MzIdentMLWriter
from pyteomics import mzid
from lxml import etree

from psims.test import mzid_data


path = 'test_mzid.mzid'


def test_write():
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

    f = MzIdentMLWriter(open(path, 'wb'))
    with f:
        f.controlled_vocabularies()
        f.providence(software=software)
        f.register("SpectraData", spectra_data['id'])
        f.register("SearchDatabase", search_database['id'])
        f.register("SpectrumIdentificationList", spectrum_identification_list["id"])

        f.sequence_collection(proteins, peptides, peptide_evidence)

        with f.analysis_protocol_collection():
            f.spectrum_identification_protocol(**protocol)
        with f.element("AnalysisCollection"):
            f.SpectrumIdentification(*analysis).write(f)
        with f.element("DataCollection"):
            f.inputs(source_file, search_database, spectra_data)
            with f.element("AnalysisData"):
                f.spectrum_identification_list(**spectrum_identification_list)

    f.format()

    reader = mzid.read(path)
    n_peptide_evidence = len(peptide_evidence)
    assert n_peptide_evidence == len(list(reader.iterfind("PeptideEvidence")))
