import warnings
from collections import defaultdict, OrderedDict
from functools import partial, update_wrapper
from contextlib import contextmanager

from .utils import add_metaclass, ensure_iterable, Mapping

from .xml import (
    id_maker, CVParam, UserParam,
    ParamGroupReference, _element,
    XMLWriterMixin)


class ChildTrackingMeta(type):
    def __new__(cls, name, parents, attrs):
        if not hasattr(cls, "_cache"):
            cls._cache = defaultdict(dict)
        new_type = type.__new__(cls, name, parents, attrs)
        ns = getattr(new_type, "component_namespace", None)
        cls._cache[ns][name] = new_type
        return new_type

    @classmethod
    def resolve_component(self, namespace, name):
        try:
            return self._cache[namespace][name]
        except KeyError:
            return self._cache[None][name]


class ReferentialIntegrityWarning(UserWarning):
    pass


class ReferentialIntegrityError(KeyError):
    pass


class SpecializedContextCache(OrderedDict):
    def __init__(self, type_name, missing_reference_is_error=False):
        super(SpecializedContextCache, self).__init__()
        self.type_name = type_name
        self.bijection = dict()
        self.preregistered = dict()
        self.missing_reference_is_error = missing_reference_is_error

    def __getitem__(self, key):
        try:
            item = dict.__getitem__(self, key)
            return item
        except KeyError:
            if key is None:
                return None
            if self.missing_reference_is_error:
                raise ReferentialIntegrityError(key)
            else:
                warnings.warn(
                    "No reference was found for %r in %s" % (key, self.type_name),
                    ReferentialIntegrityWarning,
                    stacklevel=3)
            if isinstance(key, int):
                new_value = id_maker(self.type_name, key)
            else:
                new_value = key
            self[key] = new_value
            return new_value

    def register(self, id):
        if isinstance(id, int):
            value = id_maker(self.type_name, id)
        else:
            value = str(id)
        self[id] = value
        self.preregistered[id] = value
        return value

    def __setitem__(self, key, value):
        if key in self and key not in self.preregistered:
            warnings.warn(
                "Overwriting existing value for %r with %r in store %s" % (
                    key, value, self.type_name), ReferentialIntegrityWarning)
        super(SpecializedContextCache, self).__setitem__(key, value)
        self.bijection[value] = key

    def __repr__(self):
        return '%s\n%s' % (self.type_name, dict.__repr__(self))


class AmbiguousTermWarning(UserWarning):
    pass


class VocabularyResolver(object):
    warn_on_ambiguous_missing_units = True
    validate_units = True

    def __init__(self, vocabularies=None):
        self.vocabularies = vocabularies

    def get_vocabulary(self, id):
        for vocab in self.vocabularies:
            if vocab.id == id:
                return vocab
            try:
                if vocab.full_name == id:
                    return vocab
            except AttributeError:
                pass
        raise KeyError(id)

    def param_group_reference(self, id):
        return ParamGroupReference(id)

    def param(self, name, value=None, cv_ref=None, **kwargs):
        accession = kwargs.get("accession")

        if isinstance(name, CVParam):
            return name
        elif isinstance(name, ParamGroupReference):
            return name
        elif isinstance(name, (tuple, list)) and value is None:
            name, value = name
        elif isinstance(name, Mapping):
            mapping = dict(name)
            if len(mapping) == 1 and 'ref' in mapping:
                return self.param_group_reference(mapping['ref'])
            value = value or mapping.pop('value', None)
            accession = accession or mapping.pop("accession", None)
            cv_ref = cv_ref or mapping.pop("cv_ref", None) or mapping.pop("cvRef", None)
            unit_name = mapping.pop("unit_name", None) or mapping.pop("unitName", None)
            unit_accession = mapping.pop("unit_accession", None) or mapping.pop("unitAccession", None)
            unit_cv_ref = mapping.pop('unit_cv_ref', None) or mapping.pop('unitCvRef', None)
            name = mapping.pop('name', None)
            if name is None and accession is None:
                if len(mapping) == 1:
                    name, value = tuple(mapping.items())[0]
                else:
                    raise ValueError("Could not coerce parameter from %r" % (mapping,))
            else:
                kwargs.update({k: v for k, v in mapping.items()
                               if k not in (
                    "name", "value", "accession")})
                # case normalize unit information so that cvParam can detect them
                if unit_name is not None:
                    kwargs.setdefault("unit_name", unit_name)
                if unit_accession is not None:
                    kwargs.setdefault("unit_accession", unit_accession)
                if unit_cv_ref is not None:
                    kwargs.setdefault("unit_cv_ref", unit_cv_ref)

        self._resolve_units(kwargs)
        if name is None and accession is None:
            raise ValueError("Could not coerce parameter from %r, %r, %r" % (name, value, kwargs))
        term = None
        if cv_ref is None:
            query = accession if accession is not None else name
            cv_ref, name, accession = self._resolve_cv_ref(query, name, accession)
        if term is not None:
            self._validate_units(term, kwargs, name)

        if cv_ref is None:
            return UserParam(name=name, value=value, **kwargs)
        else:
            kwargs.setdefault("ref", cv_ref)
            kwargs.setdefault("accession", accession)
            return CVParam(name=name, value=value, **kwargs)

    def _resolve_cv_ref(self, query, name, accession):
        cv_ref = None
        for cv in self.vocabularies:
            try:
                term = cv[query]
                name = term["name"]
                accession = term["id"]
                if cv_ref is not None:
                    raise ValueError(
                        "Resolutions exist for the term denoted by %r, found in %s and %s" % (
                            query, cv_ref, cv.id
                        ))
                cv_ref = cv.id
            except KeyError:
                continue
        return cv_ref, name, accession

    def _resolve_units(self, state):
        unit_name = state.get("unit_name")
        unit_accession = state.get("unit_accession")
        unit_ref = state.get('unit_cv_ref')
        if unit_name is not None or unit_accession is not None:
            if unit_accession is not None:
                unit_term, source = self.term(unit_accession, include_source=True)
                unit_name = unit_term.name
                unit_accession = unit_term.id
                unit_ref = source.id
            elif unit_name is not None:
                unit_term, source = self.term(unit_name, include_source=True)
                unit_name = unit_term.name
                unit_accession = unit_term.id
                unit_ref = source.id
            state['unit_name'] = unit_name
            state['unit_accession'] = unit_accession
            state['unit_cv_ref'] = unit_ref

    def _validate_units(self, term, state, name):
        has_units = term.get("has_units", [])
        if has_units:
            if len(has_units) == 1:
                provided_unit_accession = state.get("unit_accession")
                if provided_unit_accession is None:
                    try:
                        unit_term, unit_source = self.term(has_units[0].accession, include_source=True)
                        state['unit_accession'] = unit_term.id
                        state['unit_name'] = unit_term.name
                        state['unit_cv_ref'] = unit_source.id
                    except KeyError:
                        pass
                elif self.validate_units:
                    unit_term, unit_source = self.term(has_units[0].accession, include_source=True)
                    if (state['unit_accession'] != unit_term.id or state['unit_name'] != unit_term.name or
                            state['unit_cv_ref'] != unit_source.id):
                        warnings.warn("Provided unit for %r does not match the permitted unit (%r, %r, %r)" % (
                            name,
                            (state['unit_accession'], unit_term.id),
                            (state['unit_name'], unit_term.name),
                            (state['unit_cv_ref'], unit_source.id),
                        ), stacklevel=4)
            elif len(has_units) > 1:
                provided_unit_accession = state.get("unit_accession")
                if provided_unit_accession is None:
                    if self.warn_on_ambiguous_missing_units:
                        warnings.warn(
                            "Multiple unit options are possible for parameter %r but none were specified" % (
                                name),
                            AmbiguousTermWarning,
                            stacklevel=4
                        )
                    try:
                        unit_term, unit_source = self.term(has_units[0].accession, include_source=True)
                        state['unit_accession'] = unit_term.id
                        state['unit_name'] = unit_term.name
                        state['unit_cv_ref'] = unit_source.id
                    except KeyError:
                        pass
                elif self.validate_units:
                    for t in has_units:
                        unit_term, unit_source = self.term(t.accession, include_source=True)
                        if (state['unit_accession'] == unit_term.id and state['unit_name'] == unit_term.name and
                                state['unit_cv_ref'] == unit_source.id):
                            break
                    else:
                        warnings.warn(
                            "Provided unit for %r does not match any of the permitted units %r" % (
                                name,
                                ((state['unit_accession'], state['unit_name'], state['unit_cv_ref']),
                                 has_units)),
                            stacklevel=4
                        )

    def term(self, name, include_source=False):
        deferred = None
        for cv in self.vocabularies:
            try:
                term = cv[name]
                if term.get("is_obsolete", False):
                    deferred = term, cv
                    raise KeyError(name)
                if include_source:
                    return term, cv
                else:
                    return term
            except KeyError:
                pass
        else:
            if deferred:
                if include_source:
                    return deferred
                else:
                    return deferred[0]
            raise KeyError(name)

    def load_vocabularies(self):
        for vocab in self.vocabularies:
            vocab.load()

    def prepare_params(self, params):
        out = []
        for param in ensure_iterable(params):
            out.append(self.param(param))
        return out


class DocumentContext(dict, VocabularyResolver):

    def __init__(self, vocabularies=None, missing_reference_is_error=False):
        dict.__init__(self)
        VocabularyResolver.__init__(self, vocabularies)
        self.missing_reference_is_error = missing_reference_is_error

    def param_group_reference(self, id):
        # This is a inelegant, as ReferenceableParamGroup is not part document type
        # independent, and may not be consistent
        param_group_index = self['ReferenceableParamGroup']
        return ParamGroupReference(param_group_index[id])

    def __getitem__(self, key):
        if not isinstance(key, str):
            if isinstance(key, (type, ReprBorrowingPartial)):
                key = key.__name__
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            if isinstance(key, (type, ReprBorrowingPartial)):
                key = key.__name__
        dict.__setitem__(self, key, value)

    def __missing__(self, key):
        if not isinstance(key, str):
            if isinstance(key, (type, ReprBorrowingPartial)):
                key = key.__name__
        self[key] = SpecializedContextCache(
            key, missing_reference_is_error=self.missing_reference_is_error)
        return self[key]


NullMap = DocumentContext()


class ReprBorrowingPartial(partial):
    """
    Create a partial instance that uses the wrapped callable's
    `__repr__` method instead of a generic partial
    """
    def __init__(self, func, *args, **kwargs):
        self._func = func
        update_wrapper(self, func)

    @property
    def type(self):
        return self._func

    def __repr__(self):
        return repr(self.func)

    def __getattr__(self, name):
        return getattr(self._func, name)

    def ensure(self, data):
        if not isinstance(data, self.type):
            return self(**data)
        else:
            if data.context is not self.context:
                raise ValueError("Cannot bind a component from another context")
        return data

    def ensure_all(self, objs):
        return [self.ensure(obj or {}) for obj in ensure_iterable(objs)]


class CallbackBindingPartial(ReprBorrowingPartial):

    callback = None

    def __call__(self, *args, **kwargs):
        result = super(CallbackBindingPartial, self).__call__(*args, **kwargs)
        if self.callback is not None:
            self.callback(result)
        return result


class ComponentDispatcherBase(object):
    """
    A container for a :class:`DocumentContext` which provides
    an automatically parameterized version of all :class:`ComponentBase`
    types which use this instance's context.

    Attributes
    ----------
    context : :class:`DocumentContext`
        The mapping responsible for managing the global
        state of all created components.
    """
    _component_partial_type = CallbackBindingPartial

    def __init__(self, context=None, vocabularies=None, component_namespace=None, missing_reference_is_error=False):
        if vocabularies is None:
            vocabularies = []
        if context is None:
            context = DocumentContext(vocabularies=vocabularies, missing_reference_is_error=missing_reference_is_error)
        else:
            if vocabularies is not None:
                context.vocabularies.extend(vocabularies)
        self.type_cache = dict()
        self.component_namespace = component_namespace
        self.context = context

    def _prepare_bind_arguments(self):
        return {'context': self.context}

    def _post_constructor(self, component):
        pass

    def _update_component_namespace(self, tp=None):
        return {}

    def _locate_component(self, name):
        try:
            tp = self.type_cache[name]
        except KeyError:
            tp_template = ChildTrackingMeta.resolve_component(self.component_namespace, name)
            new_tp = type(tp_template.__name__, (tp_template, ), self._update_component_namespace(tp_template))
            try:
                new_tp.__module__ = tp_template.__module__
            except AttributeError:
                pass
            try:
                new_tp.__qualname__ = tp_template.__qualname__
            except AttributeError:
                pass
            tp = self._component_partial_type(new_tp, **self._prepare_bind_arguments())
            self.type_cache[name] = tp
        return tp

    def _dispatch_component(self, name):
        tp = self._locate_component(name)
        tp.context = self.context
        tp.callback = self._post_constructor
        return tp

    def __getattr__(self, name):
        """
        Provide access to an automatically parameterized
        version of all :class:`ComponentBase` types which
        use this instance's context.

        Parameters
        ----------
        name : str
            Component Name

        Returns
        -------
        ReprBorrowingPartial
            A partially parameterized instance constructor for
            the :class:`ComponentBase` type requested.
        """
        tp = self._dispatch_component(name)
        return tp

    def ensure_component(self, data, tp):
        if isinstance(data, tp.type):
            if self.context is not data.context:
                raise ValueError("Cannot bind a component from another context")
            return data
        else:
            return tp(**data)

    def register(self, entity_type, id):
        """
        Pre-declare an entity in the document context. Ensures that
        a reference look up will be satisfied.

        Parameters
        ----------
        entity_type : str
            An entity type, either a tag name or a component name
        id : int
            The unique id number for the thing registered

        Returns
        -------
        str
            The constructed reference id
        """
        value = self.context[entity_type].register(id)
        return value

    @property
    def vocabularies(self):
        return self.context.vocabularies

    def load_vocabularies(self):
        self.context.load_vocabularies()

    def param(self, *args, **kwargs):
        return self.context.param(*args, **kwargs)

    def prepare_params(self, params):
        return self.context.prepare_params(params)

    def term(self, *args, **kwargs):
        return self.context.term(*args, **kwargs)

    def get_vocabulary(self, *args, **kwargs):
        return self.context.get_vocabulary(*args, **kwargs)


class XMLBindingDispatcherBase(ComponentDispatcherBase):

    def _post_constructor(self, component):
        component.writer = self.writer


# ------------------------------------------
# Base Component Definitions


@add_metaclass(ChildTrackingMeta)
class ComponentBase(object):
    """A base class for all parts of an XML document which
    describe structures composed of more than a single XML
    tag without any children. In addition to wrapping additional
    descriptive data, this type's metaclass is :class:`ChildTrackingMeta`
    which enables :class:`ComponentDispatcherBase` to automatically bind
    a :class:`DocumentContext` object to the `context` paramter of the
    constructor of dynamically generated wrappers.

    Forwards any missing attribute requests to :attr:`element` for resolution
    against's the XML tag's attributes.
    """

    # in any sane world, these would be initialized in a constructor but
    # would require substantial work to add the super-call to all constructors.
    _context_manager = None
    _is_open = False
    _after_queue = None
    requires_id = True
    writer = None

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, key):
        if key == "element":
            raise AttributeError(
                ("The `element` attribute failed to instantiate "
                 "or is being accessed too early."))
        try:
            return self.element.attrs[key]
        except KeyError:
            raise AttributeError(key)

    def after(self, callback):
        if self._after_queue is None:
            self._after_queue = []
        self._after_queue.append(callback)

    def write(self, xml_file):
        with self.begin(xml_file):
            pass

    def write_content(self, xml_file):
        raise NotImplementedError()

    def bind(self, writer):
        if isinstance(writer, XMLWriterMixin):
            writer = writer.writer
        self.writer = writer
        return self

    def is_bound(self):
        return self.writer is not None

    @contextmanager
    def begin(self, xml_file=None, with_id=None):
        if with_id is None:
            with_id = self.requires_id
        if xml_file is None:
            xml_file = getattr(self, "writer", None)
            if xml_file is None:
                raise ValueError("xml_file must be provided if this component is not bound to a writer!")
        self._is_open = True
        with self.element.begin(xml_file, with_id=with_id):
            self.write_content(xml_file)
            yield
            self._is_open = False
            if self._after_queue:
                for callback in self._after_queue:
                    callback(xml_file)

    def __enter__(self):
        if not self.is_bound():
            raise ValueError(
                "A component not bound to an XMLWriter cannot be used as a context manager directly. "
                "Call the `bind` method first with an ")
        begun = self.begin()
        self._context_manager = begun
        # actually execute the code in `begin` now
        self._context_manager.__enter__()
        return self._context_manager

    def __exit__(self, exc_type, exc_value, traceback):
        # execute all instructions post-yield of begin
        self._context_manager.__exit__(exc_type, exc_value, traceback)
        self._context_manager = None

    def __call__(self, xml_file):
        self.write(xml_file)

    def __repr__(self):
        return "%s\n%s" % (
            self.element, "\n".join([
                "  %s: %r" % (k, v) for k, v in self.__dict__.items()
                if k not in ("context", "element") and not k.startswith("_")])
        )

    def prepare_params(self, params, **kwargs):
        if isinstance(params, Mapping):
            if ("name" not in params and "accession" not in params) and ("ref" not in params):
                params = list(params.items())
            else:
                params = [params]
        elif isinstance(params, (list, tuple)):
            params = list(params)
        else:
            params = list(ensure_iterable(params)) or []
        params.extend(kwargs.items())
        return params

    def has_param(self, query, params=None):
        if params is None:
            params = self.params
        query_param = self.context.term(query)
        for param in params:
            try:
                param = self.context.param(param)
                term = self.context.term(param.accession)
                if term.id == query_param.id:
                    return True
            except KeyError:
                continue
        return False

    def add_param(self, param):
        if isinstance(param, list):
            self.params.extend(param)
        else:
            self.params.append(param)
        return self

    def write_params(self, xml_file, params=None):
        if params is None:
            params = self.params
        params = self.prepare_params(params)
        user_params = []
        cv_params = []
        references = []
        for param in params:
            param = self.context.param(param)
            if isinstance(param, ParamGroupReference):
                references.append(param)
            elif isinstance(param, UserParam):
                user_params.append(param)
            else:
                cv_params.append(param)
        for param in (references + cv_params + user_params):
            param(xml_file)

    @classmethod
    def ensure(cls, obj, **kwargs):
        if isinstance(obj, cls):
            return obj
        else:
            kwargs.update(obj)
            return cls(**kwargs)

    @classmethod
    def ensure_all(cls, objs, **kwargs):
        return [cls.ensure(obj or {}, **kwargs) for obj in ensure_iterable(objs)]


class ParameterContainer(ComponentBase):
    """An base class for a component whose only purpose
    is to contain one or more cv- or userParams.

    Attributes
    ----------
    context : DocumentContext
        The document metadata store
    element : lxml.etree.Element
        The XML tag object to be written
    params : list
        The list of parameters to include
    """
    requires_id = False

    def __init__(self, tag_name, params=None, element_args=None, context=NullMap, **kwargs):
        if element_args is None:
            element_args = dict()
        if params is None:
            params = []
        self.params = self.prepare_params(params, **kwargs)
        self.context = context
        self.element = _element(tag_name, **element_args)

    def write_content(self, xml_file):
        self.write_params(xml_file)


class IDParameterContainer(ParameterContainer):
    requires_id = True
