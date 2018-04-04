from lxml import etree
from six import add_metaclass, string_types as basestring
from gzip import GzipFile

try:
    from collections import Iterable, Mapping
except ImportError:
    from collections.abc import Iterable, Mapping


def ensure_iterable(obj):
    if obj is None:
        return tuple()
    if not isinstance(obj, Iterable) or isinstance(obj, basestring) or isinstance(obj, Mapping):
        return [obj]
    return obj


compressed_stream_openers = {
    None: open,
    "gzip": GzipFile
}


compressed_file_extensions = {
    'gz': 'gzip'
}


def pretty_xml(path, outpath=None, encoding=b'utf-8', compression=None):
    tree = etree.parse(path)
    if outpath is None:
        outpath = path
    if hasattr(outpath, 'write'):
        outstream = outpath
    else:
        try:
            outstream = compressed_stream_openers[compression](outpath, 'wb')
        except KeyError:
            outstream = open(outpath, 'wb')
    with outstream:
        outstream.write(b'<?xml version="1.0" encoding="' + encoding + b'"?>\n')
        outstream.write(
            etree.tostring(tree, pretty_print=True))
