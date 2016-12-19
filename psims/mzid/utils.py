from collections import Iterable, Mapping

try:
    basestring = basestring
except:
    basestring = (str, bytes)


def ensure_iterable(obj):
    if obj is None:
        return tuple()
    if not isinstance(obj, Iterable) or isinstance(obj, basestring) or isinstance(obj, Mapping):
        return [obj]
    return obj
