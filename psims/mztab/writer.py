import io
import csv

from typing import Any, DefaultDict, List, Dict, Set, Tuple, Optional, Union

from psims.document import DocumentContext
from psims.xml import CVParam, UserParam


ParamType = Union[str, Dict[str, Any]]
_MetadataStore = DefaultDict[str, List[ParamType]]

SEP = '\t'


class DocumentSection(DocumentContext):
    stream: io.TextIOBase

    def __init__(self, stream: io.TextIOBase, vocabularies=None, vocabulary_resolver=None, missing_reference_is_error=False):
        super().__init__(vocabularies, vocabulary_resolver, missing_reference_is_error)
        self.stream = stream

    def format_param(self, param: ParamType):
        param = self.param(param)
        if isinstance(param, CVParam):
            accession = param.accession
            cv_ref = param.cv_ref
            name = param.name
            value = param.value
            return f'[{cv_ref}, {accession}, {name}, {value}]'
        elif isinstance(param, UserParam):
            name = param.name
            value = param.value
            if not value:
                return name
            else:
                return f"{name}={value}"
        else:
            raise TypeError(param)



class MetadataSection(DocumentSection):
    metadata: _MetadataStore
    version: Optional[str]
    mode: Optional[str]
    type: Optional[str]
    description: str

    def __init__(self, stream: io.TextIOBase, metadata: Optional[_MetadataStore]=None, vocabularies=None, vocabulary_resolver=None, missing_reference_is_error=False):
        super().__init__(stream, vocabularies, vocabulary_resolver, missing_reference_is_error)
        if metadata is None:
            metadata = DefaultDict(list)
        self.metadata = metadata

    def add(self, key: str, param: ParamType) -> 'MetadataSection':
        self.metadata[key].append(param)
        return self

    def write(self):
        for key, params in self.metadata.items():
            for param in params:
                self.stream.write(f"MTD\t{key}\t{self.format_param(param)}\n")



