import pkg_resources

from lxml import etree

from six import raise_from


def get_xsd(name):
    return pkg_resources.resource_stream(__name__, "xsd/%s" % name)


schemas = {
    'mzML': ('mzML1.1.0.xsd'),
    'indexedmzML': ('mzML1.1.2_idx.xsd'),
    # 'MzIdentML': ('mzIdentML1.2.0.xsd'),
    "http://psidev.info/psi/pi/mzIdentML/1.1 ../schema/mzIdentML1.1.0.xsd": ("mzIdentML1.1.0.xsd"),
    "http://psidev.info/psi/pi/mzIdentML/1.1.1 ../schema/mzIdentML1.1.1.xsd": ("mzIdentML1.1.1.xsd"),
    "http://psidev.info/psi/pi/mzIdentML/1.2 ../schema/mzIdentML1.2.0.xsd": ("mzIdentML1.2.0.xsd"),
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
        try:
            location = root.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
            schema = get_schema(location)
        except KeyError:
            raise_from(KeyError("Could not locate a schema for %r or %r" % (name, location)), None)
    result = schema.validate(tree)
    return result, schema
