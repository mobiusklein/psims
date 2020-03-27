import re
import datetime
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
    'integer': int,
    'double': float,
    'float': float,
    'decimal': float,
    'string': text_type,
    "anyURI": text_type,
    'nonNegativeInteger': non_negative_integer,
    'boolean': bool,
    'positiveInteger': positive_integer,
    'dateTime': lambda x: datetime.datetime.strptime(x, '%Y-%m-%dT%H:%M:%S')
}


def parse_xsdtype(text):
    """Parse an XSD type definition to determine the appropriate Python type
    coercion function.

    Parameters
    ----------
    text : str
        The XSD type name

    Returns
    -------
    :class:`~.Callable`
    """
    match = xsd_pattern.search(text)
    if match:
        dtype_name = match.group(1).strip()
        return value_type_resolvers[dtype_name]


def obj_to_xsdtype(value):
    """Determine the appropriate XSD type from a Python object's
    type.

    Parameters
    ----------
    value : object
        The object whose appropriate XSD type to determine

    Returns
    -------
    :class:`str`:
        The XSD name for the type appropriate for `value`
    """
    if isinstance(value, bool):
        return "xsd:boolean"
    elif isinstance(value, int):
        return "xsd:int"
    elif isinstance(value, float):
        return "xsd:float"
    elif isinstance(value, text_type):
        return "xsd:string"
    else:
        return None
