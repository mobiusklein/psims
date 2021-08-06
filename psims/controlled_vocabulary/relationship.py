import re

from .type_definition import TypeDefinition, ListOfType, parse_xsdtype

class SemanticEdge(object):
    def __init__(self, accession, comment=None):
        self.accession = accession
        self.comment = comment

    def __eq__(self, other):
        try:
            return self.accession == other.accession
        except AttributeError:
            return self.accession == other

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        if self.comment:
            return "{self.accession} ! {self.comment}".format(self=self)
        else:
            return self.accession

    def __repr__(self):
        return "Reference(%r, %r)" % (self.accession, self.comment)

    def __hash__(self):
        return hash(self.accession)


class Reference(SemanticEdge):
    @classmethod
    def fromstring(cls, string):
        try:
            accession, comment = map(lambda s: s.strip(), string.split("!"))
            return cls(accession, comment)
        except Exception:
            return cls(string)


class Relationship(SemanticEdge):
    dispatch = {}

    def __init__(self, predicate, accession, comment=None):
        self.predicate = predicate.strip(":")
        self.accession = accession
        self.comment = comment

    def __str__(self):
        return "%s %s ! %s" % (self.predicate, self.accession, self.comment)

    def __repr__(self):
        return "{self.__class__.__name__}({self.predicate}, {self.accession}, {self.comment})".format(self=self)

    @classmethod
    def fromstring(cls, string):
        groups_match = re.search(
            r"(?P<predicate>\S+):?\s(?P<accession>\S+)\s?(?:!\s(?P<comment>.*))?",
            string)
        if groups_match is None:
            raise ValueError("Could not parse relationship from %r" % string)
        else:
            groups = groups_match.groupdict()
            if groups['predicate'] in cls.dispatch:
                return cls.dispatch[groups['predicate']](**groups)
            return cls(**groups)


class HasValueTypeRelationship(Relationship):
    name = "has_value_type"

    def __init__(self, predicate, accession, comment=None):
        super(HasValueTypeRelationship, self).__init__(predicate, accession, comment=comment)
        self.value_type = None

    def make_value_type(self, vocabulary):
        # We have a built-in data type with known semantics
        if 'xsd' in self.accession:
            self.value_type = TypeDefinition(self.accession, self.comment or self.accession, parse_xsdtype(self.accession))
        else:
            term = vocabulary[self.accession]
            self.value_type = term.as_value_type()

    def parse(self, value):
        if self.value_type is None:
            raise NotImplementedError()
        return self.value_type(value)

    def format(self, value):
        if self.value_type is None:
            raise NotImplementedError()
        return self.value_type.format(value)

    def __call__(self, value):
        return self.parse(value)


Relationship.dispatch[HasValueTypeRelationship.name] = HasValueTypeRelationship
