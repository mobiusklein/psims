import warnings
from datetime import datetime
from collections import Mapping, Iterable
from numbers import Number

from ..xml import _element, element, TagBase
from ..document import (
    ComponentBase as _ComponentBase, NullMap, ComponentDispatcherBase,
    ParameterContainer, IDParameterContainer)


class MzML(TagBase):
    type_attrs = {
        "xmlns": "http://psi.hupo.org/ms/mzml",
        "version": "1.1.0",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://psi.hupo.org/ms/mzml http://psidev.info/files/ms/mzML/xsd/mzML1.1.0.xsd"
    }

    def __init__(self, **attrs):
        attrs.setdefault('creationDate', datetime.utcnow())
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
    _element(
        "cv", id="PSI-MS",
        uri=("http://psidev.cvs.sourceforge.net/*checkout*/"
             "psidev/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"),
        fullName="PSI-MS"),
    _element(
        "cv", id="UO",
        uri="http://obo.cvs.sourceforge.net/*checkout*/obo/obo/ontology/phenotype/unit.obo",
        fullName="UNIT-ONTOLOGY"),
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


class IDMemberGenericCollection(GenericCollection):
    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            for member in self.members:
                member.write(xml_file, with_id=True)


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
    def __init__(self, spectrum_types, context=NullMap):
        self.spectrum_types = spectrum_types
        self.element = _element("fileContent")
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file):
            for spectrum_type in self.spectrum_types:
                self.context.param(spectrum_type)(xml_file)


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
            for param in self.params:
                self.context.param(param)(xml_file)


class FileDescription(ComponentBase):
    def __init__(self, content, source_files, contacts=None, context=NullMap):
        if not isinstance(content, FileContent):
            content = FileContent(content, context=context)
        if not isinstance(source_files, SourceFileList):
            if len(source_files) > 0 and not isinstance(source_files[0], SourceFile):
                source_files = [SourceFile(context=context, **f) for f in source_files]
            source_files = SourceFileList(source_files, context=context)
        self.content = content
        self.source_files = source_files
        self.contacts = contacts
        self.context = context
        self.element = _element("fileDescription")

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=False):
            self.content.write(xml_file)
            self.source_files.write(xml_file)
            # TODO: handle contact


# --------------------------------------------------
# ParamGroups

class ReferenceableParamGroupList(IDGenericCollection):
    def __init__(self, members, context):
        super(ReferenceableParamGroupList, self).__init__(
            "referenceableParamGroupList", members, context)


class ReferenceableParamGroup(IDParameterContainer):
    def __init__(self, params=None, id=None, context=NullMap):
        if params is None:
            params = []
        super(ReferenceableParamGroup, self).__init__(
            "referenceableParamGroup", params, dict(id=id), context=context)
        self.id = self.element.id
        context["ReferenceableParamGroup"][id] = self.element.id


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
            for param in self.params:
                self.context.param(param)(xml_file)


# --------------------------------------------------
# Instrument Configuration Metadata

class InstrumentConfigurationList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(InstrumentConfigurationList, self).__init__("instrumentConfigurationList", members, context)


class InstrumentConfiguration(ComponentBase):
    def __init__(self, scan_settings_reference, id, component_list=None, params=None,
                 software_reference=None, context=NullMap):
        self.scan_settings_reference = scan_settings_reference
        self.params = params
        self.software_reference = software_reference
        self._software_reference = context['Software'][software_reference]
        self.component_list = component_list
        self.element = _element(
            "instrumentConfiguration", id=id,
            scanSettingsRef=context['ScanSettings'][scan_settings_reference])
        self.context = context

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for param in self.params:
                self.context.param(param)(xml_file)
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
        for component in members:
            if component[type_key] == 'source':
                components.append(
                    Source(component['order'], component['params'], context))
            elif component[type_key] == 'analyzer':
                components.append(
                    Analyzer(component['order'], component['params'], context))
            elif component[type_key] == 'detector':
                components.append(
                    Detector(component['order'], component['params'], context))
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


class Detector(ComponentBase):
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
        with self.element.element(xml_file, with_id=True):
            for param in self.params:
                self.context.param(param)(xml_file)

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
                 id=None,
                 params=None, context=NullMap):
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
        self.params = params

    def write(self, xml_file):
        with self.element.element(xml_file, with_id=True):
            for param in self.params:
                self.context.param(param)(xml_file)
            if self.scan_list is not None:
                self.scan_list.write(xml_file)
            if self.precursor_list is not None:
                self.precursor_list.write(xml_file)

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
            for param in self.params:
                self.context.param(param)(xml_file)
            self.binary.write(xml_file)


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
            for param in self.params:
                self.context.param(param)(xml_file)
            for member in self.members:
                member.write(xml_file)


class Scan(ComponentBase):
    def __init__(self, scan_window_list=None, params=None, context=NullMap):
        if scan_window_list is None:
            scan_window_list = ScanWindowList([], context)
        elif not isinstance(scan_window_list, ScanWindowList):
            scan_window_list = ScanWindowList(scan_window_list, context)
        if params is None:
            params = []
        self.params = params
        self.scan_window_list = scan_window_list
        self.element = _element("scan")
        self.context = context

    def write(self, xml_file):
        with self.element(xml_file, with_id=False):
            for param in self.params:
                self.context.param(param)(xml_file)
            self.scan_window_list.write(xml_file)


class ScanWindowList(GenericCollection):
    def __init__(self, members, context=NullMap):
        super(ScanWindowList, self).__init__('scanWindowList', members, context=context)


class ScanWindow(ParameterContainer):
    def __init__(self, *args, **kwargs):
        super(ScanWindow, self).__init__("scanWindow", *args, **kwargs)


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
            for param in self.params:
                self.context.param(param)(xml_file)


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
            if self.activation is not None:
                self.activation.write(xml_file)
            if self.isolation_window is not None:
                self.isolation_window.write(xml_file)
            self.selected_ion_list.write(xml_file)


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
            for param in self.params:
                self.context.param(param)(xml_file)


class Chromatogram(ComponentBase):
    def __init__(self, index, binary_data_list=None, default_array_length=None,
                 data_processing_reference=None, id=None, params=None,
                 context=NullMap):
        if params is None:
            params = []
        self.index = index
        self.default_array_length = default_array_length
        self.binary_data_list = binary_data_list
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
            for param in self.params:
                self.context.param(param)(xml_file)

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
        with element(xml_file, 'cvList'):
            for member in self.cv_list:
                xml_file.write(member.element(with_id=True))


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
