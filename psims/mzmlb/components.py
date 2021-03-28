from ..mzml.components import BinaryDataArray, Binary, NullMap
from ..xml import _element


# EXTERNAL_DATASET_PARAM = "external reference dataset"
EXTERNAL_DATASET_PARAM = "external dataset"


class ExternalBinaryDataArray(BinaryDataArray):
    def __init__(self, external_dataset_name, data_processing_reference=None,
                 offset=None, array_length=None, params=None, context=NullMap, **kwargs):
        if (params is None):
            params = []
        self.external_dataset_name = external_dataset_name
        self.array_length = array_length
        self.offset = offset
        self.data_processing_reference = data_processing_reference
        if data_processing_reference:
            self._data_processing_reference = context[
                'DataProcessing'][data_processing_reference]
        else:
            self._data_processing_reference = None
        self.params = self.prepare_params(params, **kwargs)
        self.element = _element(
            'binaryDataArray',
            encodedLength=0,
            dataProcessingRef=self._data_processing_reference)
        self.context = context
        self._array_type = None
        self._prepare_external_refs()
        self.binary = Binary(b"", context=self.context)

    def _prepare_external_refs(self):
        self.add_param({
            "name": EXTERNAL_DATASET_PARAM,
            "value": self.external_dataset_name
        }).add_param({
            "name": "external array length",
            "value": self.array_length,
        }).add_param({
            "name": "external offset",
            "value": self.offset
        })
        return self

