class Entity(dict):
    def __init__(self, vocabulary=None, **attributes):
        dict.__init__(self, **attributes)
        object.__setattr__(self, "children", [])
        object.__setattr__(self, "vocabulary", vocabulary)

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if key in ("vocabulary", "children"):
            object.__setattr__(self, key, value)
        else:
            self[key] = value

    def parent(self):
        try:
            reference = self.is_a
        except KeyError:
            return None
        try:
            return self.vocabulary[reference]
        except TypeError:
            return [self.vocabulary[r] for r in reference]
