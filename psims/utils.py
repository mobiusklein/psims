import warnings
import hashlib

from functools import total_ordering

from lxml import etree
from six import add_metaclass, string_types as basestring

try:
    from collections import Iterable, Mapping
except ImportError:
    from collections.abc import Iterable, Mapping

from collections import OrderedDict

from psims import compression


def ensure_iterable(obj):
    if obj is None:
        return tuple()
    if not isinstance(obj, Iterable) or isinstance(obj, basestring) or isinstance(obj, Mapping):
        return [obj]
    return obj


def checksum_file(path, hash_type='sha-1'):
    digestor = hashlib.new(hash_type)
    with open(path, 'rb') as fh:
        chunk_size = 2 ** 16
        chunk = fh.read(chunk_size)
        while chunk:
            digestor.update(chunk)
            chunk = fh.read(chunk_size)
    return digestor.hexdigest()


def pretty_xml(path, outpath=None, encoding=b'utf-8'):
    try:
        path.seek(0)
    except AttributeError:
        pass
    tree = etree.parse(path)
    if outpath is None:
        opener = compression.get(path)
        outpath = opener(path, 'wb')
    if hasattr(outpath, 'write'):
        outstream = outpath
    else:
        opener = compression.get(path)
        outstream = opener(outpath, 'wb')
    with outstream:
        # try to ensure that the stream is at the beginning
        try:
            outstream.seek(0)
        except Exception:
            pass
        formatted = etree.tostring(tree, pretty_print=True, encoding=encoding, xml_declaration=True)
        outstream.write(formatted)


def simple_repr(self):  # pragma: no cover
    template = "{self.__class__.__name__}({d})"

    def formatvalue(v):
        if isinstance(v, float):
            return "%0.4f" % v
        else:
            return str(v)

    if not hasattr(self, "__slots__"):
        d = [
            "%s=%s" % (k, formatvalue(v)) if v is not self else "(...)" for k, v in sorted(
                self.__dict__.items(), key=lambda x: x[0])
            if (not k.startswith("_") and not callable(v)) and not (v is None)]
    else:
        d = [
            "%s=%s" % (k, formatvalue(v)) if v is not self else "(...)" for k, v in sorted(
                [(name, getattr(self, name)) for name in self.__slots__], key=lambda x: x[0])
            if (not k.startswith("_") and not callable(v)) and not (v is None)]

    return template.format(self=self, d=', '.join(d))


@total_ordering
class SimpleVersion(object):
    def __init__(self, major=0, minor=0, patch=0):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __iter__(self):
        yield self.major
        yield self.minor
        yield self.patch

    def __hash__(self):
        return hash(tuple(self))

    def __getitem__(self, i):
        if i == 0:
            return self.major
        elif i == 1:
            return self.minor
        elif i == 2:
            return self.patch
        raise IndexError(i)

    def __len__(self):
        return 3

    def __repr__(self):
        t = "{self.__class__.__name__}({self.major}, {self.minor}, {self.patch})"
        return t.format(self=self)

    def __str__(self):
        return '.'.join(map(str, self))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __lt__(self, other):
        return tuple(self) < tuple(other)

    @classmethod
    def parse(cls, text):
        parts = text.split(".")
        out = []
        for a in parts:
            try:
                v = int(a)
            except (TypeError, ValueError):
                v = a
            out.append(v)
        if len(out) > 3:
            raise ValueError("Not a SimpleVersion")
        return cls(*out)


class KeyToAttrProxy(object):
    def __init__(self, source):
        self.source = source

    def __getitem__(self, key):
        try:
            return getattr(self.source, key)
        except AttributeError:
            raise KeyError(key)

    def keys(self):
        return list(filter(lambda x: not x.startswith("_"), self.source.__dict__.keys()))

    def values(self):
        return [kv[1] for kv in filter(lambda x: not x[0].startswith("_"), self.source.__dict__.items())]

    def items(self):
        return [kv for kv in filter(lambda x: not x[0].startswith("_"), self.source.__dict__.items())]

    def __contains__(self, k):
        return k in self.source.__dict__

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())


class StateSpaceBase(object):
    def validate(self, start, end):
        raise NotImplementedError()

    def next_states(self, current):
        raise NotImplementedError()


class StateTable(StateSpaceBase):
    def __init__(self, table):
        self.table = OrderedDict(table)

    def validate(self, start, end):
        options = self.table[start]
        return end in options

    def next_states(self, current):
        try:
            return list(self.table[current])
        except KeyError:
            return []

    def __getitem__(self, i):
        return list(self.table.items())[i]

    def __len__(self):
        return len(self.states)


class StateTransitionWarning(Warning):
    pass


class StateMachineBase(object):
    def __init__(self, current_state):
        self._current_state = None
        self._previous_state = None
        self.current_state = current_state

    def transition(self, state):
        is_valid = self.states.validate(self.current_state, state)
        self.current_state = state
        if not is_valid:
            self.transition_error()
        return is_valid

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, value):
        self._previous_state = self.current_state
        self._current_state = value

    @property
    def previous_state(self):
        return self._previous_state

    def expects_state(self, state):
        is_valid = self.current_state == state
        if not is_valid:
            self.expects_error(state)
        return is_valid

    def expects_error(self, state):
        warnings.warn(
            ("Action expected {state!r} but current state is {self.current_state!r}").format(
                self=self, state=state), StateTransitionWarning)

    def transition_error(self):
        next_states = self.states.next_states(self.previous_state)
        warnings.warn(
            ("Transition from {self.previous_state!r} to {self.current_state!r} is"
             " not valid. Expected one of {next_states!r}").format(self=self, next_states=next_states),
            StateTransitionWarning)


class TableStateMachine(StateMachineBase):
    def __init__(self, state_table, current_state=None):
        self.states = StateTable(state_table)
        super(TableStateMachine, self).__init__(current_state)
        if current_state is None:
            self.current_state = self.states[0][0]
