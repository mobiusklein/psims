import warnings

from collections import defaultdict

from six import string_types as basestring

from .entity import Entity
from .relationship import Relationship, Reference
from .type_definition import parse_xsdtype


synonym_scopes = {
    "EXACT",
    "BROAD",
    "NARROW",
    "RELATED"
}


def _synonym_parser(text):
    state = None
    quoted_chars = []
    scopes = []
    scope_chars = []
    references = []
    for c in text:
        if c == "\"":
            if state is None:
                state = "quote_open"
            elif state == 'quote_open':
                state = "quote_close"
            elif state == 'trailing':
                pass
            else:
                raise ValueError("Quote after quoted text!")
        else:
            if state == "quote_open":
                quoted_chars.append(c)
            elif state == "quote_close":
                if c == " ":
                    state = 'scope'
                else:
                    raise ValueError("Expected space before scope")
            elif state == 'scope':
                if c == ' ':
                    scopes.append(''.join(scope_chars))
                    scope_chars = []
                elif c == '[':
                    state = 'references'
                else:
                    scope_chars.append(c)
            elif state == 'references':
                if c != ']':
                    references.append(c)
                else:
                    state = 'trailing'
            elif state == 'trailing':
                pass
    return ''.join(quoted_chars), scopes, ''.join(references)


def synonym_parser(text):
    synonym, scopes, references = _synonym_parser(text)
    return synonym


class OBOParser(object):
    """Parser for an :title-reference:`OBO` [OBO]_ file that constructs a semantic graph.

    Attributes
    ----------
    current_term : dict
        The current term being parsed
    handle : file
        The file stream to read from
    header : defaultdict(list)
        Store the header information from the OBO file
    terms : dict
        Maps term id to :class:`~.Entity` objects

    References
    ----------
    OBO
        http://owlcollab.github.io/oboformat/doc/GO.format.obo-1_2.html
    """

    def __init__(self, handle):
        self.handle = handle
        self.terms = {}
        self.current_term = None
        self.header = defaultdict(list)
        self.parse()

    @property
    def version(self):
        try:
            return self.header['data-version']
        except KeyError:
            return None

    @property
    def name(self):
        try:
            return self.header['ontology'].upper()
        except KeyError:
            return None

    def _get_value_type(self, xref_string):
        return parse_xsdtype(xref_string)

    def pack(self):
        """Pack the currently collected OBO entry into an :class:`~.Entity`.

        Returns
        -------
        :class:`~.Entity`
        """
        if self.current_term is None:
            return
        entity = Entity(self, **{k: v[0] if len(v) == 1 else v for k, v in self.current_term.items()})
        try:
            is_as = entity['is_a']
            if isinstance(is_as, basestring):
                is_as = Reference.fromstring(is_as)
            else:
                is_as = list(map(Reference.fromstring, is_as))
            entity['is_a'] = is_as
        except KeyError:
            pass
        try:
            relationships = entity['relationship']
            if not isinstance(relationships, list):
                relationships = [relationships]
            relationships = [Relationship.fromstring(r) for r in relationships]
            for rel in relationships:
                entity.setdefault(rel.predicate, [])
                entity[rel.predicate].append(rel)
        except KeyError:
            pass
        try:
            synonyms = entity['synonym']
            if not isinstance(synonyms, list):
                synonyms = [synonyms]
            synonyms = list(map(synonym_parser, synonyms))
            entity['synonym'] = synonyms
        except KeyError:
            pass
        try:
            xref = entity['xref']
            if isinstance(xref, basestring):
                entity.value_type = self._get_value_type(xref)
            else:
                for x in xref:
                    value_type = self._get_value_type(x)
                    if x is not None:
                        entity.value_type = value_type
        except KeyError:
            pass
        self.terms[entity['id']] = entity
        self.current_term = None

    def _connect_parents(self):
        """Walk the semantic graph up the parent hierarchy, binding child
        to parent through ``is_a`` :class:`~.Reference` connections.
        """
        for term in self.terms.values():
            try:
                if isinstance(term.is_a, Reference):
                    self.terms[term.is_a].children.append(term)
                else:
                    for is_a in term.is_a:
                        self.terms[is_a].children.append(term)
            except KeyError:
                continue

    def _pack_if_occupied(self):
        if self.current_term is not None:
            self.pack()

    def _simplify_header_information(self):
        self.header = {
            k: v if len(v) > 1 else v[0] for k, v in self.header.items()
        }

    def parse(self):
        """Iteratively parse a binary file stream for an OBO file into a
        semantic graph.
        """
        in_header = True
        for line in self.handle.readlines():
            line = line.decode('utf-8')
            line = line.strip()
            if not line:
                in_header = False
                continue
            elif in_header:
                key, val = line.split(":", 1)
                self.header[key].append(val.strip())
            elif line == "[Typedef]":
                self._pack_if_occupied()
                self.current_term = None
            elif line == "[Term]":
                self._pack_if_occupied()
                self.current_term = defaultdict(list)
            else:
                if self.current_term is None:
                    continue
                key, sep, val = line.partition(":")
                self.current_term[key].append(val.strip())
        self.pack()
        self._connect_parents()
        self._simplify_header_information()

    def __getitem__(self, key):
        return self.terms[key]

    def __iter__(self):
        return iter(self.terms.items())
