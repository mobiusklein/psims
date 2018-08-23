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


def synonym_parser(text):
    original = text
    if text.endswith("]"):
        text = text.rsplit("[", 1)[0].rstrip()
    synonym, scope = text.rsplit(" ", 1)
    if scope not in synonym_scopes:
        warnings.warn("Non-standardized Synonym Scope %s for %s" % (scope, original))
    return synonym.strip()[1:-1]


class OBOParser(object):
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
                entity[rel.predicate] = rel
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
