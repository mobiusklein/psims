import warnings
import operator
import re

from datetime import datetime
from numbers import Number as NumberBase
from itertools import chain

from ..xml import (
    _element, element, TagBase, ProvidedCV, UserParam,
    CVParam, sanitize_id)
from ..document import (
    ComponentBase as _ComponentBase, NullMap, ComponentDispatcherBase)

from .utils import ensure_iterable

from lxml import etree


class MzIdentML(TagBase):
    type_attrs = {
        "xmlns": "http://psidev.info/psi/pi/mzIdentML/1.1",
        "version": "1.1.0",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://psidev.info/psi/pi/mzIdentML/1.1 ../../schema/mzIdentML1.1.0.xsd"
    }

    def __init__(self, **attrs):
        attrs.setdefault('creationDate', datetime.utcnow())
        super(MzIdentML, self).__init__("MzIdentML", **attrs)


_COMPONENT_NAMESPACE = 'mzid'


class ComponentDispatcher(ComponentDispatcherBase):
    def __init__(self, *args, **kwargs):
        super(ComponentDispatcher, self).__init__(*args, component_namespace=_COMPONENT_NAMESPACE, **kwargs)


class ComponentBase(_ComponentBase):
    component_namespace = _COMPONENT_NAMESPACE


def _unimod_converter(modification):
    return {
        "name": modification.code_name,
        "id": "UNIMOD:%s" % modification.id,
        "_object": modification
    }


default_cv_list = [
    _element(
        "cv", id="PSI-MS",
        uri=("http://psidev.cvs.sourceforge.net/viewvc/*checkout*/psidev"
             "/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"),
        version="2.25.0", fullName="PSI-MS"),
    _element(
        "cv", id="UO",
        uri="http://obo.cvs.sourceforge.net/*checkout*/obo/obo/ontology/phenotype/unit.obo",
        fullName="UNIT-ONTOLOGY"),
    ProvidedCV(id="UNIMOD", uri="http://www.unimod.org/obo/unimod.obo", fullName="UNIMOD", converter=_unimod_converter)
]


common_units = {
    "parts per million": "UO:0000169",
    "dalton": "UO:0000221"
}


_xmlns = "http://psidev.info/psi/pi/mzIdentML/1.1"


class GenericCollection(ComponentBase):
    def __init__(self, tag_name, members, context=NullMap):
        self.members = members
        self.tag_name = tag_name
        self.element = _element(tag_name, xmlns=_xmlns)

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            for member in self.members:
                member.write(xml_file)


class IDGenericCollection(GenericCollection):
    def __init__(self, tag_name, members, id, context=NullMap):
        self.members = members
        self.tag_name = tag_name
        self.element = _element(tag_name, xmlns=_xmlns, id=id)
        context[tag_name][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for member in self.members:
                member.write(xml_file)

# --------------------------------------------------
# Input File Information


class SourceFile(ComponentBase):
    def __init__(self, location, file_format, id=None, context=NullMap):
        self.file_format = file_format
        self.element = _element("SourceFile", location=location, id=id)
        self.context = context
        context["SourceFile"][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            with element(xml_file, "FileFormat"):
                self.context.param(self.file_format)(xml_file)


class SearchDatabase(ComponentBase):
    def __init__(self, name, file_format, location=None, id=None, context=NullMap):
        self.location = location
        self.file_format = file_format
        self.element = _element("SearchDatabase", location=location, name=name, id=id)
        context["SearchDatabase"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            with element(xml_file, "FileFormat"):
                self.context.param(self.file_format)(xml_file)
            with element(xml_file, "DatabaseName"):
                UserParam(name=self.name).write(xml_file)


class SpectraData(ComponentBase):
    def __init__(self, location, file_format, spectrum_id_format, id=None, context=NullMap):
        self.file_format = file_format
        self.spectrum_id_format = spectrum_id_format
        self.element = _element("SpectraData", id=id, location=location)
        context['SpectraData'][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            with element(xml_file, "FileFormat"):
                self.context.param(self.file_format)(xml_file)
            with element(xml_file, "SpectrumIDFormat"):
                self.context.param(self.spectrum_id_format)(xml_file)


class Inputs(GenericCollection):
    def __init__(self, source_files=tuple(), search_databases=tuple(), spectra_data=tuple(), context=NullMap):
        items = list()
        items.extend(source_files)
        items.extend(search_databases)
        items.extend(spectra_data)
        super(Inputs, self).__init__("Inputs", items, context=context)

# --------------------------------------------------
# Identification Information


class DBSequence(ComponentBase):
    def __init__(self, accession, sequence=None, id=None, search_database_id=1, params=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        params.extend(kwargs.items())
        self.params = params
        self.sequence = sequence
        self.search_database_ref = context['SearchDatabase'][search_database_id]
        self.element = _element(
            "DBSequence", accession=accession, id=id,
            length=len(sequence), searchDatabase_ref=self.search_database_ref)

        context["DBSequence"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        protein = self.sequence
        with self.element.element(xml_file, with_id=True):
            if self.sequence is not None:
                with element(xml_file, "Seq"):
                    xml_file.write(protein)
            for param in self.params:
                self.context.param(param)(xml_file)


class Peptide(ComponentBase):
    def __init__(self, peptide_sequence, id, modifications=None, params=None, context=NullMap):
        if modifications is None:
            modifications = []
        if params is None:
            params = []

        self.context = context
        self.peptide_sequence = peptide_sequence
        self.modifications = [Modification(context=context, **mod) for mod in modifications]
        self.params = params
        self.element = _element("Peptide", id=id)
        context["Peptide"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            with element(xml_file, "PeptideSequence"):
                xml_file.write(self.peptide_sequence)
            for mod in self.modifications:
                mod.write(xml_file)
            for param in self.params:
                self.context.param(param)(xml_file)


class Modification(ComponentBase):
    def __init__(self, monoisotopic_mass_delta=None, location=None, name=None,
                 id=None, known=True, params=None, context=NullMap):
        if params is None:
            params = []
        if id is None:
            try:
                mod = context.term(name)
                self.name = mod["name"]
                self.accession = mod['id']
            except KeyError:
                known = False
                self.name = name
                self.accession = "MS:1001460"
        elif name is None:
            try:
                mod = context.term(id)
                self.name = mod["name"]
                self.accession = mod['id']
            except KeyError:
                known = False
                self.name = id
                self.accession = "MS:1001460"
        else:
            warnings.warn("Unknown modification saved: %s" % monoisotopic_mass_delta)
            self.name = name
            self.accession = id

        self.element = _element(
            "Modification", monoisotopicMassDelta=monoisotopic_mass_delta,
            location=location)
        self.context = context
        self.params = params
        self.known = known

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            if self.accession is not None:
                if self.known:
                    self.context.param(
                        name=self.name, accession=self.accession,
                        ref=self.accession.split(":")[0])(xml_file)
                else:
                    self.context.param(
                        name="unknown modification",
                        accession=self.accession,
                        value=self.name,
                        ref=self.accession.split(":")[0])(xml_file)
            for param in self.params:
                self.context.param(param)(xml_file)


class PeptideEvidence(ComponentBase):
    def __init__(self, peptide_id, db_sequence_id, id, start_position, end_position,
                 is_decoy=False, pre='', post='', params=None, context=NullMap):
        if params is None:
            params = []
        self.params = params
        self.context = context
        self.peptide_id = peptide_id
        self.db_sequence_id = db_sequence_id
        self.element = _element(
            "PeptideEvidence", isDecoy=is_decoy, start=start_position,
            end=end_position, peptide_ref=context["Peptide"][peptide_id],
            dBSequence_ref=context['DBSequence'][db_sequence_id],
            pre=pre, post=post, id=id)
        context["PeptideEvidence"][id] = self.element.id

    def write(self, xml_file):
        if self.params:
            with self.element(xml_file, with_id=True):
                for param in self.params:
                    self.context.param(param)(xml_file)
        else:
            xml_file.write(self.element(with_id=True))


class SpectrumIdentificationResult(ComponentBase):
    def __init__(self, spectra_data_id, spectrum_id, id=None, identifications=None, context=NullMap):
        if identifications is None:
            identifications = []
        self.identifications = identifications
        self.element = _element(
            "SpectrumIdentificationResult", spectraData_ref=context["SpectraData"][spectra_data_id],
            spectrumID=spectrum_id, id=id)

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for item in self.identifications:
                item.write(xml_file)


class IonType(ComponentBase):
    def __init__(self, series, indices, charge_state, measures=None, context=NullMap):
        if measures is None:
            measures = dict()
        self.context = context
        self.series = series
        self.measures = measures
        self.element = _element(
            "IonType", charge=charge_state, index=' '.join([str(int(i)) for i in ensure_iterable(indices)]))

    def write(self, xml_file):
        with self.element(xml_file):
            self.context.param(self.series)(xml_file)
            for measure, values in self.measures.items():
                el = _element(
                    "FragmentArray", measure_ref=self.context["Measure"][measure],
                    values=' '.join([str(float(i)) for i in values]))
                el.write(xml_file)

    all_ion_types = [
        'frag: a ion', 'frag: a ion - H2O', 'frag: a ion - NH3',
        'frag: b ion', 'frag: b ion - H2O', 'frag: b ion - NH3',
        'frag: c ion', 'frag: c ion - H2O', 'frag: c ion - NH3',
        'frag: d ion',
        'frag: immonium ion',
        'frag: internal ya ion',
        'frag: internal yb ion',
        'frag: precursor ion', 'frag: precursor ion - H2O', 'frag: precursor ion - NH3',
        'frag: v ion',
        'frag: w ion',
        'frag: x ion', 'frag: x ion - H2O', 'frag: x ion - NH3',
        'frag: y ion', 'frag: y ion - H2O', 'frag: y ion - NH3',
        'frag: z ion', 'frag: z ion - H2O', 'frag: z ion - NH3',
        'frag: z+1 ion', 'frag: z+2 ion'
    ]

    _ion_pattern = re.compile(
        r"""(?P<prefix>frag:\s?)?
            (?P<key>[abcxyzdvw]|internal [yab]{2}|precursor|immonium|z\+[12])
            (?P<ion>\s?ion\s?)?
            (?=\s?-\s?(?P<loss>NH3|H2O))?""", re.VERBOSE)

    @classmethod
    def guess_ion_type(cls, string):
        match = cls._ion_pattern.search(string)
        if match:
            groups = match.groupdict()
            loss = groups.get("loss")
            if loss is not None:
                loss = " - " + loss
            else:
                loss = ''
            return "frag: {key} ion{loss}".format(key=groups['key'], loss=loss)
        else:
            raise KeyError("No mapping found for %s" % string)


class SpectrumIdentificationItem(ComponentBase):
    def __init__(self, calculated_mass_to_charge, experimental_mass_to_charge,
                 charge_state, peptide_id, peptide_evidence_id, score, id, ion_types=None,
                 params=None, pass_threshold=True, rank=1, context=NullMap):
        self.peptide_evidence_ref = context["PeptideEvidence"][peptide_evidence_id]
        self.params = params
        self.score = score
        self.ion_types = ion_types
        self.element = _element(
            "SpectrumIdentificationItem", calculatedMassToCharge=calculated_mass_to_charge, chargeState=charge_state,
            experimentalMassToCharge=experimental_mass_to_charge, id=id, passThreshold=pass_threshold,
            peptide_ref=context['Peptide'][peptide_id]
        )
        context['SpectrumIdentificationItem'][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            _element(
                "PeptideEvidenceRef",
                peptideEvidence_ref=self.peptide_evidence_ref).write(
                xml_file)
            ion_types = ensure_iterable(self.ion_types)
            if self.ion_types is not None and len(ion_types) > 0:
                with element(xml_file, "Fragmentation"):
                    for ion_type in ion_types:
                        ion_type.write(xml_file)
            if isinstance(self.score, CVParam):
                self.score.write(xml_file)
            elif isinstance(self.score, dict):
                self.context.param(self.score)(xml_file)
            else:
                self.context.param(name="score", value=self.score)(xml_file)
            for param in self.params:
                self.context.param(param)(xml_file)


class Measure(ComponentBase):
    def __init__(self, name=None, id=None, param=None, getter=None, context=NullMap):
        if isinstance(name, CVParam):
            param = name
            name = param.name
        elif param is None and name is not None:
            param = context.param(name)
        self.name = name
        self.param = param
        if name is not None and id is None:
            id = name
        self.element = _element("Measure", id=sanitize_id(id), name=name)
        context["Measure"][id] = self.element.id
        self.context = context

        if getter is None:
            getter = operator.itemgetter(name)
        self.getter = getter

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            self.context.param(self.param)(xml_file)

    common_measures = ["product ion %s" % s for s in ("m/z", "intensity", "m/z error")]


class FragmentationTable(ComponentBase):
    def __init__(self, measures=None, context=NullMap):
        if measures is None:
            measures = Measure.common_measures
        self.context = context

        self.element = _element("FragmentationTable")

        self.measures = []
        for measure in measures:
            if isinstance(measure, Measure):
                self.measures.append(measure)
            else:
                measure = Measure(context.param(measure), context=context)
                self.measures.append(measure)

    def write(self, xml_file):
        with self.element(xml_file):
            for measure in self.measures:
                measure.write(xml_file)


class SpectrumIdentificationList(ComponentBase):
    def __init__(self, identification_results, id, fragmentation_table=None, context=NullMap):
        self.identification_results = identification_results
        self.fragmentation_table = fragmentation_table
        self.element = _element("SpectrumIdentificationList", xmlns=_xmlns, id=id)
        context["SpectrumIdentificationList"][id] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            if self.fragmentation_table is not None:
                self.fragmentation_table.write(xml_file)
            for identification_result in self.identification_results:
                identification_result.write(xml_file)


class AnalysisData(GenericCollection):
    def __init__(self, identification_lists=tuple(), protein_detection_lists=tuple(), context=NullMap):
        items = list()
        items.extend(identification_lists)
        items.extend(protein_detection_lists)
        super(AnalysisData, self).__init__("AnalysisData", items, context)


class ProteinDetectionList(ComponentBase):
    def __init__(self, ambiguity_groups=None, context=NullMap):
        self.ambiguity_groups = ambiguity_groups
        self.element = _element("ProteinDetectionList")

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for ambiguity_group in self.ambiguity_groups:
                ambiguity_group.write(xml_file)


class PeptideHypothesis(ComponentBase):
    def __init__(self, peptide_evidence_id, spectrum_identification_ids, params=None, context=NullMap):
        self.peptide_evidence_id = peptide_evidence_id
        self.spectrum_identification_ids = spectrum_identification_ids
        self.params = params
        self.context = context
        self.element = _element("PeptideHypothesis", peptideEvidence_ref=peptide_evidence_id)

    def write(self, xml_file):
        with self.element(xml_file):
            for spectrum_identification_id in self.spectrum_identification_ids:
                el = _element(
                    "SpectrumIdentificationItemRef",
                    spectrumIdentificationItem_ref=self.context[
                        "SpectrumIdentificationItem"][spectrum_identification_id])
                el.write(xml_file)
            if self.params is not None:
                for param in ensure_iterable(self.params):
                    self.context.param(param)(xml_file)


class ProteinDetectionHypothesis(ComponentBase):
    def __init__(self, id, db_sequence_id, peptide_hypotheses, score, pass_threshold=True,
                 params=None, context=NullMap):
        self.peptide_hypotheses = peptide_hypotheses
        self.db_sequence_id = db_sequence_id
        self.score = score
        self.pass_threshold = pass_threshold
        self.params = params
        self.context = context
        self.element = _element(
            "ProteinDetectionHypothesis", id=id,
            dBSequence_ref=context["DBSequence"][db_sequence_id],
            passThreshold=pass_threshold)
        context['ProteinDetectionHypothesis'][id] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for peptide_hypothesis in self.peptide_hypotheses:
                peptide_hypothesis.write(xml_file)
            if self.score is not None:
                self.context.param(self.score)(xml_file)
            if self.params is not None:
                for param in ensure_iterable(self.params):
                    self.context.param(param)(xml_file)


class ProteinAmbiguityGroup(ComponentBase):
    def __init__(self, id, protein_hypotheses, params=None, context=NullMap):
        self.protein_hypotheses = protein_hypotheses
        self.params = params
        self.context = context
        self.element = _element(
            "ProteinAmbiguityGroup", id=id)
        context["ProteinAmbiguityGroup"][id] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for protein in self.protein_hypotheses:
                protein.write(xml_file, with_id=True)
            if self.params is not None:
                for param in ensure_iterable(self.params):
                    self.context.param(param)(xml_file)


# --------------------------------------------------
# Meta-collections


class DataCollection(GenericCollection):
    def __init__(self, inputs, analysis_data, context=NullMap):
        super(DataCollection, self).__init__("DataCollection", [inputs, analysis_data], context)


class SequenceCollection(GenericCollection):
    def __init__(self, db_sequences, peptides, peptide_evidence, context=NullMap):
        super(SequenceCollection, self).__init__("SequenceCollection", chain.from_iterable(
            [db_sequences, peptides, peptide_evidence]))


# --------------------------------------------------
# Software Execution Protocol Information


class Enzyme(ComponentBase):
    def __init__(self, name, missed_cleavages=1, id=None, semi_specific=False, site_regexp=None, context=NullMap):
        self.name = name
        if site_regexp is None:
            term = context.term(name)
            try:
                regex_ref = term['has_regexp']
                regex_ent = context.term(regex_ref)
                regex = regex_ent['name']
                site_regexp = regex
            except Exception:
                pass
        self.site_regexp = site_regexp
        self.element = _element(
            "Enzyme", semiSpecific=semi_specific, missedCleavages=missed_cleavages,
            id=id)
        context["Enzyme"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            if self.site_regexp is not None:
                regex = _element("SiteRegexp").element()
                regex.text = etree.CDATA(self.site_regexp)
                xml_file.write(regex)
            with element(xml_file, "EnzymeName"):
                self.context.param(self.name)(xml_file)


class _Tolerance(ComponentBase):

    def __init__(self, low, high=None, unit="parts per million", context=NullMap):
        if isinstance(low, NumberBase):
            low = CVParam(
                accession="MS:1001413", ref="PSI-MS", unitCvRef="UO", unitName=unit,
                unitAccession=common_units[unit], value=low,
                name="search tolerance minus value")
        if high is None:
            high = CVParam(
                accession="MS:1001412", ref="PSI-MS", unitCvRef="UO", unitName=unit,
                unitAccession=common_units[unit], value=low.value,
                name="search tolerance plus value")
        elif isinstance(high, NumberBase):
            high = CVParam(
                accession="MS:1001412", ref="PSI-MS", unitCvRef="UO", unitName=unit,
                unitAccession=common_units[unit], value=high,
                name="search tolerance plus value")

        self.low = low
        self.high = high

    def write(self, xml_file):
        with element(xml_file, self.tag_name):
            self.low.write(xml_file)
            self.high.write(xml_file)


class FragmentTolerance(_Tolerance):
    tag_name = "FragmentTolerance"


class ParentTolerance(_Tolerance):
    tag_name = "ParentTolerance"


class Threshold(ComponentBase):
    no_threshold = CVParam(accession="MS:1001494", ref="PSI-MS", name="no threshold")

    def __init__(self, name=None, context=NullMap):
        if name is None:
            name = self.no_threshold
        self.name = name
        self.context = context

    def write(self, xml_file):
        with element(xml_file, "Threshold"):
            self.context.param(self.name)(xml_file)


class SpectrumIdentificationProtocol(ComponentBase):
    def __init__(self, search_type, analysis_software_id=1, id=1, additional_search_params=tuple(),
                 modification_params=tuple(), enzymes=tuple(), fragment_tolerance=None, parent_tolerance=None,
                 threshold=None, context=NullMap):
        if threshold is None:
            threshold = Threshold(context=context)
        self.parent_tolerance = parent_tolerance
        self.fragment_tolerance = fragment_tolerance
        self.threshold = threshold
        self.enzymes = enzymes
        temp = []
        for mod in modification_params:
            if isinstance(mod, SearchModification):
                temp.append(mod)
            else:
                temp.append(
                    SearchModification(
                        context=context, **mod))
        modification_params = temp
        self.modification_params = modification_params
        self.additional_search_params = additional_search_params
        self.search_type = search_type

        self.element = _element(
            "SpectrumIdentificationProtocol", id=id,
            analysisSoftware_ref=context['AnalysisSoftware'][analysis_software_id])
        context["SpectrumIdentificationProtocol"][id] = self.element.id

        self.context = context

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            with element(xml_file, "SearchType"):
                self.context.param(self.search_type)(xml_file)
            if self.additional_search_params:
                with element(xml_file, "AdditionalSearchParams"):
                    for search_param in self.additional_search_params:
                        self.contex.param(search_param)(xml_file)
            with element(xml_file, "ModificationParams"):
                for mod in self.modification_params:
                    mod.write(xml_file)
            with element(xml_file, "Enzymes"):
                for enzyme in self.enzymes:
                    enzyme.write(xml_file)
            if self.fragment_tolerance is not None:
                self.fragment_tolerance.write(xml_file)
            if self.parent_tolerance is not None:
                self.parent_tolerance.write(xml_file)
            self.threshold.write(xml_file)


class SearchModification(ComponentBase):
    def __init__(self, mass_delta, fixed, residues, specificity=None,
                 params=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        if specificity is not None:
            if not isinstance(specificity, (tuple, list)):
                specificity = [specificity]
        params.extend(kwargs.items())
        self.params = params
        self.mass_delta = mass_delta
        self.fixed = fixed
        self.residues = ''.join(residues)
        self.specificity = specificity
        self.context = context
        self.element = _element(
            "SearchModification", fixedMod=fixed, massDelta=mass_delta,
            residues=self.residues)

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            for param in self.params:
                self.context.param(param)(xml_file)
            if self.specificity is not None:
                with _element("SpecificityRules"):
                    for param in self.specificity:
                        self.context.param(param)(xml_file)


class ProteinDetectionProtocol(ComponentBase):
    def __init__(self, id=1, analysis_software_id=1, threshold=None, context=NullMap):
        if threshold is None:
            threshold = Threshold(context=context)
        self.analysis_software_id = analysis_software_id
        self.element = _element(
            "ProteinDetectionProtocol", id=id,
            analysisSoftware_ref=context["AnalysisSoftware"][analysis_software_id])
        context["ProteinDetectionProtocol"][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            self.threshold.write(xml_file)


class AnalysisProtocolCollection(GenericCollection):
    def __init__(self, spectrum_identification_protocols=tuple(),
                 protein_detection_protocols=tuple(), context=NullMap):
        items = list()
        items.extend(spectrum_identification_protocols)
        items.extend(protein_detection_protocols)
        super(AnalysisProtocolCollection, self).__init__(self, items, context)


# --------------------------------------------------
# Analysis Collection - Data-to-Analysis

class SpectrumIdentification(ComponentBase):
    def __init__(self, spectra_data_ids_used=None, search_database_ids_used=None, spectrum_identification_list_id=1,
                 spectrum_identification_protocol_id=1, id=1, context=NullMap):
        self.spectra_data_ids_used = [context["SpectraData"][x] for x in (spectra_data_ids_used or [])]
        self.search_database_ids_used = [context["SearchDatabase"][x] for x in (search_database_ids_used or [])]

        self.element = _element(
            "SpectrumIdentification", id=id,
            spectrumIdentificationList_ref=context["SpectrumIdentificationList"][
                spectrum_identification_list_id],
            spectrumIdentificationProtocol_ref=context["SpectrumIdentificationProtocol"][
                spectrum_identification_protocol_id])
        context["SpectrumIdentification"] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for spectra_data_id in self.spectra_data_ids_used:
                _element("InputSpectra", spectraData_ref=spectra_data_id).write(xml_file)
            for search_database_id in self.search_database_ids_used:
                _element("SearchDatabaseRef", searchDatabase_ref=search_database_id).write(xml_file)


# --------------------------------------------------
# Misc. Providence Management


DEFAULT_CONTACT_ID = "PERSON_DOC_OWNER"
DEFAULT_ORGANIZATION_ID = "ORG_DOC_OWNER"


class CVList(ComponentBase):
    def __init__(self, cv_list=None, context=NullMap):
        if cv_list is None:
            cv_list = default_cv_list
        self.cv_list = cv_list

    def write(self, xml_file):
        with element(xml_file, 'cvList'):
            for member in self.cv_list:
                xml_file.write(member.element(with_id=True))


class AnalysisSoftware(ComponentBase):
    def __init__(self, name, id=1, version=None, uri=None, contact=DEFAULT_CONTACT_ID, context=NullMap, **kwargs):
        self.name = name
        self.version = version
        self.uri = uri
        self.contact = contact
        self.kwargs = kwargs
        self.element = _element("AnalysisSoftware", id=id, name=self.name, version=self.version, uri=self.uri)
        context["AnalysisSoftware"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            with element(xml_file, "ContactRole", contact_ref=self.contact):
                with element(xml_file, "Role"):
                    xml_file.write(CVParam(accession="MS:1001267", name="software vendor", cvRef="PSI-MS").element())
            with element(xml_file, "SoftwareName"):
                self.context.param(name=self.name)(xml_file)


class Provider(ComponentBase):
    def __init__(self, id="PROVIDER", contact=DEFAULT_CONTACT_ID, context=NullMap):
        self.id = id
        self.contact = contact

    def write(self, xml_file):
        with element(xml_file, "Provider", id=self.id, xmlns=_xmlns):
            with element(xml_file, "ContactRole", contact_ref=self.contact):
                with element(xml_file, "Role"):
                    xml_file.write(CVParam(accession="MS:1001271", name="researcher", cvRef="PSI-MS").element())


class Person(ComponentBase):
    def __init__(self, first_name='first_name', last_name='last_name', id=DEFAULT_CONTACT_ID,
                 affiliation=DEFAULT_ORGANIZATION_ID, context=NullMap):
        self.first_name = first_name
        self.last_name = last_name
        self.id = id
        self.affiliation = affiliation
        self.element = _element("Person", firstName=first_name, last_name=last_name, id=id)
        context["Person"][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            element(xml_file, 'Affiliation', organization_ref=self.affiliation)


class Organization(ComponentBase):
    def __init__(self, name="name", id=DEFAULT_ORGANIZATION_ID, context=NullMap):
        self.name = name
        self.id = id
        self.element = _element("Organization", name=name, id=id)
        context["Organization"][id] = self.id

    def write(self, xml_file):
        xml_file.write(self.element.element())


DEFAULT_PERSON = Person()
DEFAULT_ORGANIZATION = Organization()


class AuditCollection(ComponentBase):
    def __init__(self, persons=None, organizations=None, context=NullMap):
        if persons is None:
            persons = (DEFAULT_PERSON,)
        if organizations is None:
            organizations = (DEFAULT_ORGANIZATION,)
        self.persons = persons
        self.organizations = organizations

    def write(self, xml_file):
        with element(xml_file, "AuditCollection", xmlns=_xmlns):
            for person in self.persons:
                person.write(xml_file)
            for organization in self.organizations:
                organization.write(xml_file)
