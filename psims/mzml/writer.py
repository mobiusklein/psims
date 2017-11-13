from collections import Mapping, defaultdict
import numbers

import numpy as np

from psims.xml import XMLWriterMixin, XMLDocumentWriter

from .components import (
    ComponentDispatcher, element,
    default_cv_list, MzML, InstrumentConfiguration)

from .binary_encoding import (
    encode_array, COMPRESSION_NONE, COMPRESSION_ZLIB,
    encoding_map)

from .utils import ensure_iterable


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
    None: 'no compression',
    False: 'no compression',
    True: "zlib compression"
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
            "spectrumList", writer, parent_context, section_args=section_args,
            **kwargs)
        self.section_args.setdefault("count", 0)
        data_processing_method = self.section_args.pop(
            "data_processing_method", None)
        if data_processing_method is not None:
            self.section_args["defaultDataProcessingRef"] = self.context[
                "DataProcessing"][data_processing_method]


class ChromatogramListSection(DocumentSection):
    def __init__(self, writer, parent_context, section_args=None, **kwargs):
        super(ChromatogramListSection, self).__init__(
            "chromatogramList", writer, parent_context,
            section_args=section_args, **kwargs)
        self.section_args.setdefault("count", 0)
        data_processing_method = self.section_args.pop(
            "data_processing_method", None)
        if data_processing_method is not None:
            self.section_args["defaultDataProcessingRef"] = self.context[
                "DataProcessing"][data_processing_method]


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


class MzMLWriter(ComponentDispatcher, XMLDocumentWriter):
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
        A count of the number of spectrums written
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
        self.default_instrument_configuration = None

    def software_list(self, software_list):
        n = len(software_list)
        if n:
            software_list = [self.Software(**sw) for sw in ensure_iterable(software_list)]
        self.SoftwareList(software_list).write(self)

    def file_description(self, file_contents=None, source_files=None, params=None):
        """Writes the `<fileDescription>` section of the document using the
        provided parameters.

        From the specification:
        .. note::
            Information pertaining to the entire mzML file (i.e. not specific
            to any part of the data set) is stored here.

        Parameters
        ----------
        file_contents : list, optional
            A list or other iterable of str, dict, or *Param-types which will
            be placed in the `<fileContent>` element.
        source_files : list, optional
            A list or other iterable of dict or :class:`.SourceFile`-like objects
            to be placed in the `<sourceFileList>` element
        """
        with self.element("fileDescription"):
            if file_contents is not None:
                with self.element("fileContent"):
                    for param in file_contents:
                        self.param(param)(self)
            if source_files is not None:
                source_file_list = self.SourceFileList(
                    [self.SourceFile(**sf) for sf in ensure_iterable(source_files)])
                source_file_list.write(self)

    def instrument_configuration_list(self, instrument_configurations=None):
        configs = [
            self.InstrumentConfiguration(**ic) if not isinstance(
                ic, InstrumentConfiguration) else ic
            for ic in ensure_iterable(
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

    def sample_list(self, samples):
        for i, sample in enumerate(samples):
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

        sample_entries = [
            self.Sample(**sample) for sample in samples
        ]

        self.SampleList(sample_entries).write(self)

    def run(self, id=None, instrument_configuration=None, source_file=None, start_time=None,
            sample=None):
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
                       encoding=32, other_arrays=None, scan_params=None,
                       instrument_configuration_id=None):
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
        default_array_length = len(mz_array)
        if mz_array is not None:
            mz_array_tag = self._prepare_array(
                mz_array, encoding=encoding[MZ_ARRAY], compression=compression, array_type=MZ_ARRAY)
            array_list.append(mz_array_tag)

        if intensity_array is not None:
            intensity_array_tag = self._prepare_array(
                intensity_array, encoding=encoding[INTENSITY_ARRAY], compression=compression,
                array_type=INTENSITY_ARRAY)
            array_list.append(intensity_array_tag)

        if charge_array is not None:
            charge_array_tag = self._prepare_array(
                charge_array, encoding=encoding[CHARGE_ARRAY], compression=compression,
                array_type=CHARGE_ARRAY)
            array_list.append(charge_array_tag)
        for array_type, array in other_arrays:
            array_tag = self._prepare_array(
                array, encoding=encoding[array_type], compression=compression, array_type=array_type,
                default_array_length=default_array_length)
            array_list.append(array_tag)
        array_list_tag = self.BinaryDataArrayList(array_list)

        if precursor_information is not None:
            precursor_list = self._prepare_precursor_information(
                **precursor_information)
        else:
            precursor_list = None

        if scan_start_time is not None:
            if isinstance(scan_start_time, numbers.Number):
                scan_params.append({"name": "scan start time",
                                    "value": scan_start_time,
                                    "unitName": 'minute'})
            else:
                scan_params.append(scan_start_time)
        if self.default_instrument_configuration == instrument_configuration_id:
            instrument_configuration_id = None
        scan = self.Scan(params=scan_params, instrument_configuration_ref=instrument_configuration_id)
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

        if isinstance(encoding, Mapping):
            encoding = defaultdict(lambda: np.float32, encoding)
        else:
            # create new variable to capture in closure
            _encoding = encoding
            encoding = defaultdict(lambda: _encoding)

        if other_arrays is None:
            other_arrays = []
        array_list = []

        default_array_length = len(time_array)
        if time_array is not None:
            time_array_tag = self._prepare_array(
                time_array, encoding=encoding[TIME_ARRAY], compression=compression,
                array_type=TIME_ARRAY)
            array_list.append(time_array_tag)

        if intensity_array is not None:
            intensity_array_tag = self._prepare_array(
                intensity_array, encoding=encoding[INTENSITY_ARRAY], compression=compression,
                array_type=INTENSITY_ARRAY)
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
            default_array_length=default_array_length,
            id=id, params=params)
        chromatogram.write(self.writer)

    def _prepare_array(self, numeric, encoding=32, compression=COMPRESSION_ZLIB,
                       array_type=None, default_array_length=None):
        if isinstance(encoding, numbers.Number):
            _encoding = int(encoding)
        else:
            _encoding = encoding
            print(encoding)
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
            binary, encoded_length,
            array_length=(len(array) if override_length else None),
            params=params)

    def _prepare_precursor_information(self, mz, intensity, charge, scan_id, activation=None,
                                       isolation_window_args=None, params=None):
        if params is None:
            params = []
        if activation is not None:
            activation = self.Activation(activation)
        ion = self.SelectedIon(mz, intensity, charge, params=params)
        ion_list = self.SelectedIonList([ion])
        if isolation_window_args is not None:
            isolation_window_tag = self.IsolationWindow(**isolation_window_args)
        else:
            isolation_window_tag = None
        precursor = self.Precursor(
            ion_list,
            activation=activation,
            isolation_window=isolation_window_tag,
            spectrum_reference=scan_id)
        precursor_list = self.PrecursorList([precursor])
        return precursor_list
