import pkg_resources

from lxml import etree


def get_xsd(name):
    return pkg_resources.resource_stream(__name__, "xsd/%s" % name)


schemas = {
    'mzML': ('mzML1.1.0.xsd'),
    'indexedmzML': ('mzML1.1.2_idx.xsd'),
    'MzIdentML': ('mzIdentML1.2.0.xsd'),
}


def get_schema(name):
    schema_name = schemas[name]
    tree = etree.parse(get_xsd(schema_name))
    return etree.XMLSchema(tree)


def validate(path):
    tree = etree.parse(path)
    root = tree.getroot()
    parts = root.tag.split("}", 1)
    if len(parts) == 1:
        name = parts[0]
    else:
        name = parts[1]
    try:
        schema = get_schema(name)
    except KeyError:
        raise KeyError("Could not locate a schema for %r" % (name,))
    result = schema.validate(tree)
    return result, schema
