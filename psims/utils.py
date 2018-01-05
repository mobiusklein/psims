from lxml import etree
from six import add_metaclass
from gzip import GzipFile


compressed_stream_openers = {
    None: open,
    "gzip": GzipFile
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
