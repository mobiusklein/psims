from contextlib import contextmanager
import numbers

from lxml import etree
import numpy as np

from psims.xml import XMLWriterMixin, XMLDocumentWriter

from .components import (
    ComponentDispatcher, element,
    default_cv_list, MzML, _xmlns)

from .binary_encoding import (
    encode_array, COMPRESSION_NONE, COMPRESSION_ZLIB,
    encoding_map)

from utils import ensure_iterable, basestring


MZ_ARRAY = 'm/z array'
INTENSITY_ARRAY = 'intensity array'
CHARGE_ARRAY = 'charge array'
TIME_ARRAY = "time array"
NON_STANDARD_ARRAY = 'non-standard data array'

ARRAY_TYPES = [
    'm/z array',
    'intensity array',
    'charge array',
    'signal to noise array',
    'time array',
    'wavelength array',
    'flow rate array',
    'pressure array',
    'temperature array',
    'mean drift time array',
    'mean charge array',
    'resolution array',
    'baseline array'
]

compression_map = {
    COMPRESSION_ZLIB: "zlib compression",
    COMPRESSION_NONE: 'no compression',
    None: 'no compression'
}


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


class SpectrumListSection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(SpectrumListSection, self).__init__(
            "spectrumList", writer, parent_context, section_args=section_args, **kwargs)
        self.section_args.setdefault("count", 0)
        data_processing_method = self.section_args.pop("data_processing_method", None)
        if data_processing_method is not None:
            self.section_args["defaultDataProcessingRef"] = self.context[
                "DataProcessing"][data_processing_method]


class ChromatogramListSection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(ChromatogramListSection, self).__init__(
            "chromatogramList", writer, parent_context, section_args=section_args, **kwargs)
        self.section_args.setdefault("count", 0)
        data_processing_method = self.section_args.pop("data_processing_method", None)
        if data_processing_method is not None:
            self.section_args["defaultDataProcessingRef"] = self.context[
                "DataProcessing"][data_processing_method]


class RunSection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(RunSection, self).__init__(
            "run", writer, parent_context, section_args=section_args, **kwargs)
        instrument_configuration_name = self.section_args.pop("instrument_configuration", None)
        if instrument_configuration_name is not None:
            self.section_args["defaultInstrumentConfigurationRef"] = self.context[
                "InstrumentConfiguration"][instrument_configuration_name]
        source_file_name = self.section_args.pop("source_file", None)
        if source_file_name is not None:
            self.section_args["defaultSourceFileRef"] = self.context["SourceFile"][source_file_name]

# ----------------------
# Order of Instantiation
# todo


class MzMLWriter(ComponentDispatcher, XMLDocumentWriter):
    """
    A high level API for generating mzML XML files from simple Python objects.

    This class depends heavily on lxml's incremental file writing API which in turn
    depends heavily on context managers. Almost all logic is handled inside a context
    manager and in the context of a particular document. Since all operations assume
    that they have access to a universal identity map for each element in the document,
    that map is centralized in this class.

    MzMLWriter inherits from :class:`.ComponentDispatcher`, giving it a :attr:`context`
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

    toplevel_tag = MzML

    def __init__(self, outfile, vocabularies=None, **kwargs):
        if vocabularies is None:
            vocabularies = []
        vocabularies = list(default_cv_list) + list(vocabularies)
        ComponentDispatcher.__init__(self, vocabularies=vocabularies)
        XMLDocumentWriter.__init__(self, outfile, **kwargs)
        self.spectrum_count = 0
        self.chromatogram_count = 0

    def controlled_vocabularies(self, vocabularies=None):
        if vocabularies is None:
            vocabularies = []
        self.vocabularies.extend(vocabularies)
        cvlist = self.CVList(self.vocabularies)
        cvlist.write(self.writer)

    def software_list(self, software_list):
        n = len(software_list)
        if n:
            software_list = [self.Software(**sw) for sw in software_list]
        self.SoftwareList(software_list).write(self)

    def file_description(self, file_contents=None, source_files=None, params=None):
        with self.element("fileDescription"):
            with self.element("fileContent"):
                for param in file_contents:
                    self.param(param)(self)
            source_file_list = self.SourceFileList(
                [self.SourceFile(**sf) for sf in ensure_iterable(source_files)])
            source_file_list.write(self)

    def instrument_configuration_list(self, instrument_configurations=None):
        configs = [
            self.InstrumentConfiguration(**ic) for ic in ensure_iterable(
                instrument_configurations)]
        self.InstrumentConfigurationList(configs).write(self)

    def data_processing_list(self, processing_methods=None):
        methods = [
            self.DataProcessing(**dp) for dp in ensure_iterable(processing_methods)]
        self.DataProcessingList(methods).write(self)

    def reference_param_group_list(self, groups=None):
        groups = [
            self.ReferenceableParamGroup(**g) for g in ensure_iterable(groups)]
        self.ReferenceableParamGroupList(groups).write(self)

    def run(self, id=None, instrument_configuration=None, source_file=None, start_time=None):
        kwargs = {}
        if start_time is not None:
            kwargs['startTimeStamp'] = start_time
        return RunSection(
            self.writer, self.context, id=id, instrument_configuration=instrument_configuration,
            source_file=source_file, **kwargs)

    def spectrum_list(self, count, data_processing_method=None):
        return SpectrumListSection(
            self.writer, self.context, count=count,
            data_processing_method=data_processing_method)

    def chromatogram_list(self, count, data_processing_method=None):
        return ChromatogramListSection(
            self.writer, self.context, count=count,
            data_processing_method=data_processing_method)

    def write_spectrum(self, mz_array=None, intensity_array=None, charge_array=None, id=None,
                       polarity='positive scan', centroided=True, precursor_information=None,
                       scan_start_time=None, params=None, compression=COMPRESSION_ZLIB,
                       encoding=32, other_arrays=None):
        if params is None:
            params = []
        else:
            params = list(params)
        if other_arrays is None:
            other_arrays = []

        # Binary choice, default to positive
        if polarity is None:
            polarity = 'positive scan'
        elif isinstance(polarity, int):
            if polarity > 0:
                polarity = 'positive scan'
            else:
                polarity = 'negative scan'
        elif 'positive' in polarity:
            polarity = 'positive scan'
        else:
            polarity = 'negative scan'

        if centroided:
            peak_mode = "centroid spectrum"
        else:
            peak_mode = 'profile spectrum'
        params.append(peak_mode)

        array_list = []
        default_array_length = len(mz_array)
        if mz_array is not None:
            mz_array_tag = self._prepare_array(
                mz_array, encoding=encoding, compression=compression, array_type=MZ_ARRAY)
            array_list.append(mz_array_tag)

        if intensity_array is not None:
            intensity_array_tag = self._prepare_array(
                intensity_array, encoding=encoding, compression=compression, array_type=INTENSITY_ARRAY)
            array_list.append(intensity_array_tag)

        if charge_array is not None:
            charge_array_tag = self._prepare_array(
                charge_array, encoding=encoding, compression=compression, array_type=CHARGE_ARRAY)
            array_list.append(charge_array_tag)
        for array, array_type in other_arrays:
            array_tag = self._prepare_array(
                array, encoding=encoding, compression=compression, array_type=array_type,
                default_array_length=default_array_length)
            array_list.append(array_tag)
        array_list_tag = self.BinaryDataArrayList(array_list)

        if polarity not in params:
            params.append(polarity)

        if precursor_information is not None:
            precursor_list = self._prepare_precursor_information(
                **precursor_information)
        else:
            precursor_list = None

        scan_params = []
        if scan_start_time is not None:
            if isinstance(scan_start_time, numbers.Number):
                scan_params.append({"name": "scan start time",
                                    "value": scan_start_time,
                                    "unitName": 'minute'})
            else:
                scan_params.append(scan_start_time)

        scan = self.Scan(params=scan_params)
        scan_list = self.ScanList([scan], params=["no combination"])

        index = self.spectrum_count
        self.spectrum_count += 1
        spectrum = self.Spectrum(
            index, array_list_tag, scan_list=scan_list, params=params, id=id,
            default_array_length=default_array_length,
            precursor_list=precursor_list)
        spectrum.write(self.writer)

    def write_chromatogram(self, time_array, intensity_array, id=None,
                           chromatogram_type="selected ion current", params=None,
                           compression=COMPRESSION_ZLIB, encoding=32, other_arrays=None):
        if params is None:
            params = []
        else:
            params = list(params)
        if other_arrays is None:
            other_arrays = []
        array_list = []

        default_array_length = len(time_array)
        if time_array is not None:
            time_array_tag = self._prepare_array(
                time_array, encoding=encoding, compression=compression, array_type=TIME_ARRAY)
            array_list.append(time_array_tag)

        if intensity_array is not None:
            intensity_array_tag = self._prepare_array(
                intensity_array, encoding=encoding, compression=compression, array_type=INTENSITY_ARRAY)
            array_list.append(intensity_array_tag)

        for array, array_type in other_arrays:
            array_tag = self._prepare_array(
                array, encoding=encoding, compression=compression, array_type=array_type,
                default_array_length=default_array_length)
            array_list.append(array_tag)
        params.append(chromatogram_type)
        array_list_tag = self.BinaryDataArrayList(array_list)
        index = self.chromatogram_count
        self.chromatogram_count += 1
        chromatogram = self.Chromatogram(
            index=index, binary_data_list=array_list_tag,
            default_array_length=default_array_length,
            id=id, params=params)
        chromatogram.write(self.writer)

    def _prepare_array(self, numeric, encoding=32, compression=COMPRESSION_ZLIB, array_type=None,
                       default_array_length=None):
        _encoding = int(encoding)
        array = np.array(numeric)
        encoding = encoding_map[_encoding]
        encoded_binary = encode_array(
            array, compression=compression, dtype=encoding)
        binary = self.Binary(encoded_binary)
        if default_array_length is not None and len(array) != default_array_length:
            override_length = True
        else:
            override_length = False
        params = []
        if array_type is not None:
            params.append(array_type)
            if array_type not in ARRAY_TYPES:
                params.append(NON_STANDARD_ARRAY)
        params.append(compression_map[compression])
        params.append("%d-bit float" % _encoding)
        encoded_length = len(encoded_binary)
        return self.BinaryDataArray(
            binary, encoded_length, array_length=(len(array) if override_length else None),
            params=params)

    def _prepare_precursor_information(self, mz, intensity, charge, scan_id, activation=None):
        if activation is not None:
            activation = self.Activation(activation)
        ion = self.SelectedIon(mz, intensity, charge)
        ion_list = self.SelectedIonList([ion])
        precursor = self.Precursor(
            ion_list,
            activation=activation,
            isolation_window=None,
            spectrum_reference=scan_id)
        precursor_list = self.PrecursorList([precursor])
        return precursor_list
