import os
try:
    from urllib2 import urlopen
except:
    from urllib.request import urlopen
from .obo import OBOParser
from . import unimod


class ControlledVocabulary(object):
    """A Controlled Vocabulary is a collection
    of terms or entities with controlled meanings
    and semantics.

    This object makes entities resolvable by name,
    accession number, or synonym.

    Attributes
    ----------
    id : str
        Unique identifier for this collection
    """
    @classmethod
    def from_obo(cls, handle):
        parser = OBOParser(handle)
        inst = cls(parser.terms)
        assert len(parser.terms) > 0
        return inst

    def __init__(self, terms, id=None):
        self.terms = terms
        for term in terms.values():
            term.vocabulary = self
        self._names = {
            v['name']: v for v in terms.values()
        }
        self._normalized = {
            v['name'].lower(): v['name']
            for v in terms.values()
        }
        self.id = id

    def __getitem__(self, key):
        try:
            return self.terms[key]
        except KeyError, e:
            try:
                return self._names[key]
            except KeyError:
                try:
                    return self._names[self.normalize_name(key)]
                except KeyError, e2:
                    raise KeyError("%s and %s were not found." % (e, e2))

    def __iter__(self):
        return iter(self.terms)

    def keys(self):
        return self.terms.keys()

    def names(self):
        return self._names.keys()

    def items(self):
        return self.terms.items()

    def normalize_name(self, name):
        return self._normalized[name.lower()]


class OBOCache(object):
    def __init__(self, cache_path='.obo_cache', enabled=True, resolvers=None):
        self._cache_path = None
        self.cache_path = cache_path
        self.enabled = enabled
        self.resolvers = resolvers or {}

    @property
    def cache_path(self):
        return self._cache_path

    @cache_path.setter
    def cache_path(self, value):
        self._cache_path = value
        self.cache_exists = os.path.exists(self.cache_path)

    def path_for(self, name, setext=True):
        if not self.cache_exists:
            os.makedirs(self.cache_path)
            self.cache_exists = True
        name = os.path.basename(name)
        if not name.endswith(".obo") and setext:
            name += '.obo'
        return os.path.join(self.cache_path, name)

    def resolve(self, uri):
        if uri in self.resolvers:
            return self.resolvers[uri](self)
        try:
            if self.enabled:
                name = self.path_for(uri)
                if os.path.exists(name) and os.path.getsize(name) > 0:
                    return open(name)
                else:
                    f = urlopen(uri)
                    code = None
                    # The keepalive library monkey patches urllib2's urlopen and returns
                    # an object with a different API. First handle the normal case, then
                    # the patched case.
                    if hasattr(f, 'getcode'):
                        code = f.getcode()
                    elif hasattr(f, "code"):
                        code = f.code
                    else:
                        raise ValueError("Can't understand how to get HTTP response code from %r" % f)
                    if code != 200:
                        raise ValueError("%s did not resolve" % uri)
                    with open(name, 'w') as cache_f:
                        n_chars = 0
                        for i, line in enumerate(f.readlines()):
                            n_chars += len(line)
                            cache_f.write(line)
                        if n_chars < 5:
                            raise ValueError("No bytes written")
                    if os.path.getsize(name) > 0:
                        return open(name)
                    else:
                        raise ValueError("Failed to download .obo")
            else:
                f = urlopen(uri)
                code = None
                if hasattr(f, 'getcode'):
                    code = f.getcode()
                elif hasattr(f, "code"):
                    code = f.code
                if code != 200:
                    raise ValueError("%s did not resolve" % uri)
                return urlopen(uri)
        except ValueError:
            import traceback
            traceback.print_exc()

    def set_resolver(self, uri, provider):
        self.resolvers[uri] = provider

    def __repr__(self):
        return "OBOCache(cache_path=%r, enabled=%r, resolvers=%s)" % (
            self.cache_path, self.enabled, self.resolvers)


def _make_relative_sqlite_sqlalchemy_uri(path):
    return "sqlite:///%s" % path


def resolve_unimod(cache):
    if cache.enabled:
        path = _make_relative_sqlite_sqlalchemy_uri(
            cache.path_for("unimod.db", False))
        return unimod.Unimod(path)
    else:
        return unimod.Unimod()


obo_cache = OBOCache(enabled=False)
obo_cache.set_resolver("http://www.unimod.org/obo/unimod.obo", resolve_unimod)
