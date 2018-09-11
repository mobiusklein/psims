import re
from six import text_type

xsd_pattern = re.compile(r"(?:value-type:)?xsd\\?:([^\"]+)")


def non_negative_integer(value):
    x = int(value)
    if x < 0:
        raise TypeError("non_negative_integer cannot be negative. (%r)" % value)
    return x


def positive_integer(value):
    x = int(value)
    if x < 0:
        raise TypeError("positive_integer cannot be less than 1. (%r)" % value)
    return x


value_type_resolvers = {
    'int': int,
    'double': float,
    'float': float,
    'string': text_type,
    "anyURI": text_type,
    'nonNegativeInteger': non_negative_integer,
    'boolean': bool,
    'positiveInteger': positive_integer,
}


def parse_xsdtype(text):
    match = xsd_pattern.search(text)
    if match:
        dtype_name = match.group(1).strip()
        return value_type_resolvers[dtype_name]
