from lxml import etree


def pretty_xml(path, outpath=None):
    tree = etree.parse(path)
    if outpath is None:
        outpath = path
    with open(outpath, 'wb') as outstream:
        outstream.write('<?xml version="1.0" encoding="utf-8"?>\n')
        outstream.write(
            etree.tostring(tree, pretty_print=True))
