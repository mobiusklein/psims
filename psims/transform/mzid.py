import re

from pyteomics import mzid
from pyteomics.auxiliary import cvquery

from psims.utils import ensure_iterable
from psims.mzid import MzIdentMLWriter


from .utils import log


N = float('inf')
K = 1000


def identity(x):
    return x


class MzIdentMLParser(mzid.MzIdentML):
    def _handle_param(self, element, **kwargs):
        try:
            element.attrib["value"]
        except KeyError:
            element.attrib["value"] = ""
        return super(MzIdentMLParser, self)._handle_param(element, **kwargs)

    def reset(self):
        super(MzIdentMLParser, self).reset()
        self.seek(0)


class MzIdentMLTranslater(object):
    def _uncamel(self, name):
        temp = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', temp).lower()

    def _translate_keys(self, d, keys):
        for key in keys:
            try:
                d[self._uncamel(key)] = d.pop(key)
            except KeyError:
                continue

    def _extract_params(self, d):
        params = []
        for key, value in list(d.items()):
            if hasattr(key, 'accession'):
                accession = key.accession
                value_type = identity
                if accession:
                    term = self.writer.term(accession)
                    try:
                        value_type = term.value_type
                    except KeyError:
                        pass
                if isinstance(value, list):
                    value_list = value
                    for value in value_list:
                        unit = None
                        if hasattr(value, 'unit_info'):
                            unit = value.unit_info
                        try:
                            cast_value = value_type(value)
                        except ValueError:
                            cast_value = value
                        param = {
                            "name": key, "value": cast_value
                        }
                        if accession:
                            param['accession'] = accession
                        if unit:
                            param['unit_name'] = unit
                        params.append(param)
                else:
                    unit = None
                    if hasattr(value, 'unit_info'):
                        unit = value.unit_info
                    try:
                        cast_value = value_type(value)
                    except ValueError:
                        cast_value = value
                    param = {
                        "name": key, "value": cast_value
                    }
                    if accession:
                        param['accession'] = accession
                    if unit:
                        param['unit_name'] = unit
                    params.append(param)

                d.pop(key)
        return params

    def __init__(self, input_stream, output_stream):
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.reader = MzIdentMLParser(input_stream, retrieve_refs=False, iterative=True)
        self.writer = MzIdentMLWriter(output_stream, version=self.reader.version_info[0])

    def insert_software_record(self):
        # self.writer.AnalysisSoftware(
        #     name='psims-example-MzIdentMLTransformer',
        #     id='psims-example-MzIdentMLTransformer').write(self.writer.writer)
        pass

    def copy_provenance(self):
        log("Copying Provenance Information")
        self.reader.reset()
        try:
            analysis_software_list = next(self.reader.iterfind("AnalysisSoftwareList"))
        except StopIteration:
            analysis_software_list = []

        analysis_software_list = map(
            self._format_analysis_software, analysis_software_list.get("AnalysisSoftware"))

        with self.writer.AnalysisSoftwareList(analysis_software_list):
            self.insert_software_record()

        try:
            self.reader.reset()
            provider = self._format_provider(next(self.reader.iterfind("Provider")))
            provider.write(self.writer)
        except StopIteration:
            pass

        try:
            self.reader.reset()
            audit_collection = self._format_autit_collection(
                next(self.reader.iterfind("AuditCollection")))
            audit_collection.write(self.writer.writer)
        except StopIteration:
            pass

    def _format_analysis_software(self, software):
        d = {}
        d.update(software)
        d['name'] = d.pop('SoftwareName')
        contact_role = ensure_iterable(d.pop("ContactRole", {}))[0]
        d['role'] = contact_role.get("Role")
        d['contact'] = contact_role.get('contact_ref')
        return self.writer.AnalysisSoftware.ensure(d)

    def _format_provider(self, provider):
        d = {}
        d.update(provider)
        contact_role = ensure_iterable(d.pop("ContactRole", {}))[0]
        d['role'] = contact_role.get("Role")
        d['contact'] = contact_role.get('contact_ref')
        return self.writer.Provider.ensure(d)

    def _format_person(self, person):
        d = {}
        d.update(person)
        self._translate_keys(d, ['firstName', 'lastName', 'midInitials'])
        d['affiliations'] = [a.get('organization_ref') for a in ensure_iterable(d.pop("Affiliation", {}))
                             if a.get('organization_ref') is not None]
        return self.writer.Person.ensure(d)

    def _format_organization(self, organization):
        d = {}
        d.update(organization)
        d['parent'] = d.pop("Parent", {}).get("organization_ref")
        return self.writer.Organization.ensure(d)

    def _format_autit_collection(self, audit_collection):
        organization = map(self._format_organization, ensure_iterable(audit_collection.pop("Organization", None)))
        person = map(self._format_person, ensure_iterable(audit_collection.pop("Person", None)))
        return self.writer.AuditCollection(person, organization)

    def copy_sequence_collection(self):
        log("Copying Sequence Collection")
        writer = self.writer
        reader = self.reader
        with writer.sequence_collection():
            reader.reset()
            i = 0
            for db_seq in map(self._format_db_sequence, reader.iterfind("dBSequence")):
                i += 1
                db_seq.write(self.writer)
                if i % K == 0:
                    log("Copied %d dBSequences" % i)
                if i > N:
                    break

            reader.reset()
            i = 0
            for peptide in map(self._format_peptide, reader.iterfind("Peptide")):
                i += 1
                peptide.write(self.writer)
                if i % K == 0:
                    log("Copied %d Peptides" % i)
                if i > N:
                    break

            reader.reset()
            i = 0
            for peptide_ev in map(self._format_peptide_evidence, reader.iterfind("PeptideEvidence")):
                i += 1
                peptide_ev.write(self.writer)
                if i % K == 0:
                    log("Copied %d PeptideEvidence" % i)
                if i > N:
                    break

    def _format_db_sequence(self, db_sequence):
        d = dict(db_sequence)
        d['search_database_id'] = d.pop("searchDatabase_ref")
        d['sequence'] = d.pop("Seq", None)
        return self.writer.DBSequence.ensure(d)

    def _format_peptide(self, peptide):
        d = dict(peptide)
        d['peptide_sequence'] = d.pop("PeptideSequence")
        d['modifications'] = map(self._format_modification, d.pop("Modification", []))
        d['substitutions'] = map(self._format_substitution, d.pop("SubstitutionModification", []))
        return self.writer.Peptide.ensure(d)

    def _format_modification(self, mod):
        temp = dict(mod)
        d = dict()
        d['location'] = temp.pop("location", None)
        d['monoisotopic_mass_delta'] = temp.pop("monoisotopicMassDelta", None)
        d['residues'] = temp.pop("residues", None)
        term_dict = cvquery(temp)
        crosslinking_donor_or_receiver = None
        has_identity = False
        params = []
        d['params'] = params

        for key, value in list(term_dict.items()):
            term = self.writer.term(key)
            if term.is_of_type('UNIMOD:0'):
                d['name'] = term.name
                has_identity = True
                term_dict.pop(key)
            elif term.is_of_type("MS:1001460"):
                d['name'] = value
                d['accession'] = "MS:1001460"
                term_dict.pop(key)
                has_identity = True
            # crosslinking donor
            elif term.is_of_type("MS:1002508"):
                crosslinking_donor_or_receiver = {"name": term.name, 'accession': term.id, 'value': int(value)}
                term_dict.pop(key)
            elif term.is_of_type("XLMOD:00001") or term.is_of_type("XLMOD:00002"):
                d['name'] = term.name
                has_identity = True
                term_dict.pop(key)

        if not has_identity and crosslinking_donor_or_receiver:
            d.update(crosslinking_donor_or_receiver)
        elif crosslinking_donor_or_receiver:
            params.append(crosslinking_donor_or_receiver)
        return self.writer.Modification.ensure(d)

    def _format_substitution(self, sub):
        d = dict(sub)
        self._translate_keys(d, ["originalResidue", "replacementResidue", "monoisotopicMassDelta"])
        return self.writer.SubstitutionModification.ensure(d)

    def _format_peptide_evidence(self, evidence):
        d = dict(evidence)
        d['peptide_id'] = d.pop("peptide_ref")
        d['db_sequence_id'] = d.pop("dBSequence_ref")
        d['start_position'] = d.pop('start', None)
        d['end_position'] = d.pop('end', None)
        d['translation_table_id'] = d.pop('translationTable_ref', None)
        d['is_decoy'] = d.pop("isDecoy", False)
        return self.writer.PeptideEvidence.ensure(d)

    def copy_analysis_collection(self):
        reader = self.reader
        writer = self.writer
        reader.reset()
        analysis_collection = next(reader.iterfind("AnalysisCollection"))
        with self.writer.analysis_collection():
            for si in analysis_collection.get("SpectrumIdentification", []):
                self._format_spectrum_identification(si).write(writer)
            for pi in ensure_iterable(analysis_collection.get("ProteinDetection", [])):
                self._format_protein_detection(pi).write(writer)

    def _format_enzyme(self, enz):
        d = dict(enz)
        d['name'] = d.pop("EnzymeName", None)
        d['site_regexp'] = d.pop('SiteRegexp', None)
        d['missed_cleavages'] = d.pop("missedCleavages", 0)
        self._translate_keys(d, ["minDistance", "semiSpecific", "nTermGain", "cTermGain"])
        return self.writer.Enzyme.ensure(d)

    def _format_search_modification(self, mod):
        temp = dict(mod)
        d = dict()
        d['fixed'] = temp.pop("fixedMod", False)
        d['mass_delta'] = temp.pop("massDelta")
        d['specificity'] = temp.pop('SpecificityRules', [])
        d['residues'] = temp.pop("residues")
        term_dict = cvquery(temp)
        crosslinking_donor_or_receiver = None
        has_identity = False
        params = []
        d['params'] = params

        for key, value in list(term_dict.items()):
            term = self.writer.term(key)
            if term.is_of_type('UNIMOD:0'):
                d['name'] = term.name
                has_identity = True
                term_dict.pop(key)
            elif term.is_of_type("MS:1001460"):
                d['name'] = value
                d['accession'] = "MS:1001460"
                term_dict.pop(key)
                has_identity = True
            # crosslinking donor
            elif term.is_of_type("MS:1002508"):
                crosslinking_donor_or_receiver = {"name": term.name, 'accession': term.id, 'value': int(value)}
                term_dict.pop(key)
            elif term.is_of_type("XLMOD:00001") or term.is_of_type("XLMOD:00002"):
                d['name'] = term.name
                has_identity = True
                term_dict.pop(key)

        if not has_identity and crosslinking_donor_or_receiver:
            d.update(crosslinking_donor_or_receiver)
        elif crosslinking_donor_or_receiver:
            params.append(crosslinking_donor_or_receiver)
        return self.writer.SearchModification.ensure(d)

    def _format_tolerance(self, tol, tp):
        term_dict = cvquery(tol)
        value = term_dict.get('MS:1001413')
        low = {"accession": 'MS:1001413', "value": value, 'unit_name': getattr(value, 'unit_info', None)}
        value = term_dict.get('MS:1001412')
        high = {"accession": 'MS:1001412', "value": value, 'unit_name': getattr(value, 'unit_info', None)}
        return tp(low, high)

    def _format_spectrum_identification_protocol(self, sip):
        d = dict(sip)
        d['additional_search_params'] = d.pop("AdditionalSearchParams", [])
        enzymes = d.pop("Enzymes", {})
        d['enzymes'] = self.writer.Enzymes(
            map(self._format_enzyme, ensure_iterable(enzymes.get("Enzyme", {}))),
            independent=enzymes.get("independent"))
        d['modification_params'] = map(
            self._format_search_modification, ensure_iterable(
                d.pop('ModificationParams', {}).get("SearchModification", [])))
        d['search_type'] = d.pop("SearchType", None)
        d['parent_tolerance'] = self._format_tolerance(d.pop("ParentTolerance", {}), self.writer.ParentTolerance)
        d['fragment_tolerance'] = self._format_tolerance(d.pop("FragmentTolerance", {}), self.writer.FragmentTolerance)
        d['threshold'] = self._extract_params(d.pop("Threshold"))
        d['analysis_software_id'] = d.pop("analysisSoftware_ref")
        return self.writer.SpectrumIdentificationProtocol.ensure(d)

    def _format_protein_detection_protocol(self, pdp):
        d = dict(pdp)
        d['threshold'] = self._extract_params(d.pop("Threshold"))
        d['analysis_software_id'] = d.pop("analysisSoftware_ref")
        d['params'] = d.pop("AnalysisParams", [])
        return self.writer.ProteinDetectionProtocol.ensure(d)

    def copy_analysis_protocol_collection(self):
        log("Copying Protocols")
        self.reader.reset()
        apc = next(self.reader.iterfind("AnalysisProtocolCollection", retrieve_refs=False))
        protocols = []
        for sip in ensure_iterable(apc.get("SpectrumIdentificationProtocol", [])):
            protocols.append(self._format_spectrum_identification_protocol(sip))
        for pdp in ensure_iterable(apc.get("ProteinDetectionProtocol", [])):
            protocols.append(self._format_protein_detection_protocol(pdp))
        with self.writer.analysis_protocol_collection():
            for protocol in protocols:
                protocol.write(self.writer)

    def _format_spectrum_identification(self, si):
        d = dict(si)
        self._translate_keys(d, ['activityDate'])
        d['spectrum_identification_list_id'] = d.pop("spectrumIdentificationList_ref")
        d['spectrum_identification_protocol_id'] = d.pop("spectrumIdentificationProtocol_ref")
        d['spectra_data_ids_used'] = [s['spectraData_ref'] for s in d.pop('InputSpectra', [])]
        d['search_database_ids_used'] = [s['searchDatabase_ref'] for s in d.pop('SearchDatabaseRef', [])]
        return self.writer.SpectrumIdentification.ensure(d)

    def _format_protein_detection(self, pi):
        d = dict(pi)
        self._translate_keys(d, ['activityDate'])
        d['protein_detection_list_id'] = d.pop("proteinDetectionList_ref")
        d['protein_detection_protocol_id'] = d.pop("proteinDetectionProtocol_ref")
        d['spectrum_identification_ids_used'] = [
            si['spectrumIdentificationList_ref'] for si in d.pop("InputSpectrumIdentifications", [])
        ]
        return self.writer.ProteinDetection.ensure(d)

    def copy_inputs(self):
        log("Copying Inputs")
        self.reader.reset()
        inputs = next(self.reader.iterfind('Inputs'))
        source_files = map(self._format_source_file, ensure_iterable(inputs.get("SourceFile")))
        search_databases = map(self._format_search_database, ensure_iterable(inputs.get("SearchDatabase")))
        spectra_data = map(self._format_spectra_data, ensure_iterable(inputs.get("SpectraData")))
        self.writer.inputs(source_files, search_databases, spectra_data)

    def _format_file_record(self, fr):
        d = dict(fr)
        file_format = d.pop("FileFormat", {})
        format_type = self._extract_params(file_format)
        if format_type:
            d['file_format'] = format_type[0]
        d['external_format'] = d.pop("ExternalFormatDocumentation", None)
        return d

    def _format_source_file(self, sf):
        d = self._format_file_record(sf)
        return self.writer.SourceFile.ensure(d)

    def _format_spectra_data(self, sd):
        d = self._format_file_record(sd)
        self._translate_keys(d, ['SpectrumIDFormat'])
        return self.writer.SpectraData.ensure(d)

    def _format_search_database(self, sd):
        d = self._format_file_record(sd)
        d['name'] = d.pop("DatabaseName", None)
        if isinstance(d['name'], dict):
            try:
                d['name'] = list(d['name'])[0]
            except KeyError:
                pass
        self._translate_keys(d, ["numDatabaseSequences", "numResidues", "releaseDate", "version"])
        return self.writer.SearchDatabase.ensure(d)

    def copy_analysis_data(self):
        log("Copying Analysis Data")
        reader = self.reader
        writer = self.writer
        with writer.analysis_data():
            reader.reset()
            for spectrum_identification_list in reader.iterfind("SpectrumIdentificationList"):
                list_id = spectrum_identification_list.pop('id')
                with writer.spectrum_identification_list(list_id):
                    i = 0
                    for spectrum_id_result in spectrum_identification_list.pop("SpectrumIdentificationResult", []):
                        i += 1
                        result = self._format_spectrum_identification_result(spectrum_id_result)
                        with result:
                            for item in map(
                                    self._format_spectrum_identification_item,
                                    spectrum_id_result['SpectrumIdentificationItem']):
                                item.write(self.writer)
                        if i % K == 0:
                            log("Copied %d SpectrumIdentificationResults" % i)
                        if i > N:
                            break

            reader.reset()
            for protein_detection_list in reader.iterfind("ProteinDetectionList"):
                list_id = protein_detection_list.pop('id')
                size = len(protein_detection_list['ProteinAmbiguityGroup'])
                with writer.protein_detection_list(list_id, count=size):
                    i = 0
                    for pag in protein_detection_list.pop('ProteinAmbiguityGroup'):
                        i += 1
                        result = self._format_protein_ambiguity_group(pag)
                        with result:
                            j = 0
                            for prot in pag['ProteinDetectionHypothesis']:
                                result = self._format_protein_detection_hypothesis(prot)
                                with result:
                                    k = 0
                                    for pept in prot['PeptideHypothesis']:
                                        result = self._format_peptide_detection_hypothesis(pept)
                                        result.write(self.writer)
                                    k += 1
                                    if k > N:
                                        break
                            j += 1
                            if j > N:
                                break
                        if i % K == 0:
                            log("Copied %d ProteinAmbiguityGroups" % i)
                        if i > N:
                            break

    def _format_spectrum_identification_result(self, sir):
        d = dict(sir)
        self._translate_keys(d, ['spectrumID'])
        d['spectra_data_id'] = d.pop('spectraData_ref', None)
        d.pop('SpectrumIdentificationItem', [])
        d['params'] = self._extract_params(d)
        return self.writer.SpectrumIdentificationResult.ensure(d)

    def _format_spectrum_identification_item(self, sii):
        d = dict(sii)
        self._translate_keys(
            d, ('chargeState', 'passThreshold', 'experimentalMassToCharge', 'calculatedMassToCharge'))
        d['peptide_id'] = d.pop("peptide_ref")
        d['peptide_evidence_ids'] = [p['peptideEvidence_ref'] for p in d.pop("PeptideEvidenceRef", [])]
        d['params'] = self._extract_params(d)
        return self.writer.SpectrumIdentificationItem.ensure(d)

    def _format_protein_ambiguity_group(self, pag):
        d = dict(pag)
        d.pop("ProteinDetectionHypothesis", [])
        d['protein_detection_hypotheses'] = []
        d['params'] = self._extract_params(d)
        return self.writer.ProteinAmbiguityGroup.ensure(d)

    def _format_protein_detection_hypothesis(self, prot):
        d = dict(prot)
        d['db_sequence_id'] = d.pop("dBSequence_ref")
        d.pop("PeptideHypothesis", [])
        d['peptide_hypotheses'] = []
        self._translate_keys(d, ['passThreshold', ])
        d['params'] = self._extract_params(d)
        return self.writer.ProteinDetectionHypothesis.ensure(d)

    def _format_peptide_detection_hypothesis(self, pept):
        d = dict(pept)
        d['peptide_evidence_id'] = d.pop("peptideEvidence_ref")
        d['spectrum_identification_ids'] = [
            siir['spectrumIdentificationItem_ref'] for siir in d.pop('SpectrumIdentificationItemRef')]
        d['params'] = self._extract_params(d)
        return self.writer.PeptideHypothesis.ensure(d)

    def write(self):
        writer = self.writer
        with writer:
            writer.controlled_vocabularies()
            self.copy_provenance()
            self.copy_sequence_collection()
            self.copy_analysis_collection()
            self.copy_analysis_protocol_collection()
            with writer.data_collection():
                self.copy_inputs()
                self.copy_analysis_data()
        try:
            self.output_stream.seek(0)
            self.writer.format()
        except Exception:
            pass
