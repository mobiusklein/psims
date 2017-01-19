import re


class Relationship(object):
    def __init__(self, predicate, accession, comment=None):
        self.predicate = predicate
        self.accession = accession
        self.comment = comment

    def __eq__(self, other):
        try:
            return self.accession == other.accession
        except AttributeError:
            return self.accession == other

    def __ne__(self, other):
        return not (self.accession == other.accession)

    def __repr__(self):
        return "%s ! %s" % (self.accession, self.comment)

    def __hash__(self):
        return hash(self.accession)

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
