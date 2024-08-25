'''Machinery for interpreting XSD data type declarations in controlled vocabulary
file formats and mapping them to and from Python types.
'''
import re
import datetime
import warnings

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


def resolve_datetime(value):
    if isinstance(value, datetime.datetime):
        return value
    else:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def resolve_date(value):
    if isinstance(value, datetime.date):
        return value
    else:
        return datetime.date.strptime(value, "%Y-%m-%d")


def str_or_f(f):
    def g(x):
        if isinstance(x, str):
            return x
        else:
            return f(x)
    return g


def resolve_boolean(x):
    if isinstance(x, str):
        if x.lower().strip() == "true":
            return True
        else:
            return False
    else:
        return bool(x)


value_type_resolvers = {
    "int": int,
    "integer": int,
    "double": float,
    "float": float,
    "decimal": float,
    "string": text_type,
    "anyURI": text_type,
    "nonNegativeInteger": non_negative_integer,
    "boolean": resolve_boolean,
    "positiveInteger": positive_integer,
    "dateTime": resolve_datetime,
    # TODO
    "date": resolve_date,
}


value_type_formatters = {
    "int": str,
    "integer": str,
    "double": str,
    "float": str,
    "decimal": str,
    "string": str,
    "anyURI": str,
    "nonNegativeInteger": str,
    "positiveInteger": str,
    "boolean": lambda x: str(x).lower(),
    "dateTime": str_or_f(datetime.datetime.isoformat),
    "date": str_or_f(datetime.date.isoformat),
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
    converter : :class:`~.Callable`
    formatter: :class:`~.Callable`
    """
    match = xsd_pattern.search(text)
    if match:
        dtype_name = match.group(1).strip()
        try:
            dtype = value_type_resolvers[dtype_name]
        except KeyError:
            warnings.warn("Could not find a converter for XSD type %r" % (text,))
            dtype = str
        try:
            formatter = value_type_formatters[dtype_name]
        except KeyError:
            warnings.warn("Could not find a formatter for XSD type %r" % (text,))
            formatter = str
        return dtype, formatter
    else:
        return str, str


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


def type_inference_guess(string):
    if string.startswith("\""):
        string = string[1:-1]
    lower_string = string.lower()
    if lower_string == 'none' or not lower_string:
        return None
    if lower_string[0].isnumeric() or lower_string == '-' and lower_string[1].isnumeric():
        try:
            value = int(string)
        except ValueError:
            try:
                value = float(string)
            except ValueError:
                value = string
        return value
    if lower_string in ('true', 'yes'):
        return True
    elif lower_string in ('false', 'no'):
        return False
    return string


class TypeDefinition(object):
    def __init__(self, id, name, type_definition, formatter=str):
        self.id = id
        self.name = name
        self.type_definition = type_definition
        self.formatter = formatter

    def __repr__(self):
        template = "{self.__class__.__name__}({self.id!r}, {self.name!r}, {self.type_definition!r})"
        return template.format(self=self)

    def parse(self, value):
        return self.type_definition(value)

    def __call__(self, value):
        return self.parse(value)

    def format(self, value):
        return self.formatter(value)


class ListOfType(TypeDefinition):
    def __init__(self, id, name, type_definition):
        super(ListOfType, self).__init__(id, name, type_definition)

    def tokenize(self, text, sep=','):
        return filter(bool, map(lambda x: x.strip(), text.split(sep)))

    def parse(self, value, sep=','):
        return [self.type_definition(v) for v in self.tokenize(value, sep=sep)]

    def format(self, value, sep=','):
        return sep.join([self.type_definition.format(v) for v in value])