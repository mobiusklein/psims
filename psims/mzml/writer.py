import numbers
import warnings

from collections import defaultdict

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

import numpy as np

from psims.xml import XMLWriterMixin, XMLDocumentWriter
from psims.utils import TableStateMachine

from .components import (
    ComponentDispatcher, element,
    default_cv_list, MzML, InstrumentConfiguration, IndexedMzML)

from .binary_encoding import (
    encode_array, COMPRESSION_ZLIB,
    encoding_map, compression_map, dtype_to_encoding)

from .utils import ensure_iterable
from .index import IndexingStream

from .element_builder import ElementBuilder, ParamManagingProperty


MZ_ARRAY = 'm/z array'
INTENSITY_ARRAY = 'intensity array'
DEFAULT_INTENSITY_UNIT = "number of detector counts"
CHARGE_ARRAY = 'charge array'
TIME_ARRAY = "time array"
DEFAULT_TIME_UNIT = "minute"
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
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.toplevel.__exit__(exc_type, exc_value, traceback)
        self.writer.flush()


class SpectrumListSection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(SpectrumListSection, self).__init__(
            "spectrumList", writer, parent_context, section_args=section_args,
            **kwargs)
        self.section_args.setdefault("count", 0)
        data_processing_method = self.section_args.pop(
            "data_processing_method", None)
        try:
            self.section_args["defaultDataProcessingRef"] = self.context[
                "DataProcessing"][data_processing_method]
        except KeyError:
            try:
                self.section_args["defaultDataProcessingRef"] = list(
                    self.context["DataProcessing"].values())[0]
            except IndexError:
                warnings.warn(
                    "No Data Processing method found. mzML file may not be fully standard-compliant",
                    stacklevel=2)


class ChromatogramListSection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(ChromatogramListSection, self).__init__(
            "chromatogramList", writer, parent_context,
            section_args=section_args, **kwargs)
        self.section_args.setdefault("count", 0)
        data_processing_method = self.section_args.pop(
            "data_processing_method", None)
        try:
            self.section_args["defaultDataProcessingRef"] = self.context[
                "DataProcessing"][data_processing_method]
        except KeyError:
            try:
                self.section_args["defaultDataProcessingRef"] = list(
                    self.context["DataProcessing"].values())[0]
            except IndexError:
                warnings.warn(
                    "No Data Processing method found. mzML file may not be fully standard-compliant",
                    stacklevel=2)


class RunSection(DocumentSection):
    """Describes a `<run>` tag. Implemented as a section to provide a more
    expressive API
    """
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(RunSection, self).__init__(
            "run", writer, parent_context, section_args=section_args, **kwargs)
        instrument_configuration_name = self.section_args.pop(
            "instrument_configuration", None)
        if instrument_configuration_name is not None:
            self.section_args["defaultInstrumentConfigurationRef"] = self.context[
                "InstrumentConfiguration"][instrument_configuration_name]
        source_file_name = self.section_args.pop("source_file", None)
        if source_file_name is not None:
            self.section_args["defaultSourceFileRef"] = self.context[
                "SourceFile"][source_file_name]
        sample_id = self.section_args.pop("sample", None)
        if sample_id is not None:
            self.section_args["sampleRef"] = self.context['Sample'][sample_id]


class IndexedmzMLSection(DocumentSection):
    def __init__(self, writer, parent_context, indexer, section_args=None, **kwargs):
        super(IndexedmzMLSection, self).__init__(
            'indexedmzML', writer, parent_context, section_args=section_args,
            **kwargs)
        self.toplevel = None
        self.inner = None
        self.indexer = indexer

    def __enter__(self):
        self.toplevel = element(self.writer, IndexedMzML())
        self.toplevel.__enter__()
        self.inner = element(self.writer, MzML(**self.section_args))
        self.inner.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.inner.__exit__(exc_type, exc_value, traceback)
        self.writer.flush()
        self.write_index()
        self.toplevel.__exit__(exc_type, exc_value, traceback)

    def write_index(self):
        self.indexer.to_xml(self)


class PlainMzMLWriter(ComponentDispatcher, XMLDocumentWriter):
    """A high level API for generating mzML XML files from simple Python objects.

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
    chromatogram_count : int
        A count of the number of chromatograms written
    spectrum_count : int
        A count of the number of spectra written
    """

    DEFAULT_TIME_UNIT = DEFAULT_TIME_UNIT
    DEFAULT_INTENSITY_UNIT = DEFAULT_INTENSITY_UNIT

    def __init__(self, outfile, close=False, vocabularies=None, missing_reference_is_error=False,
                 vocabulary_resolver=None, id=None, accession=None, **kwargs):
        if vocabularies is None:
            vocabularies = []
        vocabularies = list(default_cv_list) + list(vocabularies)
        ComponentDispatcher.__init__(
            self,
            vocabularies=vocabularies,
            vocabulary_resolver=vocabulary_resolver,
            missing_reference_is_error=missing_reference_is_error)
        XMLDocumentWriter.__init__(self, outfile, close, **kwargs)
        self.id = id
        self.accession = accession
        self.spectrum_count = 0
        self.chromatogram_count = 0
        self.default_instrument_configuration = None
        self.state_machine = TableStateMachine([
            ("start", ['controlled_vocabularies', ]),
            ("controlled_vocabularies", ['file_description', ]),
            ("file_description", ['reference_param_group_list', 'sample_list', 'software_list']),
            ("reference_param_group_list", ['sample_list', 'software_list']),
            ("sample_list", ['software_list', ]),
            ("software_list", ["scan_settings_list", 'instrument_configuration_list']),
            ("scan_settings_list", ['instrument_configuration_list', ]),
            ("instrument_configuration_list", ['data_processing_list']),
            ("data_processing_list", ['run']),
            ("run", ['spectrum_list', 'chromatogram_list']),
            ('spectrum_list', ['chromatogram_list']),
            ('chromatogram_list', [])
        ])

    def toplevel_tag(self):
        return MzML(id=self.id, accession=self.accession)

    def controlled_vocabularies(self):
        """Write out the `<cvList>` element and all its children,
        including both this format's default controlled vocabularies
        and those passed as arguments to this method.this

        This method requires writing to have begun.
        """
        self.state_machine.transition("controlled_vocabularies")
        super(PlainMzMLWriter, self).controlled_vocabularies()

    def software_list(self, software_list):
        """Writes the ``<softwareList>`` section of the document.

        .. note::
            List and descriptions of software used to acquire and/or process the
            data in this mzML file

        Parameters
        ----------
        software_list : list
            A list or other iterable of :class:`dict` or :class:`~.Software`-like objects
        """
        self.state_machine.transition("software_list")
        n = len(software_list)
        if n:
            software_list = [self.Software.ensure(sw) for sw in ensure_iterable(software_list)]
        self.SoftwareList(software_list).write(self)

    def file_description(self, file_contents=None, source_files=None, contacts=None):
        r"""Writes the ``<fileDescription>`` section of the document.

        .. note::
            Information pertaining to the entire mzML file (i.e. not specific
            to any part of the data set) is stored here.

        Parameters
        ----------
        file_contents : list, optional
            A list or other iterable of :class:`str`, :class:`dict`, or \*Param-types which will
            be placed in the ``<fileContent>`` element.
        source_files : list
            A list or other iterable of dict or :class:`~.SourceFile`-like objects
            to be placed in the ``<sourceFileList>`` element
        """
        self.state_machine.transition("file_description")
        fd = self.FileDescription(
            file_contents, [self.SourceFile.ensure(sf) for sf in ensure_iterable(source_files)],
            contacts=[self.Contact.ensure(c) for c in ensure_iterable(contacts)])
        fd.write(self.writer)

    def instrument_configuration_list(self, instrument_configurations):
        """Writes the ``<instrumentConfigurationList>`` section of the document.

        .. note::
            List and descriptions of instrument configurations. At least one instrument configuration MUST
            be specified, even if it is only to specify that the instrument is unknown. In that case, the
            "instrument model" term is used to indicate the unknown instrument in the instrumentConfiguration

        Parameters
        ----------
        instrument_configurations : list
            A list or other iterable of :class:`dict` or :class:`~.InstrumentConfiguration`-like
            objects
        """
        self.state_machine.transition("instrument_configuration_list")
        configs = [
            self.InstrumentConfiguration.ensure(ic) if not isinstance(
                ic, InstrumentConfiguration) else ic
            for ic in ensure_iterable(
                instrument_configurations)]
        self.InstrumentConfigurationList(configs).write(self)

    def data_processing_list(self, data_processing):
        """Writes the ``<dataProcessingList>`` section of the document.

        .. note::
            List and descriptions of data processing applied to this data

        Parameters
        ----------
        data_processing : list
            A list or other iterable of :class:`dict` or :class:`~.DataProcessing`-like
            objects

        """
        self.state_machine.transition("data_processing_list")
        methods = [
            self.DataProcessing.ensure(dp) for dp in ensure_iterable(data_processing)]
        self.DataProcessingList(methods).write(self)

    def reference_param_group_list(self, groups):
        """Writes the ``<referenceableParamGroupList>`` section of the document.

        Parameters
        ----------
        groups : list
            A list or other iterable of :class:`dict` or :class:`~.ReferenceableParamGroup`-like
            objects

        """
        self.state_machine.transition("reference_param_group_list")
        groups = [
            self.ReferenceableParamGroup.ensure(g) for g in ensure_iterable(groups)]
        self.ReferenceableParamGroupList(groups).write(self)

    def sample_list(self, samples):
        """Writes the ``<sampleList>`` section of the document

        Parameters
        ----------
        samples : list
            A list or other iterable of :class:`dict` or :class:`~.mzml.components.Sample`-like
            objects

        """
        self.state_machine.transition("sample_list")
        for i, sample in enumerate(ensure_iterable(samples)):
            if isinstance(sample, Mapping):
                sample_id = sample.get('id')
                sample_name = sample.get("name")

                if sample_id is None and sample_name is not None:
                    sample_id = "%s_%d_id" % (sample_name, i)
                elif sample_id is not None and sample_name is None:
                    sample_name = str(sample_id)
                elif sample_id is sample_name is None:
                    sample_id = "sample_%d_id" % (i,)
                    sample_name = "sample_%d" % (i,)
                sample['id'] = sample_id
                sample['name'] = sample_name

        sample_entries = self.Sample.ensure_all(samples)

        self.SampleList(sample_entries).write(self)

    def scan_settings_list(self, scan_settings):
        self.state_machine.transition("scan_settings_list")
        scan_settings = self.ScanSettings.ensure_all(scan_settings)
        self.ScanSettingsList(scan_settings).write(self)

    def run(self, id=None, instrument_configuration=None, source_file=None, start_time=None, sample=None):
        """Begins the `<run>` section of the document, describing a single
        sample run.

        Parameters
        ----------
        id : str, optional
            The unique identifier for this element
        instrument_configuration : str, optional
            The id string for the default `InstrumentConfiguration` for this
            sample
        source_file : str, optional
            The id string for the source file used to produce this data
        start_time : str, optional
            A string encoding the date and time the sample was acquired
        sample: str, optional
            The id string for the sample used to produce this data

        Returns
        -------
        RunSection
        """
        self.state_machine.transition("run")
        kwargs = {}
        if start_time is not None:
            kwargs['startTimeStamp'] = start_time
        if instrument_configuration is None:
            keys = list(self.context['InstrumentConfiguration'].keys())
            if keys:
                instrument_configuration = keys[0]
            else:
                instrument_configuration = None
        self.default_instrument_configuration = instrument_configuration
        return RunSection(
            self.writer, self.context, id=id,
            instrument_configuration=instrument_configuration,
            source_file=source_file,
            sample=sample, **kwargs)

    def spectrum_list(self, count, data_processing_method=None):
        self.state_machine.transition('spectrum_list')
        if data_processing_method is None:
            dp_map = self.context['DataProcessing']
            try:
                data_processing_method = list(dp_map.keys())[0]
            except IndexError:
                warnings.warn(
                    "No Data Processing method found. mzML file may not be fully standard-compliant",
                    stacklevel=2)
        return SpectrumListSection(
            self.writer, self.context, count=count,
            data_processing_method=data_processing_method)

    def chromatogram_list(self, count, data_processing_method=None):
        self.state_machine.transition('chromatogram_list')
        if data_processing_method is None:
            dp_map = self.context['DataProcessing']
            try:
                data_processing_method = list(dp_map.keys())[0]
            except IndexError:
                warnings.warn(
                    "No Data Processing method found. mzML file may not be fully standard-compliant",
                    stacklevel=2)
        return ChromatogramListSection(
            self.writer, self.context, count=count,
            data_processing_method=data_processing_method)

    def spectrum(self, mz_array=None, intensity_array=None, charge_array=None, id=None,
                 polarity='positive scan', centroided=True, precursor_information=None,
                 scan_start_time=None, params=None, compression=COMPRESSION_ZLIB,
                 encoding=None, other_arrays=None, scan_params=None, scan_window_list=None,
                 instrument_configuration_id=None, intensity_unit=DEFAULT_INTENSITY_UNIT):
        '''Create a new :class:`~.Spectrum` instance to be written.

        Parameters
        ----------
        mz_array: :class:`np.ndarray` of floats
            The m/z array of the spectrum
        intensity_array: :class:`np.ndarray` of floats
            The intensity array of the spectrum
        charge_array: :class:`np.ndarray`, optional
            The charge state array of the spectrum, optional.
        id: str
            The native ID of the spectrum.
        polarity: str or int, optional
            The polarity of the spectrum. If an integer, the sign of
            the integer is used, otherwise it is interpreted as a cvParam
        centroided: bool, optional
            Whether the spectrum is continuous or discretized by peak picking.
            Defaults to :const:`True`.
        precursor_information: dict or :class:`PrecursorBuilder`, optional
            The precursor ion description. Will be passed to :meth:`_prepare_precursor_list`
        scan_start_time: float, optional
            The scan start time, in minutes
        params: list, optional
            The parameters of the `spectrum`
        compression: str, optional
            The compression type name to use. Defaults to `COMPRESSION_ZLIB`.
        encoding: dict, optional
            A mapping from array name to NumPy data types.
        other_arrays: dict, optional
            A mapping of array names to additional data arrays
        scan_params: list, optional
            A list of cvParams for the `scan` of this `spectrum`
        scan_window_list: list, optional
            A list of scan windows specified as pairs of m/z intervals
        instrument_configuration_id: str, optional
            The `id` of the `instrumentConfiguration` to associate with this spectrum
            if not the default one.

        Returns
        -------
        :class:`~.Spectrum`
        '''
        self.state_machine.expects_state("spectrum_list")
        if encoding is None:
            {MZ_ARRAY: np.float64}
        if params is None:
            params = []
        else:
            params = list(params)
        if scan_params is None:
            scan_params = []
        else:
            scan_params = list(scan_params)
        if other_arrays is None:
            other_arrays = []
        if scan_window_list is None:
            scan_window_list = []
        else:
            scan_window_list = list(scan_window_list)

        if isinstance(encoding, Mapping):
            encoding = defaultdict(lambda: np.float32, encoding)
        else:
            # create new variable to capture in closure
            _encoding = encoding
            encoding = defaultdict(lambda: _encoding)
        if polarity is not None:
            if isinstance(polarity, int):
                if polarity > 0:
                    polarity = 'positive scan'
                elif polarity < 0:
                    polarity = 'negative scan'
                else:
                    polarity = None
            elif 'positive' in polarity:
                polarity = 'positive scan'
            elif 'negative' in polarity:
                polarity = 'negative scan'
            else:
                polarity = None

            if polarity not in params and polarity is not None:
                params.append(polarity)

        if centroided:
            peak_mode = "centroid spectrum"
        else:
            peak_mode = 'profile spectrum'
        params.append(peak_mode)

        array_list = []
        default_array_length = len(mz_array) if mz_array is not None else 0
        if mz_array is not None:
            mz_array_tag = self._prepare_array(
                mz_array, encoding=encoding[MZ_ARRAY], compression=compression, array_type=MZ_ARRAY)
            array_list.append(mz_array_tag)

        if intensity_array is not None:
            intensity_array_tag = self._prepare_array(
                intensity_array, encoding=encoding[INTENSITY_ARRAY], compression=compression,
                array_type={"name": INTENSITY_ARRAY, "unit_name": intensity_unit})
            array_list.append(intensity_array_tag)

        if charge_array is not None:
            charge_array_tag = self._prepare_array(
                charge_array, encoding=encoding[CHARGE_ARRAY], compression=compression,
                array_type=CHARGE_ARRAY)
            array_list.append(charge_array_tag)
        for array_type, array in other_arrays:
            if array_type is None:
                raise ValueError("array type can't be None")
            array_tag = self._prepare_array(
                array, encoding=encoding[array_type], compression=compression, array_type=array_type,
                default_array_length=default_array_length)
            array_list.append(array_tag)
        array_list_tag = self.BinaryDataArrayList(array_list)

        if precursor_information is not None:
            precursor_list = self._prepare_precursor_list(
                precursor_information, intensity_unit=intensity_unit)
        else:
            precursor_list = None

        if scan_start_time is not None:
            if isinstance(scan_start_time, numbers.Number):
                scan_params.append({"name": "scan start time",
                                    "value": scan_start_time,
                                    "unitName": DEFAULT_TIME_UNIT})
            else:
                scan_params.append(scan_start_time)
        # The spec says this is optional, but the validator calls this a must
        # if self.default_instrument_configuration == instrument_configuration_id:
        #     instrument_configuration_id = None
        scan = self.Scan(scan_window_list=scan_window_list, params=scan_params,
                         instrument_configuration_ref=instrument_configuration_id)
        scan_list = self.ScanList([scan], params=["no combination"])

        index = self.spectrum_count
        self.spectrum_count += 1
        spectrum = self.Spectrum(
            index, array_list_tag, scan_list=scan_list, params=params, id=id,
            default_array_length=default_array_length,
            precursor_list=precursor_list)
        return spectrum

    def write_spectrum(self, mz_array=None, intensity_array=None, charge_array=None, id=None,
                       polarity='positive scan', centroided=True, precursor_information=None,
                       scan_start_time=None, params=None, compression=COMPRESSION_ZLIB,
                       encoding=None, other_arrays=None, scan_params=None, scan_window_list=None,
                       instrument_configuration_id=None, intensity_unit=DEFAULT_INTENSITY_UNIT):
        '''Write a :class:`~.Spectrum` with the provided data.

        Parameters
        ----------
        mz_array: :class:`np.ndarray` of floats
            The m/z array of the spectrum
        intensity_array: :class:`np.ndarray` of floats
            The intensity array of the spectrum
        charge_array: :class:`np.ndarray`, optional
            The charge state array of the spectrum, optional.
        id: str
            The native ID of the spectrum.
        polarity: str or int, optional
            The polarity of the spectrum. If an integer, the sign of
            the integer is used, otherwise it is interpreted as a cvParam
        centroided: bool, optional
            Whether the spectrum is continuous or discretized by peak picking.
            Defaults to :const:`True`.
        precursor_information: dict or :class:`PrecursorBuilder`, optional
            The precursor ion description. Will be passed to :meth:`_prepare_precursor_list`
        scan_start_time: float, optional
            The scan start time, in minutes
        params: list, optional
            The parameters of the `spectrum`
        compression: str, optional
            The compression type name to use. Defaults to `COMPRESSION_ZLIB`.
        encoding: dict, optional
            A mapping from array name to NumPy data types.
        other_arrays: dict, optional
            A mapping of array names to additional data arrays
        scan_params: list, optional
            A list of cvParams for the `scan` of this `spectrum`
        scan_window_list: list, optional
            A list of scan windows specified as pairs of m/z intervals
        instrument_configuration_id: str, optional
            The `id` of the `instrumentConfiguration` to associate with this spectrum
            if not the default one.

        See Also
        --------
        :meth:`spectrum`
        '''
        spectrum = self.spectrum(
            mz_array=mz_array, intensity_array=intensity_array, charge_array=charge_array,
            id=id, polarity=polarity, centroided=centroided, precursor_information=precursor_information,
            scan_start_time=scan_start_time, params=params, compression=compression,
            encoding=encoding, other_arrays=other_arrays, scan_params=scan_params,
            scan_window_list=scan_window_list,
            instrument_configuration_id=instrument_configuration_id,
            intensity_unit=intensity_unit)
        spectrum.write(self.writer)

    def chromatogram(self, time_array, intensity_array, id=None,
                     chromatogram_type="selected ion current",
                     precursor_information=None, params=None,
                     compression=COMPRESSION_ZLIB, encoding=32, other_arrays=None,
                     intensity_unit=DEFAULT_INTENSITY_UNIT, time_unit=DEFAULT_TIME_UNIT):
        self.state_machine.expects_state("chromatogram_list")
        if params is None:
            params = []
        else:
            params = list(params)

        if isinstance(encoding, Mapping):
            encoding = defaultdict(lambda: np.float32, encoding)
        else:
            # create new variable to capture in closure
            _encoding = encoding
            encoding = defaultdict(lambda: _encoding)

        if other_arrays is None:
            other_arrays = []
        array_list = []

        if precursor_information is not None:
            precursor = self._prepare_precursor_list(
                precursor_information, intensity_unit=intensity_unit)[0]
        else:
            precursor = None

        default_array_length = len(time_array) if time_array is not None else 0
        if time_array is not None:
            time_array_tag = self._prepare_array(
                time_array, encoding=encoding[TIME_ARRAY], compression=compression,
                array_type={"name": TIME_ARRAY, "unit_name": time_unit})
            array_list.append(time_array_tag)

        if intensity_array is not None:
            intensity_array_tag = self._prepare_array(
                intensity_array, encoding=encoding[INTENSITY_ARRAY], compression=compression,
                array_type={"name": INTENSITY_ARRAY, "unit_name": intensity_unit})
            array_list.append(intensity_array_tag)

        for array_type, array in other_arrays:
            array_tag = self._prepare_array(
                array, encoding=encoding[array_type], compression=compression, array_type=array_type,
                default_array_length=default_array_length)
            array_list.append(array_tag)
        params.append(chromatogram_type)
        array_list_tag = self.BinaryDataArrayList(array_list)
        index = self.chromatogram_count
        self.chromatogram_count += 1
        chromatogram = self.Chromatogram(
            index=index, binary_data_list=array_list_tag,
            precursor=precursor,
            default_array_length=default_array_length,
            id=id, params=params)
        return chromatogram

    def write_chromatogram(self, time_array, intensity_array, id=None,
                           chromatogram_type="selected ion current",
                           precursor_information=None, params=None,
                           compression=COMPRESSION_ZLIB, encoding=32, other_arrays=None,
                           intensity_unit=DEFAULT_INTENSITY_UNIT, time_unit=DEFAULT_TIME_UNIT):
        chromatogram = self.chromatogram(
            time_array=time_array, intensity_array=intensity_array, id=id,
            chromatogram_type=chromatogram_type, precursor_information=precursor_information,
            params=params, compression=compression, encoding=encoding,
            other_arrays=other_arrays, intensity_unit=intensity_unit, time_unit=time_unit)
        chromatogram.write(self.writer)

    def _prepare_array(self, array, encoding=32, compression=COMPRESSION_ZLIB,
                       array_type=None, default_array_length=None):
        if isinstance(encoding, numbers.Number):
            _encoding = int(encoding)
        else:
            _encoding = encoding
        dtype = encoding_map[_encoding]
        array = np.array(array, dtype=dtype)
        encoded_binary = encode_array(
            array, compression=compression, dtype=dtype)
        binary = self.Binary(encoded_binary)
        if default_array_length is not None and len(array) != default_array_length:
            override_length = True
        else:
            override_length = False
        params = []
        if array_type is not None:
            params.append(array_type)
            if isinstance(array_type, Mapping):
                array_type_ = array_type['name']
            else:
                array_type_ = array_type
            if array_type_ not in ARRAY_TYPES:
                params.append(NON_STANDARD_ARRAY)
        params.append(compression_map[compression])
        params.append(dtype_to_encoding[dtype])
        encoded_length = len(encoded_binary)
        return self.BinaryDataArray(
            binary, encoded_length,
            array_length=(len(array) if override_length else None),
            params=params)

    def _prepare_precursor_list(self, precursors, intensity_unit=DEFAULT_INTENSITY_UNIT):
        if isinstance(precursors, self.PrecursorList.type):
            return precursors
        elif isinstance(precursors, (dict)):
            precursors = self.PrecursorList([self._prepare_precursor_information(
                intensity_unit=intensity_unit, **precursors)])
        elif isinstance(precursors, PrecursorBuilder):
            precursors = self.PrecursorList([self._prepare_precursor_information(
                precursors,
                intensity_unit=intensity_unit)])
        else:
            packaged = []
            for p in ensure_iterable(precursors):
                if isinstance(p, self.Precursor.type):
                    packaged.append(p)
                elif isinstance(p, dict):
                    packaged.append(
                        self._prepare_precursor_information(
                            intensity_unit=intensity_unit, **p))
                elif isinstance(p, PrecursorBuilder):
                    packaged.append(
                        self._prepare_precursor_information(
                            p, intensity_unit=intensity_unit))
            precursors = self.PrecursorList(packaged)
        return precursors

    def _prepare_precursor_information(self, mz=None, intensity=None, charge=None, spectrum_reference=None, activation=None,
                                       isolation_window_args=None, params=None,
                                       intensity_unit=DEFAULT_INTENSITY_UNIT, scan_id=None, external_spectrum_id=None,
                                       source_file_reference=None):
        '''Prepare a :class:`Precursor` element from disparate data structures.

        Parameters
        ----------
        mz: float, optional
            The m/z of the first selected ion
        intensity: float, optional
            The intensity of the first selected ion
        charge: int, optional
            The charge state of the first seelcted ion
        spectrum_reference: str, optional
            The `id` of the prescursor `<spectrum>` for this precursor
        activation: dict, optional
            Parameters forwarded to :meth:`PrecursorBuilder.activation`
        isolation_window_args: tuple, list, or dict, optional
            Parameters forwarded to :meth:PrecursorBuilder.isolation_window`,
            tuple or list values are converted into :class:`dict` of the correct
            structure.
        params: list, optional
            The cv-params of the first selected ion
        intensity_unit: str
            The intensity unit of the first selected ion
        scan_id: str, optional
            An alias for `spectrum_reference`
        external_spectrum_id: str, optional
            The `externalSpectrumID` attribute of the precursor
        source_file_reference: str, optional
            The `sourceFileRef` attribute of the precursor

        Returns
        -------
        :class:`~.Precursor`
        '''
        if isinstance(mz, PrecursorBuilder):
            return self.Precursor(**mz.pack())
        if scan_id is not None:
            spectrum_reference = scan_id
        if params is None:
            params = []
        if activation:
            activation = self.Activation(activation)
        if any((mz, intensity, charge)):
            ion = self.SelectedIon(mz, intensity, charge, params=params)
            ion_list = self.SelectedIonList([ion])
        else:
            ion_list = None
        if isolation_window_args:
            isolation_window_tag = self.IsolationWindow(**isolation_window_args)
        else:
            isolation_window_tag = None
        precursor = self.Precursor(
            ion_list,
            activation=activation,
            isolation_window=isolation_window_tag,
            spectrum_reference=spectrum_reference)
        return precursor

    def precursor_builder(self, mz=None, intensity=None, charge=None, spectrum_reference=None, activation=None,
                          isolation_window_args=None, params=None,
                          intensity_unit=DEFAULT_INTENSITY_UNIT, scan_id=None,
                          external_spectrum_id=None,
                          source_file_reference=None):
        '''Create a :class:`PrecursorBuilder`, an object to help populate the precursor information
        data structure.

        Parameters
        ----------
        mz: float, optional
            The m/z of the first selected ion
        intensity: float, optional
            The intensity of the first selected ion
        charge: int, optional
            The charge state of the first seelcted ion
        spectrum_reference: str, optional
            The `id` of the prescursor `<spectrum>` for this precursor
        activation: dict, optional
            Parameters forwarded to :meth:`PrecursorBuilder.activation`
        isolation_window_args: tuple, list, or dict, optional
            Parameters forwarded to :meth:PrecursorBuilder.isolation_window`,
            tuple or list values are converted into :class:`dict` of the correct
            structure.
        params: list, optional
            The cv-params of the first selected ion
        intensity_unit: str
            The intensity unit of the first selected ion
        scan_id: str, optional
            An alias for `spectrum_reference`
        external_spectrum_id: str, optional
            The `externalSpectrumID` attribute of the precursor
        source_file_reference: str, optional
            The `sourceFileRef` attribute of the precursor

        Returns
        -------
        :class:`PrecursorBuilder`
        '''
        if scan_id is None:
            spectrum_reference = scan_id
        inst = PrecursorBuilder(
            self, spectrum_reference=spectrum_reference,
            external_spectrum_id=external_spectrum_id)
        if mz is not None or intensity is not None or charge is not None or params is not None:
            inst.selected_ion(
                mz=mz, intensity=intensity, charge=charge,
                intensity_unit=intensity_unit, params=params)
        if isolation_window_args is None:
            if isinstance(isolation_window_args, (tuple, list)):
                isolation_window_args = {
                    "lower": isolation_window_args[0],
                    "target": isolation_window_args[1],
                    "upper": isolation_window_args[2]}
            inst.isolation_window(isolation_window_args)
        if activation is not None:
            inst.activation(activation)
        return  inst


class SelectedIonBuilder(ElementBuilder):
    mz = ParamManagingProperty('selected_ion_mz', 0.0, aliases=['mz'])
    charge = ParamManagingProperty('charge')
    intensity = ParamManagingProperty('intensity', 0.0)
    intensity_unit = ParamManagingProperty(
        'intensity_unit', DEFAULT_INTENSITY_UNIT)


class IsolationWindowBuilder(ElementBuilder):
    lower = ParamManagingProperty('lower')
    target = ParamManagingProperty('target')
    upper = ParamManagingProperty('upper')


class ActivationBuilder(ElementBuilder):
    pass


class PrecursorBuilder(ElementBuilder):
    def __init__(self, source, binding=None, params=None, **kwargs):
        super(PrecursorBuilder, self).__init__(
            source, binding, params, **kwargs)

    selected_ion_list = ParamManagingProperty("selected_ion_list", list)
    _isolation_window = ParamManagingProperty("isolation_window")
    _activation = ParamManagingProperty('activation')

    spectrum_reference = ParamManagingProperty('spectrum_reference')
    source_file_reference = ParamManagingProperty('source_file_reference')
    external_spectrum_id = ParamManagingProperty('external_spectrum_id', aliases=['scan_id'])

    def selected_ion(self, binding=None, **kwargs):
        sib = SelectedIonBuilder(self.source, binding=binding, **kwargs)
        self.selected_ion_list.append(sib)
        return sib

    def isolation_window(self, binding=None, **kwargs):
        self._isolation_window = IsolationWindowBuilder(
            self.source, binding=binding, **kwargs)
        return self._isolation_window

    def activation(self, binding=None, **kwargs):
        self._activation = ActivationBuilder(
            self.source, binding=binding, **kwargs)
        return self._activation


class IndexedMzMLWriter(PlainMzMLWriter):
    def __init__(self, outfile, close=False, vocabularies=None, missing_reference_is_error=False,
                 vocabulary_resolver=None, id=None, accession=None, **kwargs):
        outfile = IndexingStream(outfile)
        super(IndexedMzMLWriter, self).__init__(
            outfile, close, vocabularies, missing_reference_is_error, vocabulary_resolver,
            id, accession, **kwargs)
        self.index_builder = outfile

    def toplevel_tag(self):
        return IndexedmzMLSection(
            self.writer, self.context, id=self.id, accession=self.accession,
            indexer=self.index_builder)

    def format(self, *args, **kwargs):
        return


MzMLWriter = IndexedMzMLWriter
# MzMLWriter = PlainMzMLWriter
