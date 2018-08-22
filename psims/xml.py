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


class CountedType(type):
    """A metaclass to keep a count of the number of times
    an instance of each derived class is created.
    """
    _cache = {}

    def __new__(cls, name, parents, attrs):
        new_type = type.__new__(cls, name, parents, attrs)
        tag_name = attrs.get("tag_name")
        new_type.counter = staticmethod(make_counter())
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


@add_metaclass(CountedType)
class TagBase(object):

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
            self._id_number = self.counter()
            self._id_string = None
            self._force_id = False
        elif isinstance(_id, int):
            self._id_number = _id
            self._id_string = None
        elif isinstance(_id, basestring):
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
        yield "id"
        for key in self.attrs:
            yield key

    def get(self, name, default):
        return getattr(self, name, default)

    @property
    def id(self):
        if self._id_string is None:
            self._id_string = id_maker(self.tag_name, self._id_number)
        return self._id_string

    def element(self, xml_file=None, with_id=False):
        with_id = with_id or self._force_id
        attrs = {k: attrencode(v) for k, v in self.attrs.items() if v is not None}
        if with_id:
            attrs['id'] = self.id
        if xml_file is None:
            return etree.Element(self.tag_name, **attrs)
        else:
            return xml_file.element(self.tag_name, **attrs)

    def write(self, xml_file, with_id=False):
        el = self.element(with_id=with_id)
        xml_file.write(el)

    def bind(self, xml_file):
        self._xml_file = xml_file
        self._context_manager = None

    @contextmanager
    def begin(self, xml_file, with_id=False):
        with self.element(xml_file, with_id):
            self.is_open = True
            yield
        self.is_open = False

    def __call__(self, xml_file=None, with_id=False):
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
    try:
        eltype = CountedType._cache[_tag_name]
    except KeyError:
        eltype = _make_tag_type(_tag_name)
    return eltype(*args, **kwargs)


def element(xml_file, _tag_name, *args, **kwargs):
    with_id = kwargs.pop("with_id", False)
    if isinstance(_tag_name, basestring):
        el = _element(_tag_name, *args, **kwargs)
    else:
        el = _tag_name
    return el.element(xml_file=xml_file, with_id=with_id)


class CVParam(TagBase):
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
    def __init__(self, full_name, id, uri, version=None, **kwargs):
        self.full_name = full_name
        self.id = id
        self.uri = uri
        self._version = version
        self.options = kwargs
        self._vocabulary = None

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
        if handle is None:
            try:
                fp = controlled_vocabulary.obo_cache.resolve(self.uri)
                cv = controlled_vocabulary.ControlledVocabulary.from_obo(fp)
            except ValueError:
                fp = controlled_vocabulary.obo_cache.fallback(self.uri)
                if fp is not None:
                    cv = controlled_vocabulary.ControlledVocabulary.from_obo(fp)
                else:
                    raise LookupError(self.uri)
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
    def __init__(self, id, uri, converter=identity, **kwargs):
        self.converter = converter
        super(ProvidedCV, self).__init__(id=id, uri=uri, **kwargs)

    def load(self, handle=None):
        cv = controlled_vocabulary.obo_cache.resolve(self.uri)
        try:
            cv.id = self.id
        except Exception:
            pass
        return cv

    def __getitem__(self, key):
        return self.converter(super(ProvidedCV, self).__getitem__(key))

    def query(self, *args, **kwargs):
        return self.convert(super(ProvidedCV, self).query(*args, **kwargs))


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

    def __init__(self, outfile, close=False, compression=None, **kwargs):
        self.outfile = outfile
        self.compression = compression
        self.xmlfile = etree.xmlfile(outfile, encoding='utf-8', **kwargs)
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
        self.toplevel.__exit__(exc_type, exc_value, traceback)
        self.writer.flush()
        self.xmlfile.__exit__(exc_type, exc_value, traceback)
        try:
            self.flush()
        except Exception:
            pass
        if self._should_close():
            self.close()

    def controlled_vocabularies(self, vocabularies=None):
        """Write out the `<cvList>` element and all its children,
        including both this format's default controlled vocabularies
        and those passed as arguments to this method.this

        This method requires writing to have begun.

        Parameters
        ----------
        vocabularies : list of ControlledVocabulary, optional
            A list of additional ControlledVocabulary objects
            which will be used to construct `<cv>` elements
        """
        if vocabularies is None:
            vocabularies = []
        self.vocabularies.extend(vocabularies)
        cvlist = self.CVList(self.vocabularies)
        cvlist.write(self.writer)

    def close(self):
        self.outfile.close()

    def flush(self):
        self.outfile.flush()

    def format(self, outfile=None):
        """Pretty-prints the contents of the file.

        Uses a tempfile.NamedTemporaryFile to receive
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
        if outfile is None:
            use_temp = True
            handle = tempfile.NamedTemporaryFile(delete=False)
        else:
            handle = open(outfile, 'wb')
        try:
            pretty_xml(self.outfile.name, handle.name)
        except MemoryError:
            pass

        if use_temp:
            handle.close()
            os.remove(self.outfile.name)
            try:
                shutil.move(handle.name, self.outfile.name)
            except IOError as e:
                if e.errno == 13:
                    try:
                        time.sleep(3)
                        shutil.move(handle.name, self.outfile.name)
                    except IOError:
                        print(
                            "Could not obtain write-permission for original\
                             file name. Formatted XML document located at \"%s\"" % (
                                handle.name))

    def validate(self):
        prev = None
        try:
            fname = (self.outfile.name)
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
