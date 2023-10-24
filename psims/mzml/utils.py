from collections import defaultdict

from typing import Union, Optional, Mapping

from psims.utils import ensure_iterable, basestring


def _map_compressor(compressor: Union[Optional[str], Mapping[str, Optional[str]]], default=None) -> Optional[Mapping[str, Optional[str]]]:
    if compressor is None:
        return None
    if isinstance(compressor, str):
        return defaultdict(lambda: compressor)
    elif isinstance(compressor, Mapping):
        if isinstance(compressor, defaultdict):
            return compressor
        return defaultdict(lambda: default, compressor)
    else:
        raise TypeError(f"Cannot coerce compressor {compressor!r}")