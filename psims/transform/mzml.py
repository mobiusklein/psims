from pyteomics import mzml

from psims import MzMLWriter
from psims.utils import ensure_iterable

from .utils import TransformerBase


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
    def __init__(self, input_stream, output_stream, transform=None, transform_description=None):
        if transform is None:
            transform = identity
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.transform = transform
        self.transform_description = transform_description
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
        for key, value in list(temp.items()):
            if not hasattr(key, 'accession'):
                continue
            accession = key.accession
            if accession == '' or accession is None:
                params.append({key: value})
                if hasattr(value, 'unit_info'):
                    params[-1]['unit_name'] = value.unit_info
                temp.pop(key)
            term = self.psims_cv[accession]
            if term.is_of_type("spectrum representation"):
                spec_data["centroided"] = term.id == "MS:1000127"
                temp.pop(key)
            elif term.is_of_type("spectrum attribute"):
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

    def write(self):
        writer = self.writer
        with writer:
            writer.controlled_vocabularies()
            self.copy_metadata()
            with writer.run(id="transformation_run"):
                with writer.spectrum_list(len(self.reader._offset_index)):
                    self.reader.reset()
                    i = 0
                    for spectrum in self.reader.iterfind("spectrum"):
                        spectrum = self.transform(spectrum)
                        self.writer.write_spectrum(**self.format_spectrum(spectrum))
                        i += 1
                        if i % 1000 == 0:
                            self.log("Handled %d spectra" % (i, ))
