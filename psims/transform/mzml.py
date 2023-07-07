"""
Transforming mzML Files
-----------------------

Often, we start with an mzML file we want to manipulate or change, but don't want to write out
explicitly unpacking it and re-packing it.

The :class:`MzMLTransformer` class is intended to give you a way to wrap an input file-like object
over an mzML file and an output file-like object to write the manipulated mzML file to, along with
a transformation function to modify spectra, and have it do the rest of the work. It uses :mod:`pyteomics.mzml`
to do the parsing internally.


Transformation Function Semantics
=================================

The transformation function passed receives a :class:`dict` object representing
the spectrum as parsed by :mod:`pyteomics.mzml` and expects the function to return
the dictionary modified or :const:`None` (in which case the spectrum is not written out).

You are free to modify existing keys in the spectrum dictionary, but *new* keys that are
intended to be recognized as either ``<cvParam />`` or ``<userParam />`` elements must
be instances of :class:`pyteomics.auxiliary.cvstr`, or otherwise have an "``accession``"
attribute to be picked up. Alternatively, the converter will make an effort to coerce keys
whose values which are scalars, or :class:`dict`s which look like parameters (having a "name"
or "accession" key, at least).

Alternatively, you can inherit from :class:`MzMLTransformer` and override :meth:`~.MzMLTransformer.format_spectrum`
to modify the spectrum before or after conversion (letting you directly append to the "params" key of the
converted spectrum and avoid needing to mark new params with :class:`cvstr`). Additionally, you
can override all other ``format_`` methods to customize how other elements are converted.


Usage and Examples
==================

In its simplest form, we would use the :class:`MzMLTransformer` like so:

.. code-block:: python

    from psims.transform.mzml import MzMLTransformer, cvstr

    def transform_drop_ms2(spectrum):
        if spectrum['ms level'] > 1:
            return None
        return spectrum

    with open("input.mzML", 'rb') as in_stream, open("ms1_only.mzML", 'wb') as out_stream:
        MzMLTransformer(in_stream, out_stream, transform_drop_ms2).write()



"""
from numbers import Number
from pyteomics import mzml

from psims import MzMLWriter, MzMLbWriter
from psims.utils import ensure_iterable

from .utils import TransformerBase, cvstr


class MzMLParser(mzml.MzML):

    def _handle_param(self, element, **kwargs):
        try:
            element.attrib["value"]
        except KeyError:
            element.attrib["value"] = ""
        return super(MzMLParser, self)._handle_param(element, **kwargs)

    def reset(self):
        super(MzMLParser, self).reset()
        self.seek(0)


def identity(x):
    return x


class MzMLTransformer(TransformerBase):
    """
    Reads an mzML file stream from :attr:`input_stream`, copying its metadata
    to :attr:`output_stream`, and then copies its spectra, applying :attr:`transform`
    to each spectrum object as it goes.

    If :attr:`sort_by_by_scan_time` is :const:`True`, then prior to writing spectra,
    a first pass will be made over the mzML file and the spectra will be written out
    ordered by ``MS:1000016|scan start time``.

    Attributes
    ----------
    input_stream : file-like
        A byte stream from an mzML format data buffer
    output_stream : file-like
        A writable binary stream to copy the contents of :attr:`input_stream` into
    sort_by_scan_time : :class:`bool`
        Whether or not to sort spectra by scan time prior to writing
    transform : :class:`Callable`, optional
        A function to call on each spectrum, passed as a :class:`dict` object as
        read by :class:`pyteomics.mzml.MzML`. A spectrum will be skipped if this function
        returns :const:`None`.
    transform_description : :class:`str`
        A description of the transformation to include in the written metadata

    Parameters
    ----------
    input_stream : path or file-like
        A byte stream from an mzML format data buffer
    output_stream : path or file-like
        A writable binary stream to copy the contents of :attr:`input_stream` into
    transform : :class:`Callable`, optional
        A function to call on each spectrum, passed as a :class:`dict` object as
        read by :class:`pyteomics.mzml.MzML`.
    transform_description : :class:`str`
        A description of the transformation to include in the written metadata
    sort_by_scan_time : :class:`bool`
        Whether or not to sort spectra by scan time prior to writing
    """

    def __init__(self, input_stream, output_stream, transform=None, transform_description=None,
                 sort_by_scan_time=False):
        if transform is None:
            transform = identity
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.transform = transform
        self.transform_description = transform_description
        self.sort_by_scan_time = sort_by_scan_time
        self.reader = MzMLParser(input_stream, iterative=True)
        self.writer = MzMLWriter(output_stream)
        self.psims_cv = self.writer.get_vocabulary('PSI-MS').vocabulary

    def format_referenceable_param_groups(self):
        self.reader.reset()
        try:
            param_list = next(self.reader.iterfind("referenceableParamGroupList", recursive=True, retrive_refs=False))
            param_groups = ensure_iterable(param_list.get("referenceableParamGroup", []))
        except StopIteration:
            param_groups = []
        return [self.writer.ReferenceableParamGroup.ensure(d) for d in param_groups]

    def format_instrument_configuration(self):
        self.reader.reset()
        configuration_list = next(self.reader.iterfind("instrumentConfigurationList", recursive=True))
        configurations = []
        for config_dict in configuration_list.get("instrumentConfiguration", []):
            components = []
            for key, members in config_dict.pop('componentList', {}).items():
                if key not in ("source", "analyzer", "detector"):
                    continue
                if key == 'source':
                    components.extend(self.writer.Source.ensure(m) for m in members)
                elif key == "analyzer":
                    components.extend(self.writer.Analyzer.ensure(m) for m in members)
                elif key == 'detector':
                    components.extend(self.writer.Detector.ensure(m) for m in members)
            components.sort(key=lambda x: x.order)
            software_reference = config_dict.pop("softwareRef", {}).get("ref")
            configuration = self.writer.InstrumentConfiguration(
                component_list=components, software_reference=software_reference, **config_dict)
            configurations.append(configuration)
        return configurations

    def format_data_processing(self):
        self.reader.reset()
        dpl = next(self.reader.iterfind("dataProcessingList", recursive=True))
        data_processing = []
        for dp_dict in dpl.get("dataProcessing", []):
            methods = []
            for pm in dp_dict.pop("processingMethod", []):
                pm['software_reference'] = pm.pop("softwareRef")
                methods.append(self.writer.ProcessingMethod.ensure(pm))
            dp_dict['processing_methods'] = methods
            data_processing.append(self.writer.DataProcessing.ensure(dp_dict))
        return data_processing

    def copy_metadata(self):
        self.reader.reset()
        file_description = next(self.reader.iterfind("fileDescription"))
        source_files = file_description.get("sourceFileList").get('sourceFile')
        self.writer.file_description(file_description.get("fileContent", {}).items(), source_files)

        param_groups = self.format_referenceable_param_groups()
        if param_groups:
            self.writer.reference_param_group_list(param_groups)

        self.reader.reset()
        software_list = next(self.reader.iterfind("softwareList"))
        software_list = software_list.get("software", [])
        software_list.append(self._make_software())
        self.writer.software_list(software_list)

        configurations = self.format_instrument_configuration()
        self.writer.instrument_configuration_list(configurations)

        # include transformation description here
        data_processing = self.format_data_processing()
        data_processing.append(self._make_data_processing_entry())
        self.writer.data_processing_list(data_processing)

    def _make_software(self):
        description = {
            "id": "psims-MzMLTransformer",
            "params": [
                self.writer.param("python-psims"),
            ]
        }
        return description

    def _make_data_processing_entry(self):
        description = {
            "id": "psims-MzMLTransformer-processing",
            "processing_methods": [
                {
                    "order": 1,
                    "software_reference": "psims-MzMLTransformer",
                    "params": ([self.transform_description] if self.transform_description else []
                               ) + ['conversion to mzML'],
                }
            ]
        }
        return description

    def format_scan(self, scan):
        scan_params = []
        scan_window_list = []
        scan_start_time = None

        temp = scan.copy()

        for key, value in list(temp.items()):
            if not hasattr(key, 'accession'):
                continue
            accession = key.accession
            if accession == '' or accession is None:
                scan_params.append({key: value})
                if hasattr(value, 'unit_info'):
                    scan_params[-1]['unit_name'] = value.unit_info
                temp.pop(key)
                continue
            term = self.psims_cv[accession]
            if term.is_of_type("scan attribute"):
                if term.name == 'scan start time':
                    scan_start_time = {
                        "name": term.id, "value": value, "unit_name": getattr(value, 'unit_info', None)
                    }
                else:
                    scan_params.append({"name": term.id, "value": value})
                    if hasattr(value, 'unit_info'):
                        scan_params[-1]['unit_name'] = value.unit_info
                temp.pop(key)
        temp = temp.get('scanWindowList', {}).get('scanWindow', [{}])[0].copy()
        for key, value in list(temp.items()):
            if not hasattr(key, 'accession'):
                continue
            accession = key.accession
            term = self.psims_cv[accession]
            if term.is_of_type("selection window attribute"):
                scan_window_list.append(
                    {"name": term.id, "value": value})
                if hasattr(value, 'unit_info'):
                    scan_window_list[-1]['unit_name'] = value.unit_info
                temp.pop(key)

        scan_window_list.sort(key=lambda x: x['value'])
        if len(scan_window_list) % 2 == 0:
            windows = []
            i = 0
            n = len(scan_window_list)
            while i < n:
                lo = scan_window_list[i]
                hi = scan_window_list[i + 1]
                windows.append((lo['value'], hi['value']))
                i += 2
            scan_window_list = windows
        else:
            scan_window_list = []

        return scan_start_time, scan_params, scan_window_list

    def format_spectrum(self, spectrum):
        spec_data = dict()
        spec_data["mz_array"] = spectrum.pop("m/z array", None)
        spec_data["intensity_array"] = spectrum.pop("intensity array", None)
        spec_data["charge_array"] = spectrum.pop("charge array", None)

        spec_data['encoding'] = {
            "m/z array": spec_data["mz_array"].dtype.type if spec_data.get('mz_array') is not None else None,
            "intensity array": spec_data["intensity_array"].dtype.type if spec_data.get(
                'intensity_array') is not None else None,
            "charge array": spec_data["charge_array"].dtype.type if spec_data.get(
                'charge_array') is not None else None
        }

        spec_data['id'] = spectrum["id"]
        params = []

        if "positive scan" in spectrum:
            spec_data['polarity'] = 1
        elif "negative scan" in spectrum:
            spec_data['polarity'] = -1
        else:
            spec_data['polarity'] = None

        temp = spectrum.copy()
        attrs_to_skip = {'id', 'index', 'sourceFileRef',
                 'defaultArrayLength', 'dataProcessingRef', 'count'}
        for key, value in list(temp.items()):
            accession = None
            if not hasattr(key, 'accession'):
                # Guess if this is looks like it could be a param tag or was added by the user
                if isinstance(value, dict) and ("name" in value or "accession" in value):
                    pass
                elif isinstance(value, list):
                    continue
                elif isinstance(value, (str, int, float, Number)) and key not in attrs_to_skip:
                    pass
                else:
                    continue
            else:
                accession = key.accession
            if accession == '' or accession is None:
                if isinstance(value, dict):
                    params.append(value)
                else:
                    params.append({key: value})
                if hasattr(value, 'unit_info'):
                    params[-1]['unit_name'] = value.unit_info
                temp.pop(key)
            else:
                term = self.psims_cv[accession]
                if term.is_of_type("spectrum representation"):
                    spec_data["centroided"] = term.id == "MS:1000127"
                    temp.pop(key)
                elif term.is_of_type("spectrum property") or term.is_of_type("spectrum attribute"):
                    params.append({"name": term.id, "value": value})
                    if hasattr(value, 'unit_info'):
                        params[-1]['unit_name'] = value.unit_info
                    temp.pop(key)

        spec_data["scan_start_time"], spec_data['scan_params'], spec_data["scan_window_list"] = self.format_scan(
            spectrum.get("scanList", {}).get('scan', [{}])[0])

        spec_data['params'] = params

        precursors = spectrum.get("precursorList", {}).get("precursor")
        if precursors:
            precursor_list = []
            for prec in precursors:
                precursor_information = {}
                precursor_information['scan_id'] = prec.get("spectrumRef")
                ion = prec['selectedIonList'].get("selectedIon")[0]
                for key, value in list(ion.items()):
                    term = self.psims_cv[key]
                    if term.id == "MS:1000744":
                        precursor_information['mz'] = value
                        ion.pop(key)
                    elif term.id == "MS:1000042":
                        precursor_information['intensity'] = value
                        ion.pop(key)
                    elif term.id in ("MS:1000041", "MS:1000633"):
                        precursor_information['charge'] = value
                        ion.pop(key)
                precursor_information.setdefault("intensity", None)
                precursor_information.setdefault("charge", None)
                precursor_information['params'] = ion.items()
                precursor_information['activation'] = (prec.get('activation', {}).items())
                precursor_information['isolation_window_args'] = prec.get("isolationWindow", None)
                precursor_list.append(precursor_information)

        else:
            precursor_list = None
        spec_data['precursor_information'] = precursor_list
        # attempt to find the instrumentConfiguration id to reference
        try:
            spec_data['instrument_configuration_id'] = spectrum.get(
                "scanList", {}).get("scan")[0].get("instrumentConfigurationRef")
        except IndexError:
            pass
        return spec_data

    def iterspectrum(self):
        self.reader.reset()
        if self.sort_by_scan_time:
            time_map = dict()
            self.log("Building Scan Time Map")
            for spectrum in self.reader.iterfind("spectrum"):
                time = self.reader._get_time(spectrum)
                time_map[spectrum['id']] = time
            self.reader.reset()
            by_time = sorted(time_map.items(), key=lambda x: x[1])
            generate = (self.reader.get_by_id(spectrum_id) for spectrum_id, _ in by_time)
            return generate
        else:
            return self.reader.iterfind("spectrum")

    def write(self):
        '''Write out the the transformed mzML file
        '''
        writer = self.writer
        with writer:
            writer.controlled_vocabularies()
            self.copy_metadata()
            with writer.run(id="transformation_run"):
                with writer.spectrum_list(len(self.reader._offset_index)):
                    self.reader.reset()
                    for i, spectrum in enumerate(self.iterspectrum()):
                        spectrum = self.transform(spectrum)
                        if spectrum is None:
                            continue
                        self.writer.write_spectrum(**self.format_spectrum(spectrum))
                        if i % 1000 == 0:
                            self.log("Handled %d spectra" % (i, ))
                    self.log("Handled %d spectra" % (i, ))


class MzMLToMzMLb(MzMLTransformer):
    """
    Convert an mzML document into an mzMLb file, with an optional transformation along
    the way.

    Parameters
    ----------
    input_stream : path or file-like
        A byte stream from an mzML format data buffer
    output_stream : path or file-like
        A writable binary stream to copy the contents of :attr:`input_stream` into
    transform : :class:`Callable`, optional
        A function to call on each spectrum, passed as a :class:`dict` object as
        read by :class:`pyteomics.mzml.MzML`.
    transform_description : :class:`str`
        A description of the transformation to include in the written metadata
    sort_by_scan_time : :class:`bool`
        Whether or not to sort spectra by scan time prior to writing
    h5_compression : :class:`str`, optional
        The name of the HDF5 compression method to use. Defaults to
        :const:`psims.mzmlb.writer.DEFAULT_COMPRESSOR`
    h5_compression_opts : :class:`tuple` or :class:`int`, optional
        The configuration options for the selected compressor. For "gzip",
        this a single integer setting the compression level, while Blosc takes
        a tuple of integers.
    h5_blocksize : :class:`int`, optional
        The size of the compression blocks used when building the HDF5 file.
        Smaller blocks improve random access speed at the expense of compression
        efficiency and space. Defaults to 2 ** 20, 1MB.
    """

    def __init__(self, input_stream, output_stream, transform=None, transform_description=None,
                 sort_by_scan_time=False, **hdf5args):
        if transform is None:
            transform = identity
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.transform = transform
        self.transform_description = transform_description
        self.sort_by_scan_time = sort_by_scan_time
        self.reader = MzMLParser(input_stream, iterative=True)
        self.writer = MzMLbWriter(output_stream, **hdf5args)
        self.psims_cv = self.writer.get_vocabulary('PSI-MS').vocabulary
