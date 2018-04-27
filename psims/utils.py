from lxml import etree
from six import add_metaclass, string_types as basestring
from gzip import GzipFile

try:
    from collections import Iterable, Mapping
except ImportError:
    from collections.abc import Iterable, Mapping

from psims import compression


def ensure_iterable(obj):
    if obj is None:
        return tuple()
    if not isinstance(obj, Iterable) or isinstance(obj, basestring) or isinstance(obj, Mapping):
        return [obj]
    return obj


def pretty_xml(path, outpath=None, encoding=b'utf-8'):
    tree = etree.parse(path)
    if outpath is None:
        opener = compression.get(path)
        outpath = opener(path, 'wb')
    if hasattr(outpath, 'write'):
        outstream = outpath
    else:
        opener = compression.get(outpath)
        outstream = opener(outpath, 'wb')
    with outstream:
        outstream.write(b'<?xml version="1.0" encoding="' + encoding + b'"?>\n')
        outstream.write(
            etree.tostring(tree, pretty_print=True))
