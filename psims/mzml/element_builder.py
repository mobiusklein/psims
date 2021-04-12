from six import add_metaclass


class ParamManagingProperty(object):
    '''A descriptor that will delegate value storage to
    the bound instance's :attr:`binding`, and can be
    enumerated by :class:`ParamManagingMeta` to set up
    defaults.

    Attributes
    ----------
    name: str
        The key to delegate to.
    default_value: object
        The value to initialize the bound key to, or a callable
        to provide that value.
    aliases: dict
        Alternative names to map the name
    '''

    def __init__(self, name, default_value=None, aliases=None):
        self.name = name
        self.default_value = default_value
        self.aliases = {a: name for a in aliases or []}

    def __get__(self, obj, cls=None):
        try:
            value = obj.binding[self.name]
        except KeyError:
            value = obj.binding[self.name] = self.default_value
        return value

    def __set__(self, obj, value):
        obj.binding[self.name] = value

    def __delete__(self, obj):
        del obj.binding[self.name]

    def _init_default(self, obj):
        if callable(self.default_value):
            obj.binding.setdefault(self.name, self.default_value())
        else:
            obj.binding.setdefault(self.name, self.default_value)

    def __repr__(self):
        return "{self.__class__.__name__}({self.name!r}, {self.default_value!r})".format(self=self)


class ParamManagingMeta(type):
    '''Register :class:`ParamManagingProperty` bound to
    the initializing class so they can be enumerated
    at a later point.

    Attributes
    ----------
    _binding_props: list
        A list of :class:`ParamManagingProperty` attached to this type
    '''

    def __new__(cls, name, parents, attrs):
        new_type = type.__new__(cls, name, parents, attrs)
        new_type._binding_props = []
        for key, value in attrs.items():
            if isinstance(value, ParamManagingProperty):
                new_type._binding_props.append(value)
        for parent in parents:
            new_type._binding_props.extend(
                getattr(parent, '_binding_props', []))
        return new_type


@add_metaclass(ParamManagingMeta)
class ElementBuilder(object):
    '''A type to accumulate information in to allow
    '''
    binding_name = None

    def __init__(self, source, binding=None, params=None, **kwargs):
        if binding is None:
            binding = dict()
        else:
            binding = dict(binding)

        self.source = source
        self.binding = dict()
        self._init_defaults()
        self.update(binding)
        self.update(kwargs)

    def add_param(self, value):
        self.params.append(value)
        return self

    def set(self, key=None, value=None, **kwargs):
        if key is not None:
            self[key] = value
        if kwargs:
            for key, value in kwargs.items():
                self[key] = value
        return self

    params = ParamManagingProperty('params', list)

    def _init_defaults(self):
        aliases = dict()
        for prop in self._binding_props:
            prop._init_default(self)
            aliases.update(prop.aliases)
        self._aliases = aliases

    def __repr__(self):
        fmt = "{self.__class__.__name__}({self.binding})"
        return fmt.format(self=self)

    def keys(self):
        return self.binding.keys()

    def values(self):
        return self.binding.values()

    def items(self):
        return self.binding.items()

    def get(self, key, value=None):
        if key in self._aliases:
            key = self._aliases[key]
        return self.binding.get(key, value)

    def __getitem__(self, key):
        if key in self._aliases:
            key = self._aliases[key]
        return self.binding[key]

    def __setitem__(self, key, item):
        if key in self._aliases:
            key = self._aliases[key]
        self.binding[key] = item
        return self

    def __iter__(self):
        return iter(self.binding)

    def update(self, _value):
        for key, value in _value.items():
            self[key] = value
        return self

    def pack(self):
        result = {}
        for key, value in self.binding.items():
            if isinstance(value, ElementBuilder):
                if value.binding_name is not None:
                    key = value.binding_name
                value = value.pack()
            if isinstance(value, list):
                value = [v.pack() if isinstance(v, ElementBuilder)
                         else v for v in value]
            if key == 'params' and not value:
                continue
            result[key] = value
        if result:
            return result
        return