import warnings
import operator
import re

from collections import Mapping

from datetime import datetime
from numbers import Number as NumberBase
from itertools import chain

from ..xml import (
    _element, element, TagBase,
    CVParam, UserParam, CV,
    ProvidedCV, sanitize_id)
from ..document import (
    ComponentBase as _ComponentBase, NullMap, ComponentDispatcherBase,
    ParameterContainer)

from .utils import ensure_iterable

from lxml import etree


AUTO = object()


class MzIdentML(TagBase):
    v1_1_0_type_attrs = {
        "xmlns": "http://psidev.info/psi/pi/mzIdentML/1.1",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://psidev.info/psi/pi/mzIdentML/1.1 ../../schema/mzIdentML1.1.0.xsd"
    }

    v1_2_0_type_attrs = {
        "xmlns": "http://psidev.info/psi/pi/mzIdentML/1.2",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://psidev.info/psi/pi/mzIdentML/1.2 ../../schema/mzIdentML1.2.0.xsd"
    }

    def __init__(self, **attrs):
        attrs.setdefault('creationDate', datetime.utcnow().isoformat())
        attrs.setdefault("id", 0)
        attrs.setdefault("version", '1.1.0')
        version = attrs['version']
        if version == '1.1.0':
            self.type_attrs = self.v1_1_0_type_attrs
        elif version == '1.2.0':
            self.type_attrs = self.v1_2_0_type_attrs

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
    CV(
        id="PSI-MS",
        uri=("http://psidev.cvs.sourceforge.net/viewvc/*checkout*/psidev"
             "/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"),
        full_name="PSI-MS"),
    CV(
        id="UO",
        uri="http://ontologies.berkeleybop.org/uo.obo",
        full_name="UNIT-ONTOLOGY"),
    ProvidedCV(id="UNIMOD", uri="http://www.unimod.org/obo/unimod.obo", full_name="UNIMOD", converter=_unimod_converter)
]


common_units = {
    "parts per million": "UO:0000169",
    "dalton": "UO:0000221"
}


_xmlns = "http://psidev.info/psi/pi/mzIdentML/1.2"


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
    def __init__(self, location, file_format, id=None, external_format=None,
                 params=None, context=NullMap, **kwargs):
        self.params = self.prepare_params(params, **kwargs)
        self.external_format = external_format
        self.file_format = file_format
        self.element = _element("SourceFile", location=location, id=id)
        self.context = context
        context["SourceFile"][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            with element(xml_file, "FileFormat"):
                self.context.param(self.file_format)(xml_file)
            if self.external_format is not None:
                with element(xml_file, "ExternalFormatDocumentation"):
                    xml_file.write(str(self.external_format))
            self.write_params(xml_file)


class SearchDatabase(ComponentBase):
    def __init__(self, name, file_format, location=None, id=None, external_format=None,
                 params=None, context=NullMap, **kwargs):
        self.external_format = external_format
        self.params = self.prepare_params(params, **kwargs)
        self.location = location
        self.file_format = file_format
        self.element = _element("SearchDatabase", location=location, name=name, id=id)
        context["SearchDatabase"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            with element(xml_file, "FileFormat"):
                self.write_params(xml_file, self.prepare_params(self.file_format))
            with element(xml_file, "DatabaseName"):
                UserParam(name=self.name).write(xml_file)
            if self.external_format is not None:
                with element(xml_file, "ExternalFormatDocumentation"):
                    xml_file.write(str(self.external_format))
            self.write_params(xml_file)


class SpectraData(ComponentBase):
    def __init__(self, location, file_format, spectrum_id_format, id=None, params=None, context=NullMap, **kwargs):
        self.params = self.prepare_params(params, **kwargs)
        self.file_format = file_format
        self.spectrum_id_format = spectrum_id_format
        self.element = _element("SpectraData", id=id, location=location)
        context['SpectraData'][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            with element(xml_file, "FileFormat"):
                self.write_params(xml_file, self.prepare_params(self.file_format))
            with element(xml_file, "SpectrumIDFormat"):
                self.context.param(self.spectrum_id_format)(xml_file)
            self.write_params(xml_file)


class Inputs(GenericCollection):
    def __init__(self, source_files=tuple(), search_databases=tuple(), spectra_data=tuple(), context=NullMap):
        items = list()
        items.extend(source_files)
        items.extend(search_databases)
        items.extend(spectra_data)
        super(Inputs, self).__init__("Inputs", items, context=context)

# --------------------------------------------------
# Search Database Content


class DBSequence(ComponentBase):
    def __init__(self, accession, sequence=None, id=None, search_database_id=1, params=None, context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        self.params = params
        self.sequence = sequence
        self.search_database_ref = context['SearchDatabase'][search_database_id]
        self.element = _element(
            "DBSequence", accession=accession, id=id,
            searchDatabase_ref=self.search_database_ref)
        if sequence is not None:
            self.element.attrs["length"] = len(sequence)

        context["DBSequence"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        protein = self.sequence
        with self.element.element(xml_file, with_id=True):
            if self.sequence is not None:
                with element(xml_file, "Seq"):
                    xml_file.write(protein)
            self.write_params(xml_file)


class Peptide(ComponentBase):
    def __init__(self, peptide_sequence, id, modifications=None, params=None, context=NullMap, **kwargs):
        if modifications is None:
            modifications = []
        params = self.prepare_params(params, **kwargs)
        self.context = context
        self.peptide_sequence = peptide_sequence
        self.modifications = [Modification(context=context, **mod)
                              if not isinstance(mod, Modification) else mod for mod in modifications]
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
            self.write_params(xml_file)


class ModificationDescriptionBase(object):
    UNKNOWN_MODIFICATION_ACCESSION = "MS:1001460"

    def _resolve_name_accession(self, name):
        try:
            mod, cv = self.context.term(name, include_source=True)
            self.name = mod["name"]
            self.accession = mod['id']
            self.known = True
            self.reference = cv.id
        except KeyError:
            self.known = False
            self.name = name
            self.accession = self.UNKNOWN_MODIFICATION_ACCESSION
            cv = self.context.get_vocabulary("PSI-MS")
            if cv is None:
                self.reference = 'PSI-MS'
            else:
                self.reference = cv.id

    def _format_identity(self, xml_file):
        if self.known:
            self.context.param(
                name=self.name, accession=self.accession,
                ref=self.reference)(xml_file)
        else:
            self.context.param(
                name="unknown modification",
                accession=self.accession,
                value=self.name,
                ref=self.reference)(xml_file)


class Modification(ComponentBase, ModificationDescriptionBase):

    def __init__(self, monoisotopic_mass_delta=None, location=None, name=None,
                 id=None, params=None, context=NullMap, **kwargs):
        self.context = context
        params = self.prepare_params(params, **kwargs)
        if id is None and name is not None:
            self._resolve_name_accession(name)
        elif name is None and id is not None:
            self._resolve_name_accession(id)
        else:
            warnings.warn("Unknown modification saved: %s" % monoisotopic_mass_delta)
            self.name = name
            self.accession = id
            self.known = False

        self.element = _element(
            "Modification", monoisotopicMassDelta=monoisotopic_mass_delta,
            location=location)
        self.params = params

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            if self.accession is not None:
                self._format_identity(xml_file)
            self.write_params(xml_file)


class SubstitutionModification(ComponentBase):
    def __init__(self, original_residue, replacement_residue,
                 monoisotopic_mass_delta=None, location=None,
                 context=NullMap):
        self.original_residue = original_residue
        self.replacement_residue = replacement_residue
        self.monoisotopic_mass_delta = monoisotopic_mass_delta
        self.location = location
        self.element = _element(
            "SubstitutionModification", originalResidue=self.original_residue,
            replacementResidue=self.replacement_residue)
        if self.monoisotopic_mass_delta is not None:
            self.element.attrs['monoisotopicMassDelta'] = self.monoisotopic_mass_delta
        if self.location is not None:
            self.element.attrs['location'] = self.location
        self.context = context

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            pass


class PeptideEvidence(ComponentBase):
    def __init__(self, peptide_id, db_sequence_id, id, start_position, end_position,
                 is_decoy=False, pre=None, post=None, params=None, frame=None,
                 translation_table_id=None, context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        self.params = params
        self.context = context
        self.peptide_id = peptide_id
        self.db_sequence_id = db_sequence_id
        self.translation_table_id = translation_table_id
        self.frame = frame
        self.element = _element(
            "PeptideEvidence", isDecoy=is_decoy, start=start_position,
            end=end_position, peptide_ref=context["Peptide"][peptide_id],
            dBSequence_ref=context['DBSequence'][db_sequence_id],
            pre=pre, post=post, id=id, frame=frame)
        if self.translation_table_id is not None:
            self.element.attrs['translationTable_ref'] = self.context['TranslationTable'][self.translation_table_id]
        self.context["PeptideEvidence"][id] = self.element.id

    def write(self, xml_file):
        if self.params:
            with self.element(xml_file, with_id=True):
                self.write_params(xml_file)
        else:
            xml_file.write(self.element(with_id=True))


# --------------------------------------------------
# Identification Information


class SpectrumIdentificationResult(ComponentBase):
    def __init__(self, spectra_data_id, spectrum_id, id=None, identifications=None, params=None,
                 context=NullMap, **kwargs):
        if identifications is None:
            identifications = []
        self.params = self.prepare_params(params, **kwargs)
        self.identifications = identifications
        self.element = _element(
            "SpectrumIdentificationResult", spectraData_ref=context["SpectraData"][spectra_data_id],
            spectrumID=spectrum_id, id=id)
        self.context = context
        self.context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for item in self.identifications:
                item.write(xml_file)
            self.write_params(xml_file)


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
    def __init__(self, experimental_mass_to_charge,
                 charge_state, peptide_id, peptide_evidence_ids, id, score=None,
                 ion_types=None, params=None, pass_threshold=True, rank=1,
                 calculated_mass_to_charge=None, calculated_pi=None,
                 name=None, mass_table_id=None, sample_id=None,
                 context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        self.peptide_evidence_refs = [
            context["PeptideEvidence"][peptide_evidence_id]
            for peptide_evidence_id in ensure_iterable(peptide_evidence_ids)]
        self.params = params
        self.score = score
        self.rank = rank
        self.element = _element(
            "SpectrumIdentificationItem", chargeState=charge_state,
            experimentalMassToCharge=experimental_mass_to_charge, id=id, passThreshold=pass_threshold,
            peptide_ref=context['Peptide'][peptide_id], rank=self.rank
        )
        self.element.attrs['calculatedMassToCharge'] = calculated_mass_to_charge
        self.element.attrs['calculatedPI'] = calculated_pi
        if sample_id is not None:
            self.element.attrs['sample_ref'] = context['Sample'][sample_id]
        if mass_table_id is not None:
            self.element.attrs['massTable_ref'] = context['MassTable'][sample_id]
        context['SpectrumIdentificationItem'][id] = self.element.id
        self.context = context
        self.ion_types = self.prepare_ion_types(ion_types)

    def prepare_ion_types(self, ion_types):
        mappings = []
        if ion_types is not None:
            if isinstance(ion_types, (list, tuple)):
                try:
                    if isinstance(ion_types[0], IonType):
                        return ion_types
                except IndexError:
                    return mappings
            elif isinstance(ion_types, Mapping):
                ion_types = list(ion_types.items())
            for series, measures in ion_types:
                measures_ = {}
                for measure, values in measures.items():
                    if measure in ("indices", "charge_state"):
                        continue
                    measures_[measure] = values

                it = IonType(series=IonType.guess_ion_type(series), indices=measures['indices'],
                             charge_state=measures.get('charge_state', 1), measures=measures_,
                             context=self.context)
                mappings.append(it)
        return mappings

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for peptide_evidence_ref in self.peptide_evidence_refs:
                _element(
                    "PeptideEvidenceRef",
                    peptideEvidence_ref=peptide_evidence_ref).write(
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
            self.write_params(xml_file)


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


class MassTable(ComponentBase):
    def __init__(self, id, ms_level, residues=None, ambiguous_residues=None,
                 name=None, params=None, context=NullMap, **kwargs):
        if residues is None:
            residues = []
        if ambiguous_residues is None:
            ambiguous_residues = []

        self.context = context
        self.residues = [Residue.ensure(r, context=context) for r in ensure_iterable(residues)]
        self.ambiguous_residues = [AmbiguousResidue.ensure(r, context=context)
                                   for r in ensure_iterable(ambiguous_residues)]
        self.name = name
        self.ms_level = list(map(lambda x: str(int(x)), ensure_iterable(ms_level)))
        self.element = _element("MassTable", id=id, msLevel=' '.join(self.ms_level))
        if self.name is not None:
            self.element.attrs['name'] = str(self.name)
        self.context['MassTable'][id] = self.element.id
        self.params = self.prepare_params(params, **kwargs)

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for residue in self.residues:
                residue.write(xml_file)
            for residue in self.ambiguous_residues:
                residue.write(xml_file)
            self.write_params(xml_file)


class Residue(ComponentBase):
    def __init__(self, mass, code, context=NullMap):
        self.mass = float(mass)
        self.code = str(code)
        self.element = _element("Residue", mass=self.mass, code=self.code)

    def write(self, xml_file):
        self.element.write(xml_file, with_id=False)


class AmbiguousResidue(ComponentBase):
    def __init__(self, code, params=None, context=NullMap, **kwargs):
        self.context = context
        self.code = str(code)
        self.params = self.prepare_params(params, **kwargs)
        self.element = _element("AmbiguousResidue", code=self.code)

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            self.write_params(xml_file)


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
    def __init__(self, ambiguity_groups=None, count=AUTO, id=1, params=None, context=NullMap, **kwargs):
        self.ambiguity_groups = ambiguity_groups
        self.element = _element("ProteinDetectionList", id=id)
        self.count = count
        self.params = self.prepare_params(params, **kwargs)
        self.context = context
        self.context['ProteinDetectionList'][id] = self.element.id

    def _count_protein_groups(self):
        count = 0
        for pg in self.ambiguity_groups:
            if pg.pass_threshold:
                count += 1
        return count

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for ambiguity_group in self.ambiguity_groups:
                ambiguity_group.write(xml_file)
            if self.count is AUTO:
                count = self._count_protein_groups()
                if count > 0:
                    self.context.param("count of identified proteins", count)(xml_file)
            elif self.count is not None:
                self.context.param("count of identified proteins", self.count)(xml_file)
            self.write_params(xml_file)


class PeptideHypothesis(ComponentBase):
    def __init__(self, peptide_evidence_id, spectrum_identification_ids, params=None,
                 context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        self.peptide_evidence_id = peptide_evidence_id
        self.spectrum_identification_ids = spectrum_identification_ids
        self.params = params
        self.context = context
        self.element = _element("PeptideHypothesis",
                                peptideEvidence_ref=self.context['PeptideEvidence'][peptide_evidence_id])

    def write(self, xml_file):
        with self.element(xml_file):
            for spectrum_identification_id in self.spectrum_identification_ids:
                el = _element(
                    "SpectrumIdentificationItemRef",
                    spectrumIdentificationItem_ref=self.context[
                        "SpectrumIdentificationItem"][spectrum_identification_id])
                el.write(xml_file)
            self.write_params(xml_file)


class ProteinDetectionHypothesis(ComponentBase):
    def __init__(self, id, db_sequence_id, peptide_hypotheses, pass_threshold=True,
                 leading=True, params=None, name=None, context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        self.db_sequence_id = db_sequence_id
        self.pass_threshold = pass_threshold
        self.leading = leading
        self.params = params
        self.context = context
        self.peptide_hypotheses = self._coerce_peptide_hypotheses(peptide_hypotheses)
        self.element = _element(
            "ProteinDetectionHypothesis", id=id,
            dBSequence_ref=context["DBSequence"][db_sequence_id],
            passThreshold=pass_threshold)
        if name is not None:
            self.element.attrs['name'] = name
        self.context['ProteinDetectionHypothesis'][id] = self.element.id

    def _coerce_peptide_hypotheses(self, peptides):
        out = []
        for peptide in ensure_iterable(peptides):
            if isinstance(peptide, Mapping):
                peptide = PeptideHypothesis(context=self.context, **peptide)
            out.append(peptide)
        return out

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for peptide_hypothesis in self.peptide_hypotheses:
                peptide_hypothesis.write(xml_file)
            if self.leading is None:
                pass
            elif self.leading:
                self.context.param("leading protein")(xml_file)
            else:
                self.context.param("non-leading protein")(xml_file)
            self.write_params(xml_file)


class ProteinAmbiguityGroup(ComponentBase):
    def __init__(self, id, protein_detection_hypotheses, pass_threshold=True, params=None,
                 context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        self.protein_detection_hypotheses = protein_detection_hypotheses
        self.params = params
        self.pass_threshold = pass_threshold
        self.context = context
        self.element = _element(
            "ProteinAmbiguityGroup", id=id)
        self.context["ProteinAmbiguityGroup"][id] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for protein in self.protein_detection_hypotheses:
                protein.write(xml_file)
            if self.pass_threshold is not None:
                self.context.param(name="protein group passes threshold",
                                   value=self.pass_threshold)(xml_file)
            self.write_params(xml_file)


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
    def __init__(self, name, missed_cleavages=1, id=None, semi_specific=False, site_regexp=None,
                 min_distance=None, n_term_gain=None, c_term_gain=None, params=None, context=NullMap,
                 **kwargs):
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
        self.params = self.prepare_params(params, **kwargs)
        self.min_distance = min_distance
        if min_distance is not None:
            self.element.attrs['minDistance'] = int(min_distance)
        self.n_term_gain = n_term_gain
        if n_term_gain is not None:
            self.element.attrs['nTermGain'] = str(n_term_gain)
        self.c_term_gain = c_term_gain
        if c_term_gain is not None:
            self.element.attrs['cTermGain'] = str(c_term_gain)

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            if self.site_regexp is not None:
                regex = _element("SiteRegexp").element()
                regex.text = etree.CDATA(self.site_regexp)
                xml_file.write(regex)
            with element(xml_file, "EnzymeName"):
                self.context.param(self.name)(xml_file)
            self.write_params(xml_file)


class Enzymes(ComponentBase):
    def __init__(self, enzymes=None, independent=None, context=NullMap):
        self.independent = independent
        self.context = context
        self.enzymes = self._coerce_enzymes(enzymes)
        self.element = _element("Enzymes")
        if self.independent is not None:
            self.element.attrs['independent'] = bool(self.independent)

    def _coerce_enzymes(self, enzymes):
        temp = []
        for enz in ensure_iterable(enzymes):
            if not isinstance(enz, Enzyme):
                enz = Enzyme(context=self.context, **enz)
            temp.append(enz)
        return temp

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            for enzyme in self.enzymes:
                enzyme.write(xml_file)


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

    def __iter__(self):
        yield self.low.value
        yield self.high.value


class FragmentTolerance(_Tolerance):
    tag_name = "FragmentTolerance"


class ParentTolerance(_Tolerance):
    tag_name = "ParentTolerance"


class Threshold(ComponentBase):
    no_threshold = CVParam(accession="MS:1001494", ref="PSI-MS", name="no threshold")

    def __init__(self, params=None, context=NullMap, **kwargs):
        params = self.prepare_params(ensure_iterable(params), **kwargs)
        self.params = params
        self.context = context

    def write(self, xml_file):
        with element(xml_file, "Threshold"):
            if not self.params:
                self.no_threshold(xml_file)
            else:
                self.write_params(xml_file)


class SpectrumIdentificationProtocol(ComponentBase):
    def __init__(self, search_type, analysis_software_id=1, id=1, additional_search_params=tuple(),
                 modification_params=tuple(), enzymes=tuple(), fragment_tolerance=None, parent_tolerance=None,
                 threshold=None, filters=None, mass_tables=None, context=NullMap):
        self.context = context
        if threshold is None:
            threshold = Threshold(context=context)
        elif not isinstance(threshold, Threshold):
            threshold = Threshold(threshold, context=context)
        if not isinstance(parent_tolerance, ParentTolerance):
            if isinstance(parent_tolerance, NumberBase):
                parent_tolerance = ParentTolerance(parent_tolerance)
            elif isinstance(parent_tolerance, (tuple, list)):
                parent_tolerance = ParentTolerance(*parent_tolerance)
            elif parent_tolerance is None:
                pass
            else:
                raise ValueError("Cannot infer ParentTolerance from %r" % (parent_tolerance,))
        if not isinstance(fragment_tolerance, FragmentTolerance):
            if isinstance(fragment_tolerance, NumberBase):
                fragment_tolerance = FragmentTolerance(fragment_tolerance)
            elif isinstance(fragment_tolerance, (tuple, list)):
                fragment_tolerance = FragmentTolerance(*fragment_tolerance)
            elif fragment_tolerance is None:
                pass
            else:
                raise ValueError("Cannot infer FragmentTolerance from %r" % (fragment_tolerance,))
        if not isinstance(enzymes, Enzymes):
            enzymes = Enzymes(ensure_iterable(enzymes), context=context)
        self.parent_tolerance = parent_tolerance
        self.fragment_tolerance = fragment_tolerance
        self.threshold = threshold
        self.enzymes = enzymes
        temp = []
        for mod in ensure_iterable(modification_params):
            if isinstance(mod, SearchModification):
                temp.append(mod)
            else:
                temp.append(
                    SearchModification(
                        context=context, **mod))
        modification_params = temp
        self.modification_params = modification_params
        self.additional_search_params = self.prepare_params(additional_search_params)
        self.search_type = search_type
        temp = []
        for filt in ensure_iterable(filters):
            if isinstance(filt, Filter):
                temp.append(filt)
            else:
                temp.append(Filter(context=context, **filt))
        filters = temp
        self.filters = filters
        if mass_tables is None:
            mass_tables = []
        else:
            mass_tables = [MassTable.ensure(table, context=context) for table in ensure_iterable(mass_tables)]
        self.mass_tables = mass_tables
        self.element = _element(
            "SpectrumIdentificationProtocol", id=id,
            analysisSoftware_ref=context['AnalysisSoftware'][analysis_software_id])
        self.context["SpectrumIdentificationProtocol"][id] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            with element(xml_file, "SearchType"):
                self.context.param(self.search_type)(xml_file)
            if self.additional_search_params:
                with element(xml_file, "AdditionalSearchParams"):
                    self.write_params(xml_file, self.additional_search_params)
            with element(xml_file, "ModificationParams"):
                for mod in self.modification_params:
                    mod.write(xml_file)
            self.enzymes.write(xml_file)
            for mass_table in self.mass_tables:
                mass_table.write(xml_file)
            if self.fragment_tolerance is not None:
                self.fragment_tolerance.write(xml_file)
            if self.parent_tolerance is not None:
                self.parent_tolerance.write(xml_file)
            self.threshold.write(xml_file)
            if self.filters:
                with element(xml_file, "DatabaseFilters"):
                    for filt in self.filters:
                        filt.write(xml_file)


class Filter(ComponentBase):
    def __init__(self, filter_type, include=None, exclude=None, context=NullMap):
        self.filter_type = filter_type
        self.include = include
        self.exclude = exclude
        self.context = context
        self.element = _element("Filter")

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            with element(xml_file, "FilterType"):
                self.context.param(self.filter_type)(xml_file)
            if self.include:
                with element(xml_file, "Include"):
                    self.write_params(xml_file, self.prepare_params(self.include))
            if self.exclude:
                with element(xml_file, "Exclude"):
                    self.write_params(xml_file, self.prepare_params(self.exclude))


class SpecificityRules(ParameterContainer):
    def __init__(self, params=None, context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        super(SpecificityRules, self).__init__("SpecificityRules", params, context=context)


class SearchModification(ComponentBase, ModificationDescriptionBase):
    def __init__(self, mass_delta, fixed, residues, name=None,
                 specificity=None, params=None, context=NullMap,
                 **kwargs):
        self.context = context
        if specificity is not None:
            if not isinstance(specificity, (tuple, list)):
                specificity = [specificity]
            if not isinstance(specificity[0], SpecificityRules):
                specificity = [
                    SpecificityRules(s, context=context) for s in specificity]

        if name is not None:
            self._resolve_name_accession(name)
        else:
            self.name = None
            self.accession = None
            self.reference = None
            self.known = None

        self.params = self.prepare_params(params, **kwargs)
        self.mass_delta = mass_delta
        self.fixed = fixed
        self.residues = ''.join(residues)
        self.specificity = specificity
        self.element = _element(
            "SearchModification", fixedMod=fixed, massDelta=mass_delta,
            residues=self.residues)

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            if self.name is not None:
                self._format_identity(xml_file)
            self.write_params(xml_file)
            if self.specificity is not None:
                self.specificity.write(xml_file)


class ProteinDetectionProtocol(ComponentBase):
    def __init__(self, id=1, params=None, analysis_software_id=1, threshold=None,
                 context=NullMap, **kwargs):
        if threshold is None:
            threshold = Threshold(context=context)
        elif isinstance(threshold, (list, tuple)):
            threshold = Threshold(threshold, context=context)
        params = self.prepare_params(params, **kwargs)
        self.context = context
        self.threshold = threshold
        self.params = params
        self.analysis_software_id = analysis_software_id
        self.element = _element(
            "ProteinDetectionProtocol", id=id,
            analysisSoftware_ref=context["AnalysisSoftware"][analysis_software_id])
        self.context["ProteinDetectionProtocol"][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            self.threshold.write(xml_file)
            if self.params:
                with element(xml_file, "AnalysisParams"):
                    self.write_params(xml_file)


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
        self.context = context
        context["SpectrumIdentification"] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for spectra_data_id in self.spectra_data_ids_used:
                _element("InputSpectra", spectraData_ref=spectra_data_id).write(xml_file)
            for search_database_id in self.search_database_ids_used:
                _element("SearchDatabaseRef", searchDatabase_ref=search_database_id).write(xml_file)


class ProteinDetection(ComponentBase):
    def __init__(self, spectrum_identification_ids_used, protein_detection_list_id=1,
                 protein_detection_protocol_id=1, id=1, context=NullMap):
        self.spectrum_identification_ids_used = [context["SpectrumIdentificationList"][x]
                                                 for x in (spectrum_identification_ids_used or [])]
        self.protein_detection_list_id = protein_detection_list_id
        self.protein_detection_protocol_id = protein_detection_protocol_id
        self.context = context
        self.element = _element(
            "ProteinDetection", id=id,
            proteinDetectionProtocol_ref=context['ProteinDetectionProtocol'][protein_detection_protocol_id],
            proteinDetectionList_ref=context['ProteinDetectionList'][protein_detection_list_id])

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            for sid in self.spectrum_identification_ids_used:
                _element("InputSpectrumIdentifications",
                         spectrumIdentificationList_ref=sid).write(xml_file)


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
                tag = _element(
                    "cv", id=member.id, fullName=member.full_name,
                    uri=member.uri)
                if member.version is not None:
                    tag.attrs['version'] = member.version
                if member.options:
                    tag.attrs.update(member.options)
                xml_file.write(tag.element(with_id=True))

    def __iter__(self):
        return iter(self.cv_list)


class AnalysisSoftware(ComponentBase):
    def __init__(self, name, id=1, version=None, uri=None, contact=DEFAULT_CONTACT_ID,
                 role='software vendor', customization=None, context=NullMap, **kwargs):
        self.name = name
        self.version = version
        self.uri = uri
        self.contact = contact
        self.role = role
        self.kwargs = kwargs
        self.element = _element("AnalysisSoftware", id=id, name=self.name, version=self.version, uri=self.uri)
        self.context = context
        self.context["AnalysisSoftware"][id] = self.element.id
        self.customization = customization

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            with element(xml_file, "ContactRole", contact_ref=self.contact):
                with element(xml_file, "Role"):
                    self.write_params(xml_file, self.prepare_params(self.role))
            with element(xml_file, "SoftwareName"):
                name_param = self.context.param(name=self.name)
                # if the software name is not a controlled vocabulary term, specify it using
                # the standard "unreleased custom software tool" term-value pair
                if isinstance(name_param, UserParam):
                    name_param = self.context.param("MS:1000799", value=self.name)
                name_param(xml_file)
            if self.customization is not None:
                with element(xml_file, "Customizations"):
                    xml_file.write('\n'.join(ensure_iterable(self.customization)))


class Provider(ComponentBase):
    def __init__(self, id="PROVIDER", role='researcher', contact=DEFAULT_CONTACT_ID, context=NullMap):
        self.id = id
        self.contact = contact
        self.role = role
        self.context = context
        self.element = _element('Provider', id=id, xmlns=_xmlns)
        self.context['Provider'][id] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            with element(xml_file, "ContactRole", contact_ref=self.contact):
                with element(xml_file, "Role"):
                    self.write_params(xml_file, self.prepare_params(self.role))


class Person(ComponentBase):
    def __init__(self, first_name=None, last_name=None, middle_initial=None, id=DEFAULT_CONTACT_ID,
                 affiliation=DEFAULT_ORGANIZATION_ID, params=None, context=NullMap, **kwargs):
        self.params = self.prepare_params(params, **kwargs)
        self.first_name = first_name
        self.middle_initial = middle_initial
        self.last_name = last_name
        self.id = id
        self.element = _element(
            "Person", firstName=first_name, lastName=last_name,
            midInitials=middle_initial, id=id)
        self.context = context
        self.context["Person"][id] = self.element.id
        self.affiliation = self.context["Organization"][affiliation]

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            if self.affiliation is not None:
                _element('Affiliation', organization_ref=self.affiliation).write(xml_file)
            self.write_params(xml_file)


class Organization(ComponentBase):
    def __init__(self, name=None, id=DEFAULT_ORGANIZATION_ID, params=None,
                 parent=None, context=NullMap, **kwargs):
        self.name = name
        self.id = id
        self.params = self.prepare_params(params, **kwargs)
        self.element = _element("Organization", name=name, id=id)
        self.context = context
        self.context["Organization"][id] = self.element.id
        self.parent = self.context["Organization"][parent]

    def write(self, xml_file):
        xml_file.write(self.element.element())
        self.write_params(xml_file)
        if self.parent is not None:
            _element("Parent", organization_ref=self.parent).write(xml_file)


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


class AnalysisSampleCollection(ComponentBase):
    def __init__(self, samples=None, context=NullMap):
        self.samples = ensure_iterable(samples)
        self.context = context
        self.element = _element("AnalysisSampleCollection")

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            for sample in self.samples:
                sample.write(xml_file)


class Sample(ComponentBase):
    def __init__(self, id, name=None, contact=None, role=None, sub_samples=None,
                 params=None, context=NullMap, **kwargs):
        self.id = id
        self.name = name
        self.contact = contact
        self.role = ensure_iterable(role)
        self.sub_samples = ensure_iterable(sub_samples)
        self.params = self.prepare_params(params, **kwargs)
        self.context = context
        self.element = _element("Sample", id=self.id, name=self.name)
        self.context['Sample'][self.id] = self.element.id

    def write(self, xml_file):
        with self.element(xml_file, with_id=True):
            with element(xml_file, "ContactRole", contact_ref=self.contact):
                with element(xml_file, "Role"):
                    self.write_params(xml_file, self.prepare_params(self.role))
            for sample_ref in self.sub_samples:
                _element(
                    "SubSample",
                    sample_ref=self.context['Sample'][sample_ref]).write(xml_file)
            self.write_params(xml_file)
