from collections import deque
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

from psims.utils import ensure_iterable

from .type_definition import parse_xsdtype


class Entity(Mapping):
    '''Represent a term in a controlled vocabulary.

    While this type implements the :class:`~collections.abc.Mapping`,
    it supports attribute access notation for keys.

    Attributes
    ----------
    children : list of :class:`Entity`
        Additional entities derived from this one
    data : :class:`dict`
        An arbitrary attribute store representing key-value pairs
    vocabulary : :class:`~.ControlledVocabulary`
        The source vocabulary. May be used for upward references
    id : str
        The CURI-style identifier of this entity, the accession of the term.
    definition : str
        The "def" field of a term.

    '''
    def __init__(self, vocabulary=None, **attributes):
        self.data = dict(attributes)
        self.children = []
        self.vocabulary = vocabulary

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if key in ("vocabulary", "children", "data"):
            object.__setattr__(self, key, value)
        else:
            self[key] = value

    def __dir__(self):
        keys = set(self.keys())
        if hasattr(object, '__dir__'):
            keys |= set(object.__dir__(self))
        else:
            keys |= set(self.__dict__.keys())
            keys |= set(self.__class__.__dict__.keys())
        return sorted(keys)

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.keys())

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def setdefault(self, key, value):
        self.data.setdefault(key, value)

    @property
    def definition(self):
        return self.data.get("def", '')

    @definition.setter
    def definition(self, value):
        self.data['def'] = value

    def parent(self):
        '''Fetch the parent or parents of this :class:`Entity`
        in the bound controlled vocabulary.

        Returns
        -------
        :class:`Entity` or :class:`list` of :class:`Entity`
        '''
        try:
            reference = self.is_a
        except KeyError:
            return None
        try:
            return self.vocabulary[reference]
        except TypeError:
            return [self.vocabulary[r] for r in reference]

    def __repr__(self):
        template = 'Entity({self.id!r}, {self.name!r}, {self.definition!r})'
        return template.format(self=self)

    def is_of_type(self, tp):
        '''Test if `tp` is an ancestor of this :class:`Entity`

        Parameters
        ----------
        tp : str
            The identifier for the entity to test

        Returns
        -------
        bool
        '''
        if isinstance(tp, str):
            try:
                tp = self.vocabulary[tp]
            except KeyError:
                return False
        stack = deque([self])
        while stack:
            ref = stack.pop()
            if ref == tp:
                return True
            stack.extend(ensure_iterable(ref.parent()))
        return False
