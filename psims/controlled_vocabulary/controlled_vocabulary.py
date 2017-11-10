import os
import pkg_resources
try:
    from urllib2 import urlopen, URLError
except ImportError:
    from urllib.request import urlopen, URLError
from .obo import OBOParser
from . import unimod


def _use_vendored_psims_obo():
    return pkg_resources.resource_stream(__name__, "vendor/psi-ms.obo")


def _use_vendored_unit_obo():
    return pkg_resources.resource_stream(__name__, "vendor/unit.obo")


def _use_vendored_unimod_xml():
    return pkg_resources.resource_stream(__name__, "vendor/unimod_tables.xml")


fallback = {
    ("http://psidev.cvs.sourceforge.net/*checkout*/"
     "psidev/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"): _use_vendored_psims_obo,
    ("http://psidev.cvs.sourceforge.net/viewvc/*checkout*/"
     "psidev/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"): _use_vendored_psims_obo,
    ("http://obo.cvs.sourceforge.net/*checkout*/"
     "obo/obo/ontology/phenotype/unit.obo"): _use_vendored_unit_obo
}


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
        except KeyError as e:
            try:
                return self._names[key]
            except KeyError:
                try:
                    return self._names[self.normalize_name(key)]
                except KeyError as e2:
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
    """A cache for retrieved ontology sources

    Attributes
    ----------
    cache_exists : bool
        Whether the cache directory exists
    cache_path : str
        The path to the cache directory
    enabled : bool
        Whether the cache will be used or not
    resolvers : dict
        A mapping from ontology URL to a function
        which will be called instead of opening the
        URL to retrieve the :class:`ControlledVocabulary`
        object.
    """

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

    def _open_url(self, uri):
        try:
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
        except Exception:
            if uri in fallback:
                f = fallback[uri]()
            else:
                raise ValueError(uri)
        return f

    def resolve(self, uri):
        if uri in self.resolvers:
            return self.resolvers[uri](self)
        try:
            if self.enabled:
                name = self.path_for(uri)
                if os.path.exists(name) and os.path.getsize(name) > 0:
                    return open(name)
                else:
                    f = self._open_url(uri)
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
                f = self._open_url(uri)
                return f
        except ValueError:
            import traceback
            traceback.print_exc()
            raise

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
        try:
            return unimod.Unimod(path)
        except IOError:
            return unimod.Unimod(path, _use_vendored_unimod_xml())
    else:
        try:
            return unimod.Unimod()
        except IOError:
            return unimod.Unimod(None, _use_vendored_unimod_xml())


obo_cache = OBOCache(enabled=False)
obo_cache.set_resolver("http://www.unimod.org/obo/unimod.obo", resolve_unimod)


def configure_obo_store(path):
    if path is None:
        obo_cache.enabled = False
    else:
        obo_cache.cache_path = path
        obo_cache.enabled = True


def register_resolver(name, fn):
    obo_cache.set_resolver(name, fn)


def load_psims():
    cv = obo_cache.resolve(("http://psidev.cvs.sourceforge.net/*checkout*/"
                            "psidev/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"))
    return ControlledVocabulary.from_obo(cv)
