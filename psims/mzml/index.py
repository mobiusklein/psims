import re

import io
from io import BytesIO
from collections import defaultdict, OrderedDict

from six import string_types as basestring

try:
    from collections.abc import Sequence, Mapping
except ImportError:
    from collections import Sequence, Mapping

from hashlib import sha1

from lxml import etree

from psims import compression


class Offset(object):
    __slots__ = ['offset', 'attrs']

    def __init__(self, offset, attrs):
        self.offset = offset
        self.attrs = attrs

    def __eq__(self, other):
        return int(self) == int(other)

    def __ne__(self, other):
        return int(self) != int(other)

    def __hash__(self):
        return hash(self.offset)

    def __int__(self):
        return self.offset

    def __index__(self):
        return self.offset

    def __repr__(self):
        template = "{self.__class__.__name__}({self.offset}, {self.attrs})"
        return template.format(self=self)


class TagIndexerBase(object):
    attr_pattern = re.compile(br"(\S+)=[\"']([^\"']+)[\"']")

    def __init__(self, name, pattern):
        if isinstance(pattern, str):
            pattern = pattern.encode("utf8")
        if isinstance(pattern, bytes):
            pattern = re.compile(pattern)
        self.name = name
        self.pattern = pattern
        self.index = OrderedDict()

    def __len__(self):
        return len(self.index)

    def __iter__(self):
        return iter(self.index.items())

    def scan(self, data, distance):
        is_match = self.pattern.search(data)
        if is_match:
            attrs = dict(self.attr_pattern.findall(data))
            xid = attrs[b'id']
            offset = Offset(distance + is_match.start(), attrs)
            self.index[xid] = offset
        return bool(is_match)

    def __call__(self, data, distance):
        return self.scan(data, distance)

    def write(self, writer):
        writer.write("    <index name=\"{}\">\n".format(self.name).encode('utf-8'))
        for ref_id, index_data in self.index.items():
            writer.write('      <offset idRef="{}">{:d}</offset>\n'.format(
                ref_id, int(index_data)).encode('utf-8'))
        writer.write(b"    </index>\n")

    def write_xml(self, writer):
        with writer.element("index", name=self.name):
            for ref_id, index_data in self.index.items():
                try:
                    ref_id = ref_id.decode("utf8")
                except AttributeError:
                    pass
                with writer.element("offset", idRef=ref_id):
                    writer.write(str(int(index_data)))


class SpectrumIndexer(TagIndexerBase):
    def __init__(self):
        super(SpectrumIndexer, self).__init__(
            'spectrum', re.compile(b"<spectrum "))


class ChromatogramIndexer(TagIndexerBase):
    def __init__(self):
        super(ChromatogramIndexer, self).__init__(
            'chromatogram', re.compile(b"<chromatogram "))


class IndexList(Sequence):

    """Wrap an arbitrary collection of :class:`TagIndexerBase`-derived
    objects, and support building XML indices.

    Attributes
    ----------
    indexers : list
        A list of :class:`TagIndexerBase`-derived objects to use when
        extracting indices from XML
    """

    def __init__(self, indexers=None):
        if indexers is None:
            indexers = []
        self.indexers = list(indexers)

    def __len__(self):
        return len([ix for ix in self.indexers if len(ix) > 0])

    def __getitem__(self, i):
        return self.indexers[i]

    def __iter__(self):
        return iter(self.indexers)

    def test(self, data, distance):
        for indexer in self:
            if indexer(data, distance):
                return True
        return False

    def __call__(self, data, distance):
        return self.test(data, distance)

    def write_index_list_xml(self, writer, distance):
        offset = distance
        n = len(self)
        with writer.element("indexList", count=str(n)):
            for index in self:
                if len(index) > 0:
                    index.write_xml(writer)
        with writer.element("indexListOffset"):
            writer.write(str(int(offset)))

    def add(self, indexer):
        self.indexers.append(indexer)


class StreamWrapperBase(object):
    def __init__(self, stream):
        if isinstance(stream, basestring):
            stream = io.open(stream, 'wb')
        self.stream = stream

    def write(self, b):
        return self.stream.write(b)

    def flush(self):
        return self.stream.flush()

    def close(self):
        self.stream.close()

    @property
    def closed(self):
        return self.stream.closed

    def writable(self):
        return self.stream.writable()

    @property
    def name(self):
        return self.stream.name


class HashingStream(StreamWrapperBase):
    def __init__(self, stream):
        super(HashingStream, self).__init__(stream)
        self._checksum = sha1()

    def write(self, b):
        n = self.stream.write(b)
        self._checksum.update(b)
        return n

    def checksum(self):
        return self._checksum.hexdigest()


class IndexingStream(StreamWrapperBase):
    def __init__(self, stream):
        # Make sure we keep a handle on the real hashing stream, regardless of
        # whether we wrap it in a buffering layer.
        self.hashing_stream = HashingStream(stream)
        # If the stream created supports writable and the rest of the io.IOBase
        # interface, we can combine it with io.BufferedWriter, cutting down on
        # the number of calls to write on the inner stream.
        try:
            if self.hashing_stream.writable():
                stream = io.BufferedWriter(self.hashing_stream)
            else:
                raise ValueError("Stream %s must be writable!" % self.hashing_stream.stream)
        except AttributeError:
            # No Python-level buffering
            stream = self.hashing_stream
        super(IndexingStream, self).__init__(stream)
        # A running tally of the number of bytes written
        self.accumulator = 0
        self.indices = IndexList()
        self.indices.add(SpectrumIndexer())
        self.indices.add(ChromatogramIndexer())

    # This could be optimized better, split produces a lot of copies.
    def tokenize(self, buff):
        delim = b'<'
        started_with_delim = buff.startswith(delim)
        parts = buff.split(delim)
        tail = parts[-1]
        front = parts[:-1]
        i = 0
        for part in front:
            i += 1
            if part == b"":
                continue
            if i == 1:
                if started_with_delim:
                    yield delim + part
                else:
                    yield part
            else:
                yield delim + part
        if tail.strip() and i > 0:
            yield delim + tail
        else:
            yield tail

    def write(self, data):
        for line in self.tokenize(data):
            self.indices.test(line, self.accumulator)
            self.accumulator += len(line)
            super(IndexingStream, self).write(line)

    def _raw_write(self, data):
        super(IndexingStream, self).write(data)

    def write_index(self, index, name):
        self.write("    <index name=\"{}\">\n".format(name).encode('utf-8'))
        for ref_id, index_data in index.items():
            self.write_offset(ref_id, index_data)
        self.write(b"    </index>\n")

    def checksum(self):
        # Make sure to flush the buffer into the underlying checksum stream so
        # that any final data is written.
        self.flush()
        return self.hashing_stream.checksum()

    def write_index_list(self):
        offset = self.accumulator
        self.indices.write_index_list(self, offset)

    def write_checksum(self):
        self.write(b"  <fileChecksum>")
        self.write(self.checksum().encode('utf-8'))
        self.write(b"</fileChecksum>")

    def to_xml(self, writer):
        offset = self.accumulator
        writer.flush()
        self.indices.write_index_list_xml(writer, offset)
        with writer.element("fileChecksum"):
            writer.flush()
            writer.write(self.checksum())
