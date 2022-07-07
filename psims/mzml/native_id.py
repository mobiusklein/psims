import re

from typing import OrderedDict, Mapping



type_pat = re.compile("([A-Za-z]+)=xsd:(%s+)" % '|'.join(
    {'IDREF', "long", 'nonNegativeInteger', 'positiveInteger', 'string'}))

xsd_to_regex = {
    "IDREF": r"(\S+)",
    "long": r"(-?\d+)",
    "nonNegativeInteger": r"(\d+)",
    "positiveInteger": r"(\d+)",
    "string": r"(\S+)",
}

xsd_to_type = {
    "IDREF": str,
    "long": int,
    "nonNegativeInteger": int,
    "positiveInteger": int,
    "string": str,
}

type_to_default = {
    "long": 0,
    "nonNegativeInteger": 0,
    "positiveInteger": 1,
}


class IDParserBase(object):
    """A base class for ID parsing and formatting.
    """

    def __call__(self, text):
        """Parse a string looking for fields defined by this ID format.

        Parameters
        ----------
        text : str
            The string to parse

        Returns
        -------
        dict:
            The parsed fields of the ID string.

        See Also
        --------
        :meth:`parse`
        """
        return self.parse(text)


class NativeIDParser(IDParserBase):
    """A parser for a single nativeID format.

    These may be automatically derived from the CV-param defining them by parsing the
    XSD string included, but no guarantee is available.
    """

    def __init__(self, parser, tokens, name):
        self.parser = parser
        self.tokens = OrderedDict(tokens)
        self.name = name

    @classmethod
    def from_term(cls, term):
        """Construct a :class:`NativeIDParser` from :class:`IDFormat` term.

        Parameters
        ----------
        term : IDFormat
            The nativeID format specification to build a parser for

        Returns
        -------
        :class:`NativeIDParser`:
            The constructed parser, or :const:`None` if no regular expression could be
            constructed.
        """
        if "Native format defined by" in term.definition:
            tokens = []
            desc = term.definition.split(
                "Native format defined by", 1)[1].rstrip()
            for mat in type_pat.finditer(desc):
                tokens.append(mat.groups())
            parser = re.compile(
                ''.join([r"(%s)=%s\s?" % (k, xsd_to_regex[v]) for k, v in tokens]))
            return cls(parser, tokens, term.name)
        return None

    def parse(self, string):
        """Parse a string according to this parser's pattern,
        returning the type-cast fields as a :class:`dict`.

        Parameters
        ----------
        string : str
            The string to parse

        Returns
        -------
        dict
            The fields of the scan ID

        Raises
        ------
        ValueError:
            If the string does not conform to the expected pattern
        """
        match = self.parser.match(string)
        if match is None:
            return OrderedDict()
        groups = match.groups()
        n = len(groups)
        i = 0
        fields = OrderedDict()
        while i < n:
            k = groups[i]
            v = groups[i + 1]
            i += 2
            try:
                v = int(v)
            except ValueError:
                pass
            fields[k] = v
        return fields

    def format(self, fields):
        """Format a set of fields as a nativeID string.

        Parameters
        ----------
        fields : dict
            The fields to populate the nativeID from.

        Returns
        -------
        str
        """
        parts = []
        for key in self.tokens:
            parts.append("%s=%s" % (key, fields[key]))
        return ' '.join(parts)

    def format_integer(self, value):
        tokens = list(self.tokens.items())
        fields = {}
        n = len(tokens) - 1
        for i, (name, tp) in enumerate(tokens):
            if i == n:
                fields[name] = value
            else:
                if tp in type_to_default:
                    fields[name] = type_to_default[tp]
                else:
                    raise ValueError(f"Cannot infer nativeID format default for {name} of type {tp}")
        return self.format(fields)



class MultipleIDFormats(Mapping, IDParserBase):
    '''Represent an ambiguous group of multiple nativeID formats.

    Implements the :class:`~collections.abc.Mapping` interface.

    Attributes
    ----------
    id_formats : OrderedDict
        A mapping of format name to :class:`IDFormat` instances
    '''

    def __init__(self, id_formats):
        self.id_formats = id_formats

    def parse(self, text):
        fields = OrderedDict()
        for name, parser in self.id_formats.items():
            fields = parser.parse(text)
            if not fields:
                continue
            else:
                fields['id_format'] = name
                break
        return fields

    def format(self, fields):
        format_name = fields.get('id_format')
        id_format = self.id_formats[format_name]
        return id_format.format(fields)

    def __iter__(self):
        return iter(self.id_formats)

    def __getitem__(self, key):
        return self.id_formats[key]

    def __len__(self):
        return len(self.id_formats)

    def __repr__(self):
        template = "{self.__class__.__name__}({self.id_formats})"
        return template.format(self=self)
