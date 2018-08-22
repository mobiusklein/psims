from lxml import etree
from six import add_metaclass, string_types as basestring

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
        opener = compression.get(path)
        outstream = opener(outpath, 'wb')
    with outstream:
        outstream.write(
            etree.tostring(tree, pretty_print=True, encoding=encoding, xml_declaration=True))


def simple_repr(self):  # pragma: no cover
    template = "{self.__class__.__name__}({d})"

    def formatvalue(v):
        if isinstance(v, float):
            return "%0.4f" % v
        else:
            return str(v)

    if not hasattr(self, "__slots__"):
        d = [
            "%s=%s" % (k, formatvalue(v)) if v is not self else "(...)" for k, v in sorted(
                self.__dict__.items(), key=lambda x: x[0])
            if (not k.startswith("_") and not callable(v)) and not (v is None)]
    else:
        d = [
            "%s=%s" % (k, formatvalue(v)) if v is not self else "(...)" for k, v in sorted(
                [(name, getattr(self, name)) for name in self.__slots__], key=lambda x: x[0])
            if (not k.startswith("_") and not callable(v)) and not (v is None)]

    return template.format(self=self, d=', '.join(d))
