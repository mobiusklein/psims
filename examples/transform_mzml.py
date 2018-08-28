from pyteomics import mzml
from pyteomics.auxiliary import cvquery

from psims import MzMLWriter


class MzMLReader(mzml.MzML):

    def _handle_param(self, element, **kwargs):
        try:
            element.attrib["value"]
        except KeyError:
            element.attrib["value"] = ""
        return super(MzMLReader, self)._handle_param(element, **kwargs)

    def reset(self):
        super(MzMLReader, self).reset()
        self.seek(0)


class ScanTransformer(object):
    def __init__(self, input_stream, output_stream, transform, transform_description=None):
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.transform = transform
        self.transform_description = transform_description
        self.reader = MzMLReader(input_stream, iterative=True)
        self.writer = MzMLWriter(output_stream)
        self.psims_cv = self.writer.get_vocabulary('PSI-MS').vocabulary

    def _format_instrument_configuration(self):
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

    def _format_data_processing(self):
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

        self.reader.reset()
        software_list = next(self.reader.iterfind("softwareList"))
        software_list = software_list.get("software", [])
        software_list.append({
            "id": "psims-example-ScanTransformer",
            "params": [
                self.writer.param("custom unreleased software tool", "psims-example-ScanTransformer"),
            ]
        })
        self.writer.software_list(software_list)

        configurations = self._format_instrument_configuration()
        self.writer.instrument_configuration_list(configurations)

        # include transformation description here
        data_processing = self._format_data_processing()
        data_processing.append({
            "id": "psims-example-ScanTransformer-processing",
            "processing_methods": [
                {
                    "order": 1,
                    "software_reference": "psims-example-ScanTransformer",
                    "params": ([self.transform_description] if self.transform_description else []
                               ) + ['conversion to mzML'],
                }
            ]
        })
        self.writer.data_processing_list(data_processing)

    def _format_spectrum(self, spectrum):
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
        term_dict = cvquery(spectrum)

        try:
            spec_data['polarity'] = spectrum.pop("positive scan")
        except KeyError:
            try:
                spec_data['polarity'] = spectrum.pop("negative scan")
            except KeyError:
                # don't know the polarity
                pass

        # strain out all the spectrm attribute parameters
        for key, value in list(term_dict.items()):
            try:
                term = self.psims_cv[key]
            except KeyError:
                continue
            if term.is_of_type("spectrum attribute"):
                params.append({"name": term.id, "value": value})
                if hasattr(value, 'unit_info'):
                    params[-1]['unit_name'] = value.unit_info
                term_dict.pop(key)
        for key, value in spectrum.items():
            if not hasattr(key, 'accession'):
                continue
            elif not key.accession:
                params.append({"name": key, "value": value})
                if hasattr(value, 'unit_info'):
                    params[-1]['unit_name'] = value.unit_info

        scan_params = []
        for key, value in list(term_dict.items()):
            try:
                term = self.psims_cv[key]
            except KeyError:
                continue

            if term.is_of_type("spectrum representation"):
                spec_data["centroided"] = term.id == "MS:1000127"
            elif term.is_of_type("scan attribute"):
                if term.name == 'scan start time':
                    spec_data['scan_start_time'] = {
                        "name": term.id, "value": value, "unit_name": getattr(value, 'unit_info', None)
                    }
                else:
                    scan_params.append({"name": term.id, "value": value})
                    if hasattr(value, 'unit_info'):
                        params[-1]['unit_name'] = value.unit_info
                term_dict.pop(key)

        spec_data['params'] = params
        spec_data['scan_params'] = scan_params

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
                precursor_information['activation'] = prec.get('activation', {}).items()
                precursor_information['isolation_window_args'] = prec.get("isolationWindow", {})
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
                    for spectrum in self.reader.iterfind("spectrum"):
                        spectrum = self.transform(spectrum)
                        self.writer.write_spectrum(**self._format_spectrum(spectrum))

        self.output_stream.seek(0)
        writer.format()
