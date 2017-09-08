from numbers import Number
from .components import (
    MzIdentML,
    ComponentDispatcher, etree, common_units, element, _element,
    default_cv_list, CVParam, UserParam,
    _xmlns)

from psims.xml import XMLWriterMixin, XMLDocumentWriter

from .utils import ensure_iterable

_t = tuple()


class DocumentSection(ComponentDispatcher, XMLWriterMixin):

    def __init__(self, section, writer, parent_context, section_args=None, **kwargs):
        if section_args is None:
            section_args = dict()
        section_args.update(kwargs)
        super(DocumentSection, self).__init__(parent_context)
        self.section = section
        self.writer = writer
        self.section_args = section_args

    def __enter__(self):
        self.toplevel = element(self.writer, self.section, **self.section_args)
        self.toplevel.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.toplevel.__exit__(exc_type, exc_value, traceback)
        self.writer.flush()


class AnalysisProtocolCollection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(AnalysisProtocolCollection, self).__init__(
            "AnalysisProtocolCollection", writer, parent_context,
            xmlns=_xmlns)


class SequenceCollection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(SequenceCollection, self).__init__(
            "SequenceCollection", writer, parent_context, xmlns=_xmlns)


class AnalysisCollection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(AnalysisCollection, self).__init__(
            "AnalysisCollection", writer, parent_context, xmlns=_xmlns)


class DataCollection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(DataCollection, self).__init__(
            "DataCollection", writer, parent_context, xmlns=_xmlns)


class AnalysisData(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(AnalysisData, self).__init__(
            "AnalysisData", writer, parent_context, xmlns=_xmlns)


# ----------------------
# Order of Instantiation
# Providence -> Input -> Protocol -> Identification


class MzIdentMLWriter(ComponentDispatcher, XMLDocumentWriter):
    """
    A high level API for generating MzIdentML XML files from simple Python objects.

    This class depends heavily on lxml's incremental file writing API which in turn
    depends heavily on context managers. Almost all logic is handled inside a context
    manager and in the context of a particular document. Since all operations assume
    that they have access to a universal identity map for each element in the document,
    that map is centralized in this instance.

    MzIdentMLWriter inherits from :class:`.ComponentDispatcher`, giving it a :attr:`context`
    attribute and access to all `Component` objects pre-bound to that context with attribute-access
    notation.

    Attributes
    ----------
    outfile : file
        The open, writable file descriptor which XML will be written to.
    xmlfile : lxml.etree.xmlfile
        The incremental XML file wrapper which organizes file writes onto :attr:`outfile`.
        Kept to control context.
    writer : lxml.etree._IncrementalFileWriter
        The incremental XML writer produced by :attr:`xmlfile`. Kept to control context.
    toplevel : lxml.etree._FileWriterElement
        The top level incremental xml writer element which will be closed at the end
        of file generation. Kept to control context
    context : :class:`.DocumentContext`
    """

    toplevel_tag = MzIdentML

    def __init__(self, outfile, vocabularies=None, **kwargs):
        if vocabularies is None:
            vocabularies = list(default_cv_list)
        ComponentDispatcher.__init__(self, vocabularies=vocabularies)
        XMLDocumentWriter.__init__(self, outfile, **kwargs)

    def controlled_vocabularies(self, vocabularies=None):
        if vocabularies is None:
            vocabularies = []
        self.vocabularies.extend(vocabularies)
        cvlist = self.CVList(self.vocabularies)
        cvlist.write(self.writer)

    def providence(self, software=tuple(), owner=None, organization=None):
        """
        Write the analysis providence section, a top-level segment of the MzIdentML document

        This section should be written early on to register the list of software used in this
        analysis

        Parameters
        ----------
        software : dict or list of dict, optional
            A single dictionary or list of dictionaries specifying an :class:`AnalysisSoftware` instance
        owner : dict, optional
            A dictionary specifying a :class:`Person` instance. If missing, a default person will be created
        organization : dict, optional
            A dictionary specifying a :class:`Organization` instance. If missing, a default organization will
            be created
        """
        software = [self.AnalysisSoftware(**(s or {}))
                    for s in ensure_iterable(software)]
        owner = self.Person(**(owner or {}))
        organization = self.Organization(**(organization or {}))

        self.GenericCollection("AnalysisSoftwareList",
                               software).write(self.writer)
        self.Provider(contact=owner.id).write(self.writer)
        self.AuditCollection([owner], [organization]).write(self.writer)

    def inputs(self, source_files=tuple(), search_databases=tuple(), spectra_data=tuple()):
        source_files = [self.SourceFile(**(s or {}))
                        for s in ensure_iterable(source_files)]
        search_databases = [self.SearchDatabase(
            **(s or {})) for s in ensure_iterable(search_databases)]
        spectra_data = [self.SpectraData(**(s or {}))
                        for s in ensure_iterable(spectra_data)]

        self.Inputs(source_files, search_databases,
                    spectra_data).write(self.writer)

    def analysis_protocol_collection(self):
        return AnalysisProtocolCollection(self.writer, self.context)

    def sequence_collection(self):
        return SequenceCollection(self.writer, self.context)

    def analysis_collection(self):
        return AnalysisCollection(self.writer, self.context)

    def data_collection(self):
        return DataCollection(self.writer, self.context)

    def _sequence_collection(self, db_sequences=tuple(), peptides=tuple(), peptide_evidence=tuple()):
        db_sequences = (self.DBSequence(**(s or {}))
                        for s in ensure_iterable(db_sequences))
        peptides = (self.Peptide(**(s or {}))
                    for s in ensure_iterable(peptides))
        peptide_evidence = (self.PeptideEvidence(**(s or {}))
                            for s in ensure_iterable(peptide_evidence))

        self.SequenceCollection(db_sequences, peptides,
                                peptide_evidence).write(self.writer)

    def spectrum_identification_protocol(self, search_type='ms-ms search', analysis_software_id=1, id=1,
                                         additional_search_params=None, enzymes=None, modification_params=None,
                                         fragment_tolerance=None, parent_tolerance=None, threshold=None):

        enzymes = [self.Enzyme(**(s or {})) for s in ensure_iterable(enzymes)]
        modification_params = [self.SearchModification(
            **(s or {})) for s in ensure_iterable(modification_params)]
        if isinstance(fragment_tolerance, (list, tuple)):
            fragment_tolerance = self.FragmentTolerance(*fragment_tolerance)
        elif isinstance(fragment_tolerance, Number):
            if fragment_tolerance < 1e-4:
                fragment_tolerance = self.FragmentTolerance(fragment_tolerance * 1e6, None, "parts per million")
            else:
                fragment_tolerance = self.FragmentTolerance(fragment_tolerance, None, "dalton")

        if isinstance(parent_tolerance, (list, tuple)):
            parent_tolerance = self.ParentTolerance(*parent_tolerance)
        elif isinstance(parent_tolerance, Number):
            if parent_tolerance < 1e-4:
                parent_tolerance = self.ParentTolerance(parent_tolerance * 1e6, None, "parts per million")
            else:
                parent_tolerance = self.ParentTolerance(parent_tolerance, None, "dalton")
        threshold = self.Threshold(threshold)
        protocol = self.SpectrumIdentificationProtocol(
            search_type, analysis_software_id, id, additional_search_params, modification_params, enzymes,
            fragment_tolerance, parent_tolerance, threshold)
        protocol.write(self.writer)

    def analysis_data(self):
        return AnalysisData(self.writer, self.context)

    def spectrum_identification_list(self, id, identification_results=None, measures=None):
        if measures is None:
            measures = self.FragmentationTable()
        converting = (self.spectrum_identification_result(**(s or {}))
                      for s in ensure_iterable(identification_results))
        self.SpectrumIdentificationList(
            id=id, identification_results=converting,
            fragmentation_table=measures).write(self.writer)

    def spectrum_identification_result(self, spectrum_id, id, spectra_data_id=1, identifications=None):
        return self.SpectrumIdentificationResult(
            spectra_data_id=spectra_data_id,
            spectrum_id=spectrum_id,
            id=id,
            identifications=(self.spectrum_identification_item(**(s or {}))
                             for s in ensure_iterable(identifications)))

    def spectrum_identification_item(self, calculated_mass_to_charge, experimental_mass_to_charge,
                                     charge_state, peptide_id, peptide_evidence_id, score, id, ion_types=None,
                                     params=None, pass_threshold=True, rank=1):
        mappings = []
        # measure_mapping = self.context["Measure"]
        if ion_types is not None:
            IonType = self.IonType
            for series, measures in ion_types.items():
                measures_ = {}
                for measure, values in measures.items():
                    if measure in ("indices", "charge_state"):
                        continue
                    measures_[measure] = values

                it = IonType(series=IonType.guess_ion_type(series), indices=measures['indices'],
                             charge_state=measures.get('charge_state', 1), measures=measures_)
                mappings.append(it)
        return self.SpectrumIdentificationItem(
            calculated_mass_to_charge, experimental_mass_to_charge,
            charge_state, peptide_id, peptide_evidence_id, score, id,
            ion_types=mappings,
            params=ensure_iterable(params), pass_threshold=pass_threshold, rank=rank)
