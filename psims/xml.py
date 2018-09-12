import os
import shutil
import re
from contextlib import contextmanager
import tempfile
import time
from lxml import etree

from . import controlled_vocabulary
from .utils import pretty_xml
from .validation import validate

from six import string_types as basestring, add_metaclass, text_type


try:
    WindowsError
    on_windows = True
except NameError:
    on_windows = False


def make_counter(start=1):
    '''
    Create a functor whose only internal piece of data is a mutable container
    with a reference to an integer, `start`. When the functor is called, it returns
    current `int` value of `start` and increments the mutable value by one.

    Parameters
    ----------
    start: int, optional
        The number to start counting from. Defaults to `1`.

    Returns
    -------
    int:
        The next number in the count progression.
    '''
    start = [start]

    def count_up():
        ret_val = start[0]
        start[0] += 1
        return ret_val
    return count_up


def camelize(name):
    """Adapts an attribute name from "snake_case" to "camelCase"
    to make lookups on Element.attrib easier.

    Parameters
    ----------
    name : str
        Attribute name

    Returns
    -------
    str
        transformed name
    """
    parts = name.split("_")
    if len(parts) > 1:
        return ''.join([parts[0]] + [part.title() if part != "ref" else "_ref" for part in parts[1:]])
    else:
        return name


def id_maker(type_name, id_number):
    return "%s_%s" % (type_name.upper(), str(id_number))


def sanitize_id(string):
    """Remove characters from a string which would be invalid
    in XML identifiers

    Parameters
    ----------
    string : str

    Returns
    -------
    str
    """
    string = re.sub(r"\s", '_', string)
    string = re.sub(r"\\|/", '', string)
    return string


NO_TRACK = object()


class ElementType(type):
    """A metaclass to keep a count of the number of times
    an instance of each derived class is created.
    """
    _cache = {}

    def __new__(cls, name, parents, attrs):
        new_type = type.__new__(cls, name, parents, attrs)
        tag_name = attrs.get("tag_name")
        if attrs.get("_track") is NO_TRACK:
            return new_type
        if not hasattr(cls, "_cache"):
            cls._cache = dict()
        cls._cache[name] = new_type
        if tag_name is not None:
            cls._cache[tag_name] = new_type
        return new_type


def attrencode(o):
    """A simple function to convert most
    basic python types to a string form
    which is safe to serialize in XML
    attributes

    Parameters
    ----------
    o : object
        Attribute value to encode

    Returns
    -------
    str:
        The encoded value
    """
    if isinstance(o, bool):
        return text_type(o).lower()
    else:
        return text_type(o)


@add_metaclass(ElementType)
class TagBase(object):
    """Represent a single XML element with arbitrary attributes.

    Mocks the :class:`Mapping` interface

    Attributes
    ----------
    attrs : dict
        The attributes of the element. :meth:`__getattr__` falls back
        to querying :attr:`attrs`, trying both requested name and ``camelCase``
        versions of the name
    is_open : bool
        Whether the element has been opened as a context manager
    tag_name : str
        The name of the element
    text : str
        The body text of the element
    type_attrs : dict
        Attributes common to all elements of this type
    id : str
        The @id attribute of the element.
    """

    type_attrs = {}

    def __init__(self, tag_name=None, text="", **attrs):
        self.tag_name = tag_name or self.tag_name
        _id = attrs.pop('id', None)
        self.attrs = {}
        self.attrs.update(self.type_attrs)
        self.text = text
        self.attrs.update(attrs)
        # When passing through a XMLWriterMixin.element() call, tags may be reconstructed
        # and any set ids will be passed through the attrs dictionary, but the `with_id`
        # flag won't be propagated. `_force_id` preserves this.
        self._force_id = True
        if _id is None:
            self._id_number = None
            self._id_string = None
            self._force_id = False
        elif isinstance(_id, int):
            self._id_number = _id
            self._id_string = None
        else:
            self._id_number = None
            self._id_string = _id
        self.is_open = False

    def __getattr__(self, key):
        try:
            return self.attrs[key]
        except KeyError:
            try:
                return self.attrs[camelize(key)]
            except KeyError:
                raise AttributeError("%s has no attribute %s" % (self.__class__.__name__, key))

    # Support Mapping Interface
    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def keys(self):
        if self.id is not None:
            yield "id"
        for key in self.attrs:
            yield key

    def get(self, name, default):
        return getattr(self, name, default)

    @property
    def id(self):
        if self._id_string is None and self._id_number is not None:
            self._id_string = id_maker(self.tag_name, self._id_number)
        return self._id_string

    def element(self, xml_file=None, with_id=False):
        """Create an XML element using either a materialized :class:`lxml.etree.Element`
        if ``xml_file`` is :const:`None` or the ephemeral context manager element
        :class:`lxml.etree._FileWriterElement`.

        The element will be constructed with all attributes in :attr:`attrs` where the
        value is not :const:`None`.

        Parameters
        ----------
        xml_file : :class:`XMLWriterMixin`, optional
            The XML writer to build the element for
        with_id : bool, optional
            Whether to require the ID attribute be present and rendered

        Returns
        -------
        :class:`lxml.etree.Element` or :class:`lxml.etree._FileWriterElement`
            Description

        Raises
        ------
        ValueError
            Description
        """
        with_id = with_id or self._force_id
        attrs = {k: attrencode(v) for k, v in self.attrs.items() if v is not None}
        if with_id:
            if self.id is None:
                raise ValueError("Required id for %r but id was None" % (self,))
            attrs['id'] = self.id
        if xml_file is None:
            elt = etree.Element(self.tag_name, **attrs)
            if self.text:
                elt.text = self.text
            return elt
        else:
            return xml_file.element(self.tag_name, **attrs)

    def write(self, xml_file, with_id=False):
        """Write this element to file

        Parameters
        ----------
        xml_file : :class:`XMLWriterMixin`
            The XML writer to build the element for
        with_id : bool, optional
            Whether to require the ID attribute be present and rendered

        See Also
        --------
        :meth:`element`
        """
        el = self.element(with_id=with_id)
        xml_file.write(el)

    def bind(self, xml_file):
        self._xml_file = xml_file

    @contextmanager
    def begin(self, xml_file, with_id=False):
        with self.element(xml_file, with_id):
            self.is_open = True
            yield
        self.is_open = False

    def __call__(self, xml_file=None, with_id=False):
        """Alias of :meth:`element`
        """
        return self.element(xml_file, with_id)

    def __repr__(self):
        return "<%s id=\"%s\" %s>" % (self.tag_name, self.id, " ".join("%s=\"%s\"" % (
            k, attrencode(v)) for k, v in self.attrs.items()))

    def __eq__(self, other):
        try:
            return self.attrs == other.attrs
        except AttributeError:
            return False

    def __ne__(self, other):
        try:
            return self.attrs != other.attrs
        except AttributeError:
            return True

    def __hash__(self):
        return hash((self.tag_name, frozenset(self.attrs.items())))


def identity(x):
    return x


def _make_tag_type(name, **attrs):
    """Creates a new TagBase-derived class dynamically at runtime.
    The new type will be cached.

    Parameters
    ----------
    name : str
        The tag name
    **attrs : dict
        Any class-wide attributes to include

    Returns
    -------
    type
        A TagBase subclass
    """
    return type(name, (TagBase,), {"tag_name": name, "type_attrs": attrs})


def _element(_tag_name, *args, **kwargs):
    """Construct a subclass instance of :class:`TagBase` with the given
    tag name. All other arguments are forwarded to the :class:`TagBase`
    constructor

    Parameters
    ----------
    _tag_name : str
        The name of the tag type to create
    *args
        Arbitrary arguments for the tag
    **kwargs
        Key word arguments for the tag

    Returns
    -------
    :class:`TagBase`
    """

    try:
        eltype = ElementType._cache[_tag_name]
    except KeyError:
        eltype = _make_tag_type(_tag_name)
    return eltype(*args, **kwargs)


def element(xml_file, _tag_name, *args, **kwargs):
    """Construct and immediately write a subclass instance of
    :class:`TagBase` with the given tag name. All other arguments
    are forwarded to the :class:`TagBase` constructor

    Parameters
    ----------
    xml_file : :class:`XMLWriterMixin`
        The XML writer to write to
    _tag_name : str
        The name of the tag type to create
    *args
        Arbitrary arguments for the tag
    **kwargs
        Key word arguments for the tag
    """
    with_id = kwargs.pop("with_id", False)
    if isinstance(_tag_name, basestring):
        el = _element(_tag_name, *args, **kwargs)
    else:
        el = _tag_name
    return el.element(xml_file=xml_file, with_id=with_id)


class CVParam(TagBase):
    """Represents a ``<cvParam />``

    .. note::
        This element holds additional data or annotation. Only controlled values
        are allowed here
    """

    tag_name = "cvParam"
    _track = NO_TRACK

    @classmethod
    def param(cls, name, value=None, **attrs):
        if isinstance(name, cls):
            return name
        elif isinstance(name, (tuple, list)):
            name, value = name
        else:
            if value is None:
                return cls(name=name, **attrs)
            else:
                return cls(name=name, value=value, **attrs)

    @staticmethod
    def _normalize_units(attrs):
        if 'unit_cv_ref' in attrs:
            attrs["unitCvRef"] = attrs.pop("unit_cv_ref")
        if 'unit_accession' in attrs:
            attrs['unitAccession'] = attrs.pop("unit_accession")
        if 'unit_name' in attrs:
            attrs['unitName'] = attrs.pop("unit_name")

        return attrs

    def __init__(self, accession=None, name=None, ref=None, value=None, **attrs):
        if ref is not None:
            attrs["cvRef"] = ref
        if accession is not None:
            attrs["accession"] = accession
        if name is not None:
            attrs["name"] = name
        if value is not None:
            attrs['value'] = value
        else:
            attrs['value'] = ''

        attrs = self._normalize_units(attrs)

        super(CVParam, self).__init__(self.tag_name, **attrs)
        self.patch_accession(accession, ref)

    @property
    def value(self):
        return self.attrs.get("value")

    @value.setter
    def value(self, value):
        self.attrs['value'] = value

    @property
    def ref(self):
        return self.attrs['cvRef']

    @property
    def name(self):
        return self.attrs['name']

    @property
    def accession(self):
        return self.attrs['accession']

    def __call__(self, *args, **kwargs):
        self.write(*args, **kwargs)

    def __repr__(self):
        return "<%s %s>" % (self.tag_name, " ".join("%s=\"%s\"" % (
            k, str(v)) for k, v in self.attrs.items()))

    def patch_accession(self, accession, ref):
        if accession is not None:
            if isinstance(accession, int):
                accession = "%s:%d" % (ref, accession)
                self.attrs['accession'] = accession
            else:
                self.attrs['accession'] = accession


class UserParam(CVParam):
    """Represents a ``<userParam />`` element

    .. note::
        Uncontrolled user parameters (essentially allowing free text). Before
        using these, one should verify whether there is an appropriate CV term
        available, and if so, use the CV term instead

    Attributes
    ----------
    accession : TYPE
        Description
    tag_name : str
        Description
    """

    tag_name = "userParam"
    accession = None


class ParamGroupReference(TagBase):
    tag_name = "referenceableParamGroupRef"

    def __init__(self, ref):
        self.ref = ref
        super(ParamGroupReference, self).__init__(self.tag_name, ref=ref)

    def __call__(self, *args, **kwargs):
        self.write(*args, **kwargs)


class CV(object):
    """Represent a Controlled Vocabulary associated with the current document.

    The controlled vocabulary referenced must specify a URI that will be used
    to either download the definitions from, to be matched to a cache of pre-built
    vocabularies, or to be matched with a set of special resolution rules for
    handled by the :attr:`resolver`.

    This object acts as a lazy-loading proxy for
    :class:`~.controlled_vocabulary.ControlledVocabulary`.

    Attributes
    ----------
    full_name : str
        The full name of the controlled vocabulary, which may or may not
        be identical to the :attr:`id`
    id : str
        A short unique identifier for the controlled vocabulary
    options : :class:`dict`
        Additional information that may be used during resolution
    resolver : :class:`~.VocabularyResolver`
        The resolver which will handle all requests for this controlled vocabulary
    uri : str
        The location where the definition can be found
    version : str
        The version of the vocabulary resolved
    vocabulary : :class:`~.ControlledVocabulary`
        The parsed term graph defining this vocabulary
    """

    def __init__(self, full_name, id, uri, version=None, resolver=None, **kwargs):
        self.full_name = full_name
        self.id = id
        self.uri = uri
        self._version = version
        self.options = kwargs
        self._vocabulary = None
        self.resolver = None

    @property
    def version(self):
        if self._version is None:
            try:
                self._version = self.vocabulary.version
            except AttributeError:
                pass
        return self._version

    @property
    def vocabulary(self):
        if self._vocabulary is None:
            self._vocabulary = self.load()
        return self._vocabulary

    def load(self, handle=None):
        """Load the vocabulary definition from source

        Assumes that the definition is in OBO format

        Parameters
        ----------
        handle : file-like, optional
            An optional file handle which can be read from directly.

        Returns
        -------
        :class:`~.ControlledVocabulary`
            The parsed vocabulary

        Raises
        ------
        KeyError
            When all fallback mechanisms fail, a KeyError is raised
        """
        resolver = self.resolver or controlled_vocabulary.obo_cache
        if handle is None:
            try:
                fp = resolver.resolve(self.uri)
                cv = controlled_vocabulary.ControlledVocabulary.from_obo(fp)
            except ValueError:
                fp = resolver.fallback(self.uri)
                if fp is not None:
                    cv = controlled_vocabulary.ControlledVocabulary.from_obo(fp)
                else:
                    raise KeyError(self.uri)
        else:
            cv = controlled_vocabulary.ControlledVocabulary.from_obo(handle)
        try:
            cv.id = self.id
        except Exception:
            import traceback
            traceback.print_exc()
            pass
        return cv

    def __getitem__(self, key):
        return self.vocabulary[key]

    def query(self, *args, **kwargs):
        return self.vocabulary.query(*args, **kwargs)


class ProvidedCV(CV):
    """A wrapper around another object that provides the same basic interface
    as :class:`CV` from that object, provided through the :attr:`converter`
    function

    Attributes
    ----------
    converter : Callable
        A function that converts elements of the provided vocabulary into
        something matching the :class:`~.controlled_vocabulary.Entity` interface.
    """

    def __init__(self, id, uri, converter=identity, **kwargs):
        self.converter = converter
        super(ProvidedCV, self).__init__(id=id, uri=uri, **kwargs)

    def load(self, handle=None):
        resolver = self.resolver or controlled_vocabulary.obo_cache
        try:
            cv = resolver.resolve(self.uri)
        except ValueError:
            cv = resolver.fallback(self.uri)
            if cv is None:
                raise LookupError(self.uri)
        try:
            cv.id = self.id
        except Exception:
            pass
        return cv

    def __getitem__(self, key):
        return self.converter(super(ProvidedCV, self).__getitem__(key), self)


class XMLWriterMixin(object):
    """A mixin class to provide methods for writing
    XML elements and aggregate Components.

    Attributes
    ----------
    verbose : bool
        Controls debug printing
    writer: lxml.etree._IncrementalFileWriter
        The low-level XML writer used by :attr:`xmlfile`
    """
    verbose = False

    @contextmanager
    def element(self, element_name, **kwargs):
        """Construct and immediately open a subclass instance of
        :class:`TagBase` with the given tag name. All other arguments
        are forwarded to the :class:`TagBase` constructor.

        Parameters
        ----------
        element_name: str
            The name of the tag type to create
        *args
            Arbitrary arguments for the tag
        **kwargs
            Key word arguments for the tag

        See Also
        --------
        :func:`element`
        """
        if self.verbose:
            print("In XMLWriterMixin.element", element_name, kwargs)
        try:
            if isinstance(element_name, basestring):
                with element(self.writer, element_name, **kwargs):
                    yield
            else:
                with element_name.element(self.writer, **kwargs):
                    yield
        except AttributeError:
            if self.writer is None:
                raise ValueError(
                    "This writer has not yet been created."
                    " Make sure to use this object as a context manager using the "
                    "`with` notation or by explicitly calling its __enter__ and "
                    "__exit__ methods.")
            else:
                raise

    def write(self, *args, **kwargs):
        """Either write a complete XML sub-tree or add free text to the file stream

        Parameters
        ----------
        arg: str or :class:`lxml.etree.Element`
            The entity to be written out.
        """
        if self.verbose:
            print(args[0])
        try:
            self.writer.write(*args, **kwargs)
        except AttributeError:
            if self.writer is None:
                raise ValueError(
                    "This writer has not yet been created."
                    " Make sure to use this object as a context manager using the "
                    "`with` notation or by explicitly calling its __enter__ and "
                    "__exit__ methods.")
            else:
                raise


class XMLDocumentWriter(XMLWriterMixin):
    """A base class for types which are used to
    write complete XML documents.

    Attributes
    ----------
    outfile : file
        A writable file object
    toplevel : TagBase
        The top-level XML tag
    xmlfile : lxml.etree.xmlfile
        The XML formatter
    writer : lxml.etree._IncrementalFileWriter
        The low-level XML writer used by :attr:`xmlfile`
    """
    @staticmethod
    def toplevel_tag():
        """Overridable method to construct the appropriate
        tag for :attr:`toplevel`

        Returns
        -------
        TagBase
        """
        raise TypeError("Must specify an XMLDocumentWriter's toplevel_tag attribute")

    def __init__(self, outfile, close=False, encoding=None, **kwargs):
        if encoding is None:
            encoding = 'utf-8'
        self.outfile = outfile
        self.encoding = encoding
        self.xmlfile = etree.xmlfile(outfile, encoding=encoding, **kwargs)
        self._writer = None
        self.toplevel = None
        self._close = close

    def _should_close(self):
        if self._close is None:
            return (self.outfile, 'close')
        return bool(self._close)

    @property
    def writer(self):
        if self._writer is None:
            raise ValueError(
                "The writer hasn't been started yet. Either use the object as a context manager"
                " or call the begin() method")
        return self._writer

    @writer.setter
    def writer(self, value):
        self._writer = value

    def begin(self):
        """Writes the doctype and starts the low-level writing machinery
        """
        if self._has_begun():
            return
        self.writer = self.xmlfile.__enter__()
        self.writer.write_declaration()
        self.toplevel = element(self.writer, self.toplevel_tag())
        self.toplevel.__enter__()

    def _has_begun(self):
        return self.toplevel is not None

    def __enter__(self):
        """Begins writing, opening the top-level tag
        """
        self.begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Closes the top-level tag, the XML formatter,
        and the file itself.
        """
        self.end(exc_type, exc_value, traceback)

    def end(self, exc_type=None, exc_value=None, traceback=None):
        """Ends the XML document, and flushes and closes the file
        """
        self.toplevel.__exit__(exc_type, exc_value, traceback)
        self.writer.flush()
        self.xmlfile.__exit__(exc_type, exc_value, traceback)
        try:
            self.flush()
        except Exception:
            pass
        if self._should_close():
            self.close()

    def controlled_vocabularies(self):
        """Write out the `<cvList>` element and all its children,
        including both this format's default controlled vocabularies
        and those passed as arguments to this method.this

        This method requires writing to have begun.
        """
        cvlist = self.CVList(self.vocabularies)
        cvlist.write(self.writer)

    def close(self):
        try:
            self.outfile.close()
        except AttributeError:
            pass

    def flush(self):
        try:
            self.outfile.flush()
        except AttributeError:
            self.writer.flush()

    def format(self, outfile=None):
        """Pretty-prints the contents of the file.

        Uses a :class:`tempfile.NamedTemporaryFile` to receive
        the formatted XML content, removes the
        original file, and moves the temporary file
        to the original file's name.
        """
        use_temp = False
        # can't format a terminal stream
        try:
            if self.outfile.isatty():
                return
        except (AttributeError, ValueError):
            pass

        # Maybe we can seek to the beginning and open the stream for reading and writing?
        if outfile is None:
            use_temp = True
            handle = tempfile.NamedTemporaryFile(delete=False)
        else:
            handle = open(outfile, 'wb')

        try:
            outfile_name = self.outfile.name
        except AttributeError:
            outfile_name = self.outfile
        try:
            try:
                pretty_xml(outfile_name, handle.name)
            except AttributeError:
                try:
                    pretty_xml(outfile_name, handle.name)
                except Exception as e:
                    print(e)
        except MemoryError:
            pass

        if use_temp:
            handle.close()
            try:
                os.remove(outfile_name)
                try:
                    shutil.move(handle.name, outfile_name)
                except IOError as e:
                    if e.errno == 13:
                        try:
                            time.sleep(3)
                            shutil.move(handle.name, outfile_name)
                        except IOError:
                            print(
                                "Could not obtain write-permission for original\
                                 file name. Formatted XML document located at \"%s\"" % (
                                    handle.name))
            except (AttributeError, TypeError):
                try:
                    self.outfile.seek(0)
                    with open(handle.name, 'rb') as fh:
                        chunk_size = int(2 ** 16)
                        chunk = fh.read(chunk_size)
                        while chunk:
                            self.outfile.write(chunk)
                            chunk = fh.read(chunk_size)
                except AttributeError as e:
                    print("Could not format document", e)

    def validate(self):
        """Attempt to perform XSD validation on the XML document
        this writer wrote

        Returns
        -------
        bool:
            Whether or not the document was valid

        lxml.etree.XMLSchema:
            The schema object where errors are logged

        Raises
        ------
        TypeError
            When the file cannot be recovered from the writer object,
            a :class:`TypeError` is thrown
        """
        prev = None
        try:
            if isinstance(self.outfile, basestring):
                fname = self.outfile
            else:
                fname = self.outfile.name
        except AttributeError:
            if hasattr(self.outfile, 'seek'):
                prev = self.outfile.tell()
                self.outfile.seek(0)
                fname = self.outfile
            else:
                raise TypeError("Can't get file from %r" % (self.outfile,))
        result, schema = validate(fname)
        if prev is not None:
            self.outfile.seek(prev)
        return result, schema
