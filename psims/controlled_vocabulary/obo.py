import re
from collections import defaultdict
from .reference import Reference
from .entity import Entity
from .relationship import Relationship

from six import string_types as basestring


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
    'string': str,
    "anyURI": str,
    'nonNegativeInteger': non_negative_integer,
    'boolean': bool,
    'positiveInteger': positive_integer,
}


class OBOParser(object):
    def __init__(self, handle):
        self.handle = handle
        self.terms = {}
        self.current_term = None
        self.header = defaultdict(list)
        self.parse()

    def _get_value_type(self, xref_string):
        match = xsd_pattern.search(xref_string)
        if match:
            dtype_name = match.group(1).strip()
            return value_type_resolvers[dtype_name]

    def pack(self):
        if self.current_term is None:
            return
        entity = Entity(self, **{k: v[0] if len(v) == 1 else v for k, v in self.current_term.items()})
        try:
            is_as = entity['is_a']
            if isinstance(is_as, basestring):
                is_as = Reference.fromstring(is_as)
                # self[is_as].children.append(entity)
            else:
                is_as = map(Reference.fromstring, is_as)
                # for term in is_as:
                #     self[term].children.append(entity)
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
                self.header[key].append(val)
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
