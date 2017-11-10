class Reference(object):
    def __init__(self, accession, comment=None):
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
        return "Reference(%r, %r)" % (self.accession, self.comment)

    def __hash__(self):
        return hash(self.accession)

    @classmethod
    def fromstring(cls, string):
        try:
            accession, comment = map(lambda s: s.strip(), string.split("!"))
            return cls(accession, comment)
        except Exception:
            return cls(string)
