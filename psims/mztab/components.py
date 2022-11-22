
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Iterable, List, Dict, Set, Tuple, Optional, Union

from psims.xml import CVParam, UserParam

ParamType = Union[str, Dict[str, Any], CVParam, UserParam]

@dataclass
class ValueType:
    value: ParamType


@dataclass
class ListValueType:
    value: List[ParamType] = field(default_factory=list)

    def append(self, value: ParamType):
        self.value.append(value)
        return self

    def extend(self, values: Iterable[ParamType]):
        self.value.extend(values)


@dataclass
class SampleProcessing(ValueType):
    pass


@dataclass
class Instrument:
    name: Optional[ParamType]
    source: Optional[ParamType]
    analyzer: Optional[ParamType]
    detector: Optional[ParamType]


@dataclass
class Software:
    value: ParamType
    setting: List[str]



class ProteinSearchEngineScore(ValueType):
    pass



class PeptideSearchEngineScore(ValueType):
    pass



class PSMSearchEngineScore(ValueType):
    pass



class SmallMoleculeSearchEngineScore(ValueType):
    pass


class FalseDiscoveryRate(ListValueType):
    pass



class Publication(ValueType):
    pass


@dataclass
class Contact:
    name: str
    affiliation: str
    email: str


class URI(ValueType):
    pass


@dataclass
class MetadataModificationBase:
    modification: ParamType
    site: str = field(default=None)
    position: Union[str, int] = field(default=None)

    def __post_init__(self):
        self.resolve_modification()

    def resolve_modification(self):
        raise NotImplementedError()


class FixedModification(MetadataModificationBase):
    pass


class VariableModification(MetadataModificationBase):
    pass


class QuantificationMethod(ValueType):
    pass


class ProteinQuantificationUnit(ValueType):
    pass


class SmallMoleculeQuantificationUnit(ValueType):
    pass


@dataclass
class MSRun:
    format: ParamType
    id_format: ParamType
    location: str
    fragmentation_method: List[ParamType]
    hash_method: ParamType
    hash: str


class Custom(ValueType):
    pass


