import warnings
from datetime import datetime
try:
    from collections import Mapping, Iterable
except ImportError:
    from collections.abc import Mapping, Iterable
from numbers import Number

import numpy as np

from ..xml import _element, element, TagBase, CV
from ..document import (
    ComponentBase as _ComponentBase, NullMap, ComponentDispatcherBase,
    ParameterContainer, IDParameterContainer)
from .binary_encoding import (dtype_to_encoding, compression_map, encode_array)
from .utils import ensure_iterable


class MzML(TagBase):
    type_attrs = {
        "xmlns": "http://psi.hupo.org/ms/mzml",
        "version": "1.1.0",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://psi.hupo.org/ms/mzml http://psidev.info/files/ms/mzML/xsd/mzML1.1.0.xsd"
    }

    def __init__(self, **attrs):
        super(MzML, self).__init__("mzML", **attrs)


_COMPONENT_NAMESPACE = 'mzml'
_xmlns = "http://psidev.info/psi/pi/mzML/1.1"


class ComponentDispatcher(ComponentDispatcherBase):
    def __init__(self, *args, **kwargs):
        super(ComponentDispatcher, self).__init__(
            *args, component_namespace=_COMPONENT_NAMESPACE, **kwargs)


class ComponentBase(_ComponentBase):
    component_namespace = _COMPONENT_NAMESPACE


default_cv_list = [
    CV(id="PSI-MS",
       uri=("https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo"),
       full_name="PSI-MS"),
    CV(id="UO",
       uri="http://ontologies.berkeleybop.org/uo.obo",
       full_name="UNIT-ONTOLOGY"),
]


class GenericCollection(ComponentBase):
    def __init__(self, tag_name, members, context=NullMap):
        self.members = members
        self.tag_name = tag_name
        self.element = _element(tag_name, count=len(self.members))

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            for member in self.members:
                member.write(xml_file)

    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, i):
        return self.members[i]


class IDGenericCollection(GenericCollection):
    def __init__(self, tag_name, members, id, context=NullMap):
        self.members = members
        self.tag_name = tag_name
        self.element = _element(tag_name, id=id, count=len(self.members))
        context[tag_name][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for member in self.members:
                member.write(xml_file)


# --------------------------------------------------
# File Metadata


class FileContent(ComponentBase):
    def __init__(self, params=None, context=NullMap, **kwargs):
        self.params = self.prepare_params(params, **kwargs)
        self.element = _element("fileContent")
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file):
            self.write_params(xml_file)


class SourceFileList(GenericCollection):
    def __init__(self, members, context):
        super(SourceFileList, self).__init__("sourceFileList", members, context)


class SourceFile(ComponentBase):
    def __init__(self, location=None, name=None, id=None, params=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        params.extend(kwargs.items())
        self.location = location
        self.name = name
        self.element = _element("sourceFile", location=location, id=id, name=name)
        self.params = params
        self.context = context
        context["SourceFile"][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            self.write_params(xml_file)


class FileDescription(ComponentBase):
    def __init__(self, content, source_files, contacts=None, context=NullMap):
        if not isinstance(content, FileContent):
            content = FileContent(content, context=context)
        if not isinstance(source_files, SourceFileList):
            if len(source_files) > 0 and not isinstance(source_files[0], SourceFile):
                source_files = [SourceFile(context=context, **f) for f in source_files]
            source_files = SourceFileList(source_files, context=context)
        contacts = ensure_iterable(contacts)
        if contacts and not isinstance(contacts[0], Contact):
            contacts = [Contact.ensure(contact, context=context) for contact in contacts]
        self.content = content
        self.source_files = source_files
        self.contacts = contacts
        self.context = context
        self.element = _element("fileDescription")

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            self.content.write(xml_file)
            self.source_files.write(xml_file)
            for contact in self.contacts:
                contact.write(xml_file)


# --------------------------------------------------
# ParamGroups

class ReferenceableParamGroupList(GenericCollection):
    def __init__(self, members, context):
        super(ReferenceableParamGroupList, self).__init__(
            "referenceableParamGroupList", members, context)


class ReferenceableParamGroup(IDParameterContainer):
    def __init__(self, params=None, id=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        super(ReferenceableParamGroup, self).__init__(
            "referenceableParamGroup", params, dict(id=id), context=context, **kwargs)
        self.id = self.element.id
        self.context = context
        self.context["ReferenceableParamGroup"][id] = self.element.id

# --------------------------------------------------
# Sample Metadata


class SampleList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(SampleList, self).__init__("sampleList", members, context)


class Sample(IDParameterContainer):
    def __init__(self, name, params=None, id=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        params.extend(kwargs.items())
        super(Sample, self).__init__("sample", params, dict(name=name, id=id), context)
        self.name = name
        self.id = self.element.id
        context["Sample"][id] = self.element.id

# --------------------------------------------------
# Software Processing Metadata


class SoftwareList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(SoftwareList, self).__init__("softwareList", members, context)


class Software(IDParameterContainer):
    def __init__(self, id=None, version="0.0", params=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        params.extend(kwargs.items())
        super(Software, self).__init__(
            "software", params, dict(id=id, version=version), context=context)
        self.version = version
        self.id = self.element.id
        context['Software'][id] = self.element.id

    @property
    def with_id(self):
        return True


# --------------------------------------------------
# Scan Settings Metadata


class ScanSettingsList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(ScanSettingsList, self).__init__("scanSettingsList", members, context)


class ScanSettings(ComponentBase):
    def __init__(self, id=None, source_file_references=None, target_list=None, params=None, context=NullMap):
        if source_file_references is None:
            source_file_references = []
        if target_list is None:
            target_list = []
        if params is None:
            params = []
        self.params = params
        self.source_file_references = source_file_references
        self.target_list = target_list
        self.element = _element("scanSettings", id=id)
        self.id = self.element.id
        self.context = context
        context['ScanSettings'][id] = self.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            source_refs = GenericCollection(
                "sourceFileRefList",
                [_element("sourceFileRef", ref=i) for i in self.source_file_references])
            if len(source_refs):
                source_refs.write(xml_file)
            # TODO handle targetList and targets
            self.write_params(xml_file)


# --------------------------------------------------
# Instrument Configuration Metadata

class InstrumentConfigurationList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(InstrumentConfigurationList, self).__init__("instrumentConfigurationList", members, context)


class InstrumentConfiguration(ComponentBase):
    def __init__(self, id, component_list=None, params=None,
                 software_reference=None, context=NullMap):
        if params is None:
            params = []
        if not isinstance(component_list, ComponentList):
            component_list = ComponentList(component_list, context=context)
        self.params = params
        self.software_reference = software_reference
        self._software_reference = context['Software'][software_reference]
        self.component_list = component_list
        self.element = _element(
            "instrumentConfiguration", id=id)
        self.context = context
        self.context['InstrumentConfiguration'][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            self.write_params(xml_file)
            if self.component_list is not None:
                self.component_list.write(xml_file)
            if self.software_reference is not None:
                _element("softwareRef", ref=self._software_reference).write(xml_file)


class ComponentList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(ComponentList, self).__init__("componentList", members, context)

    @classmethod
    def build(cls, members, context=NullMap, type_key='type'):
        components = []
        for component in sorted(members, key=lambda x: int(x['order'])):
            if component[type_key] == 'source':
                components.append(
                    Source(int(component['order']), component['params'], context))
            elif component[type_key] == 'analyzer':
                components.append(
                    Analyzer(int(component['order']), component['params'], context))
            elif component[type_key] == 'detector':
                components.append(
                    Detector(int(component['order']), component['params'], context))
            else:
                raise KeyError("Unknown component %s" % component[type_key])
        return cls(components, context=context)


class Source(ParameterContainer):
    def __init__(self, order, params=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        params.extend(kwargs.items())
        super(Source, self).__init__(
            "source", params, dict(order=order), context=context)
        self.order = order


class Analyzer(ParameterContainer):
    def __init__(self, order, params=None, context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        super(Analyzer, self).__init__("analyzer", params, dict(order=order), context=context)
        self.order = order


class Detector(ParameterContainer):
    def __init__(self, order, params=None, context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        super(Detector, self).__init__("detector", params, dict(order=order), context=context)
        self.order = order


# --------------------------------------------------
# Data Processing Metadata


class DataProcessingList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(DataProcessingList, self).__init__("dataProcessingList", members, context)


class DataProcessing(ComponentBase):
    def __init__(self, processing_methods=None, id=None, context=NullMap):
        if processing_methods is None:
            processing_methods = []
        if processing_methods and not isinstance(processing_methods[0], ProcessingMethod):
            processing_methods = [ProcessingMethod(context=context, **m) for m in (
                processing_methods)]
        self.processing_methods = processing_methods
        self.element = _element("dataProcessing", id=id)
        self.context = context
        context['DataProcessing'][id] = self.element.id

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for method in self.processing_methods:
                method.write(xml_file)


class ProcessingMethod(ParameterContainer):
    def __init__(self, order, software_reference, params=None, context=NullMap, **kwargs):
        params = self.prepare_params(params, **kwargs)
        self.order = order
        self.software_reference = software_reference
        self._software_reference = context['Software'][software_reference]
        self.element = _element("processingMethod", order=order, softwareRef=self._software_reference)
        self.params = params
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            self.write_params(xml_file)

# --------------------------------------------------
# Spectral and Chromatographic Data Storage


class SpectrumList(ComponentBase):
    def __init__(self, members, default_data_processing_reference, context=NullMap):
        self.members = members
        self.default_data_processing_reference = default_data_processing_reference
        self._default_data_processing_reference = context["DataProcessing"][default_data_processing_reference]
        self.element = _element(
            "spectrumList", count=len(self.members), defaultDataProcessingRef=self._default_data_processing_reference)
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            for member in self.members:
                member.write(xml_file)


class Spectrum(ComponentBase):
    def __init__(self, index, binary_data_list=None, scan_list=None, precursor_list=None, product_list=None,
                 default_array_length=None, source_file_reference=None, data_processing_reference=None,
                 id=None, params=None, context=NullMap, **kwargs):
        if params is None:
            params = []
        self.index = index
        self.binary_data_list = binary_data_list
        self.scan_list = scan_list
        self.data_processing_reference = data_processing_reference
        self._data_processing_reference = context["DataProcessing"][data_processing_reference]
        self.precursor_list = precursor_list
        self.product_list = product_list
        self.default_array_length = default_array_length
        self.source_file_reference = source_file_reference
        self._source_file_reference = context["SourceFile"][source_file_reference]
        self.element = _element(
            "spectrum", id=id, index=index, sourceFileRef=self._source_file_reference,
            defaultArrayLength=self.default_array_length, dataProcessingRef=self._data_processing_reference)
        self.context = context
        self.context["Spectrum"][id] = self.element.id
        self.params = self.prepare_params(params, **kwargs)
        self._check_params()

    def _check_params(self):
        ms_level = None
        spectrum_type = None
        for param in self.params:
            param = self.context.param(param)
            try:
                term = self.context.term(param.accession)
            except (AttributeError, KeyError):
                continue
            if term.id == 'MS:1000511':
                ms_level = int(param.value)
            elif term.id == 'MS:1000579' or term.id == 'MS:1000580':
                spectrum_type = term.name
        if ms_level is not None and spectrum_type is None:
            spectrum_type = "MS:1000579" if ms_level == 1 else "MS:1000580"
            self.params.append(self.context.param(spectrum_type))
        elif spectrum_type is not None and ms_level is None:
            if spectrum_type == 'MS:1000579':
                self.params.append(self.context.param(accession='MS:1000511', value=1))
            else:
                raise ValueError("A spectrum without MS:100511 'ms level' and cannot "
                                 "be determined from other parameters")

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            self.write_params(xml_file)
            if self.scan_list is not None:
                self.scan_list.write(xml_file)
            if self.precursor_list is not None:
                self.precursor_list.write(xml_file)
            if self.product_list is not None:
                self.product_list.write(xml_file)
            self.binary_data_list.write(xml_file)


class Run(ComponentBase):
    def __init__(self, default_instrument_configuration_reference, spectrum_list=None, chromatogram_list=None, id=None,
                 default_source_file_reference=None, sample_reference=None, start_time_stamp=None, params=None,
                 context=NullMap):
        if params is None:
            params = []
        if spectrum_list is None:
            spectrum_list = []
        if chromatogram_list is None:
            chromatogram_list = []
        self.params = params
        self.spectrum_list = spectrum_list
        self.chromatogram_list = chromatogram_list
        self.sample_reference = sample_reference
        self._sample_reference = context["Sample"][sample_reference]
        self.default_instrument_configuration_reference = default_instrument_configuration_reference
        self._default_instrument_configuration_reference = context["InstrumentConfiguration"][
            default_instrument_configuration_reference]
        self.default_source_file_reference = default_source_file_reference
        self._default_source_file_reference = context["SourceFile"][default_source_file_reference]
        self.start_time_stamp = start_time_stamp
        self.element = _element(
            "run", id=id, defaultInstrumentConfigurationRef=self._default_instrument_configuration_reference,
            defaultSourceFileRef=self._default_source_file_reference, sampleRef=self._sample_reference,
            startTimeStamp=start_time_stamp)
        self.context = context


class BinaryDataArrayList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(BinaryDataArrayList, self).__init__("binaryDataArrayList", members, context)


class BinaryDataArray(ComponentBase):
    def __init__(self, binary, encoded_length, data_processing_reference=None, array_length=None,
                 params=None, context=NullMap):
        if params is None:
            params = []
        self.encoded_length = encoded_length
        self.data_processing_reference = data_processing_reference
        self._data_processing_reference = context["DataProcessing"][data_processing_reference]
        self.array_length = array_length
        self.params = params
        self.binary = binary

        self.element = _element(
            "binaryDataArray", arrayLength=array_length, encodedLength=encoded_length,
            dataProcessingRef=self._data_processing_reference)
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            self.write_params(xml_file)
            self.binary.write(xml_file)

    @classmethod
    def from_array(cls, data_array, compression=None, params=None, context=None):
        if params is None:
            params = []
        if context is None:
            context = NullMap
        compression = compression_map[compression]
        encoded_binary = encode_array(
            data_array, compression=compression, dtype=data_array.dtype.type)
        binary = Binary(encoded_binary)
        array_length = len(data_array)
        params.append(compression_map[compression])
        params.append(dtype_to_encoding[data_array.dtype.type])
        encoded_length = len(encoded_binary)
        inst = cls(
            binary, encoded_length,
            array_length=array_length,
            params=params, context=context)
        return inst


class Binary(ComponentBase):
    def __init__(self, encoded_array, context=NullMap):
        self.encoded_array = encoded_array
        self.context = context
        self.element = _element("binary", text=encoded_array)

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            xml_file.write(self.encoded_array)


class ScanList(ComponentBase):
    def __init__(self, members, params=None, context=NullMap):
        if params is None:
            params = []
        self.members = members
        self.params = params
        self.element = _element("scanList", count=len(self.members))
        self.context = context

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            self.write_params(xml_file)
            for member in self.members:
                member.write(xml_file)


class Scan(ComponentBase):
    def __init__(self, scan_window_list=None, instrument_configuration_ref=None, params=None,
                 context=NullMap, **kwargs):
        if scan_window_list is None:
            scan_window_list = ScanWindowList([], context)
        elif not isinstance(scan_window_list, ScanWindowList):
            scan_window_list = ScanWindowList(scan_window_list, context)
        self.instrument_configuration_ref = instrument_configuration_ref
        self._instrument_configuration_ref = context['InstrumentConfiguration'].get(instrument_configuration_ref)
        self.params = self.prepare_params(params, **kwargs)
        self.scan_window_list = scan_window_list
        self.element = _element("scan")
        if self._instrument_configuration_ref is not None:
            self.element.attrs['instrumentConfigurationRef'] = self._instrument_configuration_ref
        self.context = context

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            self.write_params(xml_file)
            if len(self.scan_window_list) > 0:
                self.scan_window_list.write(xml_file)


class ScanWindowList(GenericCollection):
    def __init__(self, members, context=NullMap):
        components = []
        for member in members:
            if isinstance(member, (list, tuple)):
                components.append(ScanWindow(*member, context=context))
            elif isinstance(member, Mapping):
                components.append(ScanWindow(context=context, **member))
            else:
                components.append(member)
        super(ScanWindowList, self).__init__('scanWindowList', components, context=context)


class ScanWindow(ComponentBase):
    def __init__(self, lower, upper, params=None, context=NullMap):
        if params is None:
            params = []
        self.lower = lower
        self.upper = upper
        self.params = params
        self.element = _element("scanWindow")
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            self.context.param(name="scan window lower limit", value=self.lower,
                               unit_name='m/z', unit_accession="MS:1000040", unit_cv_ref='MS')(xml_file)
            self.context.param(name="scan window upper limit", value=self.upper,
                               unit_name='m/z', unit_accession="MS:1000040", unit_cv_ref='MS')(xml_file)
            self.write_params(xml_file)


class IsolationWindow(ComponentBase):
    def __init__(self, lower, target, upper, params=None, context=NullMap):
        if params is None:
            params = []
        self.target = target
        self.lower = lower
        self.upper = upper
        self.element = _element("isolationWindow")
        self.context = context
        self.params = params

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            self.context.param(name="isolation window target m/z", value=self.target,
                               unit_name='m/z', unit_accession="MS:1000040",
                               unit_cv_ref="MS")(xml_file)
            self.context.param(name="isolation window lower offset", value=self.lower,
                               unit_name='m/z', unit_accession="MS:1000040",
                               unit_cv_ref="MS")(xml_file)
            self.context.param(name="isolation window upper offset", value=self.upper,
                               unit_name='m/z', unit_accession="MS:1000040",
                               unit_cv_ref="MS")(xml_file)
            self.write_params(xml_file)


class PrecursorList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(PrecursorList, self).__init__('precursorList', members, context=context)


class Precursor(ComponentBase):
    def __init__(self, selected_ion_list, activation, isolation_window=None, spectrum_reference=None, context=NullMap):
        if isolation_window is not None:
            if isinstance(isolation_window, (tuple, list)):
                isolation_window = IsolationWindow(*isolation_window, context=context)
            elif isinstance(isolation_window, Mapping):
                isolation_window = IsolationWindow(context=context, **isolation_window)
        self.selected_ion_list = selected_ion_list
        self.activation = activation
        self.isolation_window = isolation_window
        self.spectrum_reference = spectrum_reference
        self._spectrum_reference = context["Spectrum"][spectrum_reference]
        self.element = _element("precursor", spectrumRef=self._spectrum_reference)
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            if self.isolation_window is not None:
                self.isolation_window.write(xml_file)
            self.selected_ion_list.write(xml_file)
            if self.activation is not None:
                self.activation.write(xml_file)


class ProductList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(ProductList, self).__init__('productList', members, context=context)


class Product(ComponentBase):
    def __init__(self, isolation_window=None, spectrum_reference=None, context=NullMap):
        if isolation_window is not None:
            if isinstance(isolation_window, (tuple, list)):
                isolation_window = IsolationWindow(*isolation_window, context=context)
            elif isinstance(isolation_window, Mapping):
                isolation_window = IsolationWindow(context=context, **isolation_window)
        self.isolation_window = isolation_window
        self.element = _element("product")
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            if self.isolation_window is not None:
                self.isolation_window.write(xml_file)


class Activation(ParameterContainer):
    def __init__(self, params, context=NullMap):
        super(Activation, self).__init__("activation", params, context=context)


class SelectedIonList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(SelectedIonList, self).__init__("selectedIonList", members, context=context)


class SelectedIon(ComponentBase):
    def __init__(self, selected_ion_mz, intensity=None, charge=None, params=None, context=NullMap):
        if params is None:
            params = []
        self.selected_ion_mz = selected_ion_mz
        self.intensity = intensity
        self.charge = charge
        self.params = params
        self.element = _element("selectedIon")
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file):
            if self.selected_ion_mz is not None:
                self.context.param(name="selected ion m/z", value=self.selected_ion_mz)(xml_file)
            if self.intensity is not None:
                self.context.param(name="peak intensity", value=self.intensity)(xml_file)
            if self.charge is not None:
                if isinstance(self.charge, Number):
                    self.context.param(name="charge state", value=int(self.charge))(xml_file)
                elif isinstance(self.charge, Iterable):
                    self.context.param(name="charge state", value=' '.join(map(str, self.charge)))(xml_file)
                else:
                    warnings.warn("Invalid charge state provided (%r)" % (self.charge,))
            self.write_params(xml_file)


class Chromatogram(ComponentBase):
    def __init__(self, index, binary_data_list=None, precursor=None, product=None,
                 default_array_length=None, data_processing_reference=None, id=None, params=None,
                 context=NullMap):
        if params is None:
            params = []
        self.index = index
        self.default_array_length = default_array_length
        self.binary_data_list = binary_data_list
        self.precursor = precursor
        self.product = product
        self.data_processing_reference = data_processing_reference
        self._data_processing_reference = context["DataProcessing"][data_processing_reference]
        self.element = _element(
            "chromatogram", id=id, index=index,
            defaultArrayLength=self.default_array_length,
            dataProcessingRef=self._data_processing_reference)
        self.context = context
        self.context["Chromatogram"][id] = self.element.id
        self.params = params

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            self.write_params(xml_file)
            if self.precursor is not None:
                self.precursor.write(xml_file)
            if self.product is not None:
                self.product.write(xml_file)
            self.binary_data_list.write(xml_file)


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
        with element(xml_file, 'cvList', count=len(self.cv_list)):
            for member in self.cv_list:
                tag = _element(
                    "cv", id=member.id, fullName=member.full_name,
                    URI=member.uri)
                if member.version is not None:
                    tag.attrs['version'] = member.version
                if member.options:
                    tag.attrs.update(member.options)
                xml_file.write(tag.element(with_id=True))

    def __iter__(self):
        return iter(self.cv_list)


class Contact(ParameterContainer):
    def __init__(self, params, context=NullMap, **kwargs):
        super(Contact, self).__init__('contact', params, context=context, **kwargs)


class Person(ComponentBase):
    def __init__(self, first_name='first_name', last_name='last_name', id=DEFAULT_CONTACT_ID,
                 affiliation=DEFAULT_ORGANIZATION_ID, context=NullMap):
        self.first_name = first_name
        self.last_name = last_name
        self.id = id
        self.affiliation = affiliation
        self.element = _element("Person", firstName=first_name, last_name=last_name, id=id)
        context["Person"][id] = self.element.id
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            element(xml_file, 'Affiliation', organization_ref=self.affiliation)


class Organization(ComponentBase):
    def __init__(self, name="name", id=DEFAULT_ORGANIZATION_ID, context=NullMap):
        self.name = name
        self.id = id
        self.element = _element("Organization", name=name, id=id)
        context["Organization"][id] = self.id
        self.context = context

    def write(self, xml_file):
        xml_file.write(self.element.element())


DEFAULT_PERSON = Person()
DEFAULT_ORGANIZATION = Organization()
