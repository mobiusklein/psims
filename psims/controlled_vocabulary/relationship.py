import re


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
    def __init__(self, predicate, accession, comment=None):
        self.predicate = predicate
        self.accession = accession
        self.comment = comment

    def __str__(self):
        return "%s: %s ! %s" % (self.predicate, self.accession, self.comment)

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
            return cls(**groups)
