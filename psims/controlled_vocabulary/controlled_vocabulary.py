import os
import sys
import re
import logging

from urllib.request import urlopen, Request
from typing import Any, Dict, Hashable, Mapping, Callable, Optional, Union, List

from six import PY2

from psims.utils import ensure_iterable
from psims.controlled_vocabulary.entity import Entity
from psims.controlled_vocabulary.relationship import Reference

from .obo import OBOParser
from . import unimod

from .vendor import (
    _use_vendored_bto_obo, _use_vendored_gno_obo, _use_vendored_go_obo,
    _use_vendored_pato_obo, _use_vendored_psimod_obo, _use_vendored_psims_obo,
    _use_vendored_unimod_xml, _use_vendored_unit_obo, _use_vendored_xlmod_obo)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

fallback = {
    ("http://psidev.cvs.sourceforge.net/*checkout*/"
     "psidev/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"): _use_vendored_psims_obo,
    ("http://psidev.cvs.sourceforge.net/viewvc/*checkout*/"
     "psidev/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"): _use_vendored_psims_obo,
    ("https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo"): _use_vendored_psims_obo,
    "http://purl.obolibrary.org/obo/ms/psi-ms.obo": _use_vendored_psims_obo,
    ("http://obo.cvs.sourceforge.net/*checkout*/"
     "obo/obo/ontology/phenotype/unit.obo"): _use_vendored_unit_obo,
    ("http://ontologies.berkeleybop.org/uo.obo"): _use_vendored_unit_obo,
    "http://purl.obolibrary.org/obo/uo.obo": _use_vendored_unit_obo,
    ("http://ontologies.berkeleybop.org/pato.obo"): _use_vendored_pato_obo,
    ("https://raw.githubusercontent.com/HUPO-PSI/mzIdentML/master/cv/XLMOD.obo"): _use_vendored_xlmod_obo,
    ("http://www.brenda-enzymes.info/ontology/tissue/tree/update/update_files/BrendaTissueOBO"
     ): _use_vendored_bto_obo,
    "http://purl.obolibrary.org/obo/go.obo": _use_vendored_go_obo,
    "https://raw.githubusercontent.com/HUPO-PSI/psi-mod-CV/master/PSI-MOD.obo": _use_vendored_psimod_obo,
    "http://purl.obolibrary.org/obo/gno.obo": _use_vendored_gno_obo,
}


def _default_import_resolver(url: str) -> Optional['ControlledVocabulary']:
    if url.endswith("obo"):
        obo_handle = obo_cache.resolve(url)
        return ControlledVocabulary.from_obo(obo_handle)


def is_curie(text: Union[str, Reference]) -> bool:
    if isinstance(text, Reference):
        text = text.accession
    if isinstance(text, str):
        return re.match(r"(\S+):(\S+)", text)
    else:
        return False



class ControlledVocabulary(Mapping[str, Entity]):
    """
    A Controlled Vocabulary is a collection
    of terms or entities with controlled meanings
    and semantics.

    This object makes entities resolvable by name,
    accession number, or synonym.

    This object implements the :class:`~collections.abc.Mapping` protocol.

    Attributes
    ----------
    id : str
        Unique identifier for this collection
    metadata : dict
        A mapping of metadata describing this controlled vocabulary
    version : str
        A string describing the version of this controlled vocabulary.
        Not all vocabularies are versioned the same way, so this is value
        is not interpreted further automatically.
    name : str
        A human-friendly name for this controlled vocabulary
    terms : dict
        The storage for storing the primary mapping from term ID to terms
    """

    id: str
    version: str
    name: str
    metadata: Dict[str, Any]
    import_resolver: Callable[[str], 'ControlledVocabulary']
    terms: Dict[str, Entity]
    type_definitions: Dict[str, Any]
    imports: Dict[str, 'ControlledVocabulary']

    @classmethod
    def from_obo(cls, handle, **kwargs):
        '''
        Construct a new instance from an OBO format stream.

        Parameters
        ----------
        handle : file-like
            A file-like object over an OBO format.
        **kwargs
            Passed to :meth:`__init__`

        Returns
        -------
        ControlledVocabulary

        Raises
        ------
        ValueError:
            When the controlled vocabulary produced contains no terms
        '''
        parser = OBOParser(handle)
        inst = cls(parser.terms, metadata=parser.header, version=parser.version, name=parser.name, **kwargs)
        if len(parser.terms) == 0:
            raise ValueError("Empty Vocabulary")
        return inst

    def __init__(self, terms, id=None, metadata=None, version=None, name=None, import_resolver: Optional[Callable[[str], 'ControlledVocabulary']]=None):
        if metadata is None:
            metadata = dict()
        if version is None:
            version = 'unknown'
        if import_resolver is None:
            import_resolver = _default_import_resolver
        self.version = version
        self.name = name
        self.id = id
        self.metadata = metadata
        self.type_definitions = dict()
        self._terms = dict()
        self.terms = terms
        self.import_resolver = import_resolver
        self.imports = {}

    def __getitem__(self, key: str) -> Entity:
        '''A wrapper for :meth:`query`'''
        return self.query(key)

    def query(self, key: str) -> Entity:
        '''
        Search for a term whose id or name matches `key`, or if it is a synonym.

        This search is case-insensitive, but case-matching is preferred.

        Parameters
        ----------
        key : str
            The key to look up.

        Returns
        -------
        term : :class:`~.Entity`
            The found entity, if any.

        Raises
        ------
        KeyError :
            If there is no match to any term in this vocabulary

        See Also
        --------
        search
        __getitem__
        '''
        if isinstance(key, Reference):
            key = key.accession
        if key in self.terms:
            return self.terms[key]
        elif key in self._names:
            return self._names[key]
        else:
            try:
                normalized_key = self.normalize_name(key)
                if normalized_key in self._names:
                    return self._names[normalized_key]
            except KeyError:
                # Just to have a value to show.
                normalized_key = key.lower()
            lower_key = key.lower()
            if lower_key in self._synonyms:
                return self._synonyms[lower_key]
            elif lower_key in self.terms:
                return self.terms[lower_key]
            elif lower_key in self._obsolete_names:
                return self._obsolete_names[lower_key]
            else:
                if is_curie(key):

                    result = self._query_imported(key)
                    if result is not None:
                        return result
                raise KeyError("%s and %s were not found." % (key, normalized_key)) from None

    def search(self, query: str) -> List[Entity]:
        '''
        Search for any term containing the query in its id, name, or synonyms.

        This algorithm uses substring containment and may return multiple hits,
        and can be ambiguous when given a common or short substring. For exact
        string matches, use :meth:`query`

        Parameters
        ----------
        query : str
            The search query

        Returns
        -------
        matched : list
            The matched terms.

        See Also
        --------
        query
        '''
        terms = {}
        query = query.lower()
        for key in self.terms:
            if query in key.lower():
                val = self.terms[key]
                terms[val.id] = val
        for key in self._names:
            if query in key.lower():
                val = self._names[key]
                terms[val.id] = val
        for key in self._synonyms:
            if query in key.lower():
                val = self._synonyms[key]
                terms[val.id] = val
        return sorted(terms.values(), key=lambda x: x.id)

    def __repr__(self):
        template = ("{self.__class__.__name__}(terms={size}, id={self.id}, "
                    "name={self.name}, version={self.version})")
        return template.format(self=self, size=len(self.terms))

    def __iter__(self):
        return iter(self.terms)

    def __len__(self):
        return len(self.terms)

    @property
    def terms(self):
        return self._terms

    @terms.setter
    def terms(self, value):
        self._terms = dict(value or {})
        self._reindex()

    def _reindex(self):
        self._build_names()
        self._build_case_normalized()
        self._build_synonyms()
        self._bind_terms()

    def _build_names(self):
        self._names = {
            v['name']: v for v in self.terms.values()
            if not v.get("is_obsolete", False) and isinstance(v['name'], Hashable)
        }
        self._obsolete_names = {
            v['name'].lower(): v for v in self.terms.values()
            if v.get("is_obsolete", False) and isinstance(v['name'], Hashable)
        }

    def _bind_terms(self):
        if PY2 or (sys.version_info.major == 3 and sys.version_info.minor < 6):
            value_typed = []
            for term in self.terms.values():
                term.vocabulary = self
                value_types = term.get('has_value_type')
                if value_types:
                    value_typed.append(value_types)
            for value_types in value_typed:
                for value_type in value_types:
                    value_type.make_value_type(self)

        else:
            for term in self.terms.values():
                term.vocabulary = self
                value_types = term.get('has_value_type')
                if value_types:
                    for value_type in value_types:
                        value_type.make_value_type(self)

    def _build_synonyms(self):
        self._synonyms = {}
        for term in self.terms.values():
            if term.get('synonym'):
                for synonym in term.get('synonym'):
                    self._synonyms[synonym.lower()] = term

    def _build_case_normalized(self):
        self._normalized = {
            v['name'].lower(): v['name']
            for v in self.terms.values()
            if isinstance(v['name'], str)
        }

    def keys(self):
        return self.terms.keys()

    def names(self):
        '''
        A key-view over all the names in this controlled vocabulary, distinct
        from accessions.

        Returns
        -------
        collections.KeysView
        '''
        return self._names.keys()

    def items(self):
        return self.terms.items()

    def normalize_name(self, name):
        return self._normalized[name.lower()]

    def _query_imported(self, query):
        term = None
        for url in ensure_iterable(self.metadata['import']):
            if url in self.imports:
                cv = self.imports[url]
            else:
                try:
                    logger.debug(f"Importing {url} for {self.name}")
                    cv = self.imports[url] = self.import_resolver(url)
                except ValueError:
                    cv = self.imports[url] = None
            if cv is None:
                continue
            try:
                term = cv.query(query)
                break
            except KeyError:
                continue
        return term


DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like'
    ' Gecko) Chrome/68.0.3440.106 Safari/537.36')


class VocabularyResolverBase(Callable):
    def load(self, uri: str):
        raise NotImplementedError()

    def resolve(self, uri: str):
        raise NotImplementedError()

    def fallback(self, uri: str):
        raise NotImplementedError()

    def __call__(self, uri: str):
        return self.resolve(uri)


class OBOCache(VocabularyResolverBase):
    """
    A cache for retrieved ontology sources stored on the file system, and an
    abstraction layer to make registered controlled vocabularies constructable
    from a URI even if they are not in the same format.

    Attributes
    ----------
    cache_exists : bool
        Whether the cache directory exists
    cache_path : str
        The path to the cache directory
    enabled : bool
        Whether the cache will be used or not
    resolvers : dict
        A mapping from ontology URL to a function which will be called instead of
        opening the URL to retrieve the :class:`ControlledVocabulary` object. A
        resolver is any callable that takes only an :class:`OBOCache` instance as
        a single argument.
    use_remote : bool
        Whether or not to try to access remote repositories over the network to
        retrieve controlled vocabularies. If not, will automatically default to
        either the cached copy or use the fallback value.
    user_agent_emulation : bool
        Whether or not to try to emulate a web browser's user agent when trying
        to download a controlled vocabulary.
    """

    default_resolvers = {}

    def __init__(self, cache_path='.obo_cache', enabled=True, resolvers=None, use_remote=True,
                 user_agent_emulation=True):
        self._cache_path = None
        self.cache_path = cache_path
        self.enabled = enabled
        self.resolvers = resolvers or {}
        self.use_remote = use_remote
        self.user_agent_emulation = user_agent_emulation
        self._register_default_resolvers()

    def _register_default_resolvers(self):
        for uri, resolver in self.default_resolvers.items():
            self.set_resolver(uri, resolver)

    @property
    def cache_path(self):
        return self._cache_path

    @cache_path.setter
    def cache_path(self, value):
        self._cache_path = value
        self.cache_exists = os.path.exists(self.cache_path)

    def path_for(self, name, setext=False):
        '''
        Construct a path for a given controlled vocabulary file
        in the cache on the file system.

        .. note::
            If the cache directory does not exist, this will create it.

        Parameters
        ----------
        name : str
            The name of the controlled vocabulary file
        setext : bool
            Whether or not to enforce the .obo extension

        Returns
        -------
        path : str
            The path in the file system cache to use for this name.
        '''
        if not self.cache_exists:
            os.makedirs(self.cache_path)
            self.cache_exists = True
        name = os.path.basename(name)
        if not name.endswith(".obo") and setext:
            name += '.obo'
        return os.path.join(self.cache_path, name)

    def _open_url(self, uri):
        try:
            if not self.use_remote:
                raise Exception("Fail fast!")
            headers = {}
            if self.user_agent_emulation:
                headers['User-Agent'] = DEFAULT_USER_AGENT
            req = Request(uri, headers=headers)
            f = urlopen(req)
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

    def fallback(self, uri):
        '''
        Obtain a stream for the vocabulary specified by `uri`
        from the packaged bundle distributed with :mod:`psims`.

        Parameters
        ----------
        uri : str
            The URI to retrieve a fallback stream for.

        Returns
        -------
        result : file-like or :const:`None`
            Returns a backup stream, or :const:`None` if no fallback exists.
        '''
        if uri in fallback:
            f = fallback[uri]()
        else:
            logger.warning("Failed to locate fallback for %r", uri)
            f = None
        return f

    def has_custom_resolver(self, uri):
        '''
        Test if `uri` has a resolver function.

        Parameters
        ----------
        uri : str
            The URI to test

        Returns
        -------
        bool
        '''
        return uri in self.resolvers

    def resolve(self, uri):
        '''
        Get an readable file-like object for the controlled vocabulary referred
        to by `uri`.

        If `uri` has a custom resolver, by :meth:`has_custom_resolver`, the custom
        resolver function will be called instead.

        Parameters
        ----------
        uri : str
            The URI for the controlled vocabulary to access

        Returns
        -------
        fp : object
            If `uri` has a custom resolver, any type may be returned, otherwise a readable
            file-like object in binary mode over the requested controlled vocabulary.
        '''
        if self.has_custom_resolver(uri):
            return self.resolvers[uri](self)
        try:
            if self.enabled:
                name = self.path_for(uri)
                if os.path.exists(name) and os.path.getsize(name) > 0:
                    return open(name, 'rb')
                else:
                    f = self._open_url(uri)
                    with open(name, 'wb') as cache_f:
                        n_chars = 0
                        for i, line in enumerate(f.readlines()):
                            n_chars += len(line)
                            cache_f.write(line)
                        if n_chars < 5:
                            raise ValueError("No bytes written")
                    if os.path.getsize(name) > 0:
                        return open(name, 'rb')
                    else:
                        raise ValueError("Failed to download file")
            else:
                f = self._open_url(uri)
                return f
        except ValueError:
            import traceback
            traceback.print_exc()
            raise

    def load(self, uri: str):
        if self.has_custom_resolver(uri):
            return self.resolvers[uri](self)
        try:
            fh = self.resolve(uri)
        except ValueError:
            fh = self.fallback(uri)
            if fh is None:
                raise ValueError(f"Failed to resolve {uri} or via its fall-back")
        if uri.endswith("obo"):
            cv = ControlledVocabulary.from_obo(fh, import_resolver=self.load)
            return cv
        else:
            raise ValueError(f"Don't know how to load {uri}")

    def set_resolver(self, uri: str, resolver: Callable[[], ControlledVocabulary]):
        '''
        Register a resolver callable for `uri`

        Parameters
        ----------
        uri : str
            The URI to register the custom resolver for
        resolver : Callable
            A resolver is any callable that takes only an :class:`OBOCache` instance as
            a single argument.
        '''
        self.resolvers[uri] = resolver

    def __repr__(self):
        return "OBOCache(cache_path=%r, enabled=%r, resolvers=%s)" % (
            self.cache_path, self.enabled, self.resolvers)


def _make_relative_sqlite_sqlalchemy_uri(path):
    return "sqlite:///%s" % path


def resolve_unimod(cache):
    '''Custom resolver for UNIMOD store'''
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


OBOCache.default_resolvers.setdefault("http://www.unimod.org/obo/unimod.obo", resolve_unimod)
obo_cache = OBOCache(enabled=False)


def configure_obo_store(path):
    """
    Specify where the default :class:`OBOCache` instance should cache files to.

    Parameters
    ----------
    path : :class:`str` or :const:`None`
        The path to store the OBO cache, or :const:`None` disables it.
    """
    if path is None:
        obo_cache.enabled = False
    else:
        obo_cache.cache_path = path
        obo_cache.enabled = True


def register_resolver(name: str, fn: Callable[[], ControlledVocabulary]):
    """Register a resolver on the default :class:`OBOCache` instance"""
    obo_cache.set_resolver(name, fn)


def load_psims() -> ControlledVocabulary:
    """Load the PSI-MS controlled vocabulary"""
    try:
        cv = obo_cache.resolve(
            ("http://purl.obolibrary.org/obo/ms/psi-ms.obo"))
        return ControlledVocabulary.from_obo(cv)
    except TypeError:
        cv = _use_vendored_psims_obo()
        return ControlledVocabulary.from_obo(cv)


def load_uo():
    """Load the Unit ontology"""
    cv = obo_cache.resolve("http://purl.obolibrary.org/obo/uo.obo")
    return ControlledVocabulary.from_obo(cv)


def load_pato():
    cv = obo_cache.resolve("http://purl.obolibrary.org/obo/pato.obo")
    return ControlledVocabulary.from_obo(cv)


def load_xlmod():
    """Load the XL-MOD cross linking modification controlled vocabulary"""
    cv = obo_cache.resolve("https://raw.githubusercontent.com/HUPO-PSI/mzIdentML/master/cv/XLMOD.obo")
    return ControlledVocabulary.from_obo(cv)


def load_unimod():
    """Load the UNIMOD protein modification controlled vocabulary"""
    return obo_cache.resolve("http://www.unimod.org/obo/unimod.obo")


def load_bto():
    cv = obo_cache.resolve("http://www.brenda-enzymes.info/ontology/tissue/tree/update/update_files/BrendaTissueOBO")
    return ControlledVocabulary.from_obo(cv)


def load_go():
    cv = obo_cache.resolve("http://purl.obolibrary.org/obo/go.obo")
    return ControlledVocabulary.from_obo(cv)


def load_psimod():
    cv = obo_cache.resolve("https://raw.githubusercontent.com/HUPO-PSI/psi-mod-CV/master/PSI-MOD.obo")
    return ControlledVocabulary.from_obo(cv)


def load_gno():
    cv = obo_cache.resolve("http://purl.obolibrary.org/obo/gno.obo")
    return ControlledVocabulary.from_obo(cv)
