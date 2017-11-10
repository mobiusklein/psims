from collections import defaultdict
from .reference import Reference
from .entity import Entity
from .relationship import Relationship

from six import string_types as basestring


class OBOParser(object):
    def __init__(self, handle):
        self.handle = handle
        self.terms = {}
        self.current_term = None
        self.parse()

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

    def parse(self):
        for line in self.handle.readlines():
            line = line.decode('utf-8')
            line = line.strip()
            if not line:
                continue
            elif line == "[Typedef]":
                if self.current_term is not None:
                    self.pack()
                self.current_term = None
            elif line == "[Term]":
                if self.current_term is not None:
                    self.pack()
                self.current_term = defaultdict(list)
            else:
                if self.current_term is None:
                    continue
                key, sep, val = line.partition(":")
                self.current_term[key].append(val.strip())
        self.pack()
        self._connect_parents()

    def __getitem__(self, key):
        return self.terms[key]

    def __iter__(self):
        return iter(self.terms.items())
