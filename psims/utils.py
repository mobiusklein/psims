from lxml import etree
from six import add_metaclass


def pretty_xml(path, outpath=None, encoding=b'utf-8'):
    tree = etree.parse(path)
    if outpath is None:
        outpath = path
    with open(outpath, 'wb') as outstream:
        outstream.write(b'<?xml version="1.0" encoding="' + encoding + b'"?>\n')
        outstream.write(
            etree.tostring(tree, pretty_print=True))
