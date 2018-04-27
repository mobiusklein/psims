from psims.mzid import MzIdentMLWriter
from pyteomics import mzid
from lxml import etree

from psims import compression
from psims.test import mzid_data
from psims.test.utils import output_path as output_path, compressor


def test_write(output_path, compressor):
    software = mzid_data.software
    spectra_data = mzid_data.spectra_data
    search_database = mzid_data.search_database
    spectrum_identification_list = mzid_data.spectrum_identification_list
    protein_detect_list = mzid_data.protein_detect_list

    proteins = mzid_data.proteins
    peptides = mzid_data.peptides
    peptide_evidence = mzid_data.peptide_evidence

    spectrum_id_protocol = mzid_data.spectrum_id_protocol
    protein_detection_protocol = mzid_data.protein_detection_protocol
    analysis = mzid_data.analysis
    source_file = mzid_data.source_file

    f = MzIdentMLWriter(compressor(output_path, 'wb'), close=True)
    with f:
        f.controlled_vocabularies()
        f.providence(software=software)
        f.register("SpectraData", spectra_data['id'])
        f.register("SearchDatabase", search_database['id'])
        f.register("SpectrumIdentificationList", spectrum_identification_list["id"])
        f.register("SpectrumIdentificationProtocol", spectrum_id_protocol['id'])
        f.register("ProteinDetectionProtocol", protein_detection_protocol['id'])
        f.register("ProteinDetectionList", 1)

        with f.sequence_collection():
            for prot in proteins:
                f.write_db_sequence(**prot)
            for pep in peptides:
                f.write_peptide(**pep)
            for evid in peptide_evidence:
                f.write_peptide_evidence(**evid)

        with f.analysis_collection():
            f.SpectrumIdentification(*analysis).write(f)
            f.ProteinDetection(spectrum_identification_ids_used=[spectrum_identification_list["id"]]).write(f)
        with f.analysis_protocol_collection():
            f.spectrum_identification_protocol(**spectrum_id_protocol)
            f.protein_detection_protocol(**protein_detection_protocol)
        with f.data_collection():
            f.inputs(source_file, search_database, spectra_data)
            with f.analysis_data():
                with f.spectrum_identification_list(id=spectrum_identification_list['id']):
                    for result in spectrum_identification_list['identification_results']:
                        f.write_spectrum_identification_result(**result)
                with f.protein_detection_list(id=protein_detect_list['id'], count=len(
                        protein_detect_list['protein_ambiguity_groups'])):
                    for pag in protein_detect_list['protein_ambiguity_groups']:
                        f.write_protein_ambiguity_group(**pag)

    try:
        f.format()
        f.close()
    except OSError:
        pass
    opener = compression.get(output_path)
    assert opener == compressor
    reader = mzid.read(opener(output_path, 'rb'))

    def reset():
        reader.reset()
        reader.seek(0)

    n_peptide_evidence = len(peptide_evidence)
    assert n_peptide_evidence == len(list(reader.iterfind("PeptideEvidence")))
    n_spectrum_identification_results = len(spectrum_identification_list['identification_results'])
    reset()
    assert n_spectrum_identification_results == len(list(reader.iterfind("SpectrumIdentificationResult")))
    reset()
    protocol = next(reader.iterfind("SpectrumIdentificationProtocol"))
    mods = protocol['ModificationParams']['SearchModification']
    assert len(mods) == 2
    assert mods[0]['fixedMod']
    assert not mods[1]['fixedMod']
    assert "unknown modification" in mods[1]
    reader.close()
