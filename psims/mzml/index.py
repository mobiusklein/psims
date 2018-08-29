import re

from io import BytesIO
from collections import defaultdict, OrderedDict

try:
    from collections import Sequence, Mapping
except ImportError:
    from collections.abc import Sequence, Mapping

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


class SpectrumIndexer(TagIndexerBase):
    def __init__(self):
        super(SpectrumIndexer, self).__init__(
            'spectrum', re.compile(b"<spectrum "))


class ChromatogramIndexer(TagIndexerBase):
    def __init__(self):
        super(ChromatogramIndexer, self).__init__(
            'chromatogram', re.compile(b"<chromatogram "))


class IndexList(Sequence):
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

    def write_index_list(self, writer, distance):
        offset = distance
        n = len(self)
        writer.write("  <indexList count=\"{:d}\">\n".format(n).encode("utf-8"))
        for index in self:
            if len(index) > 0:
                index.write(writer)
        writer.write(b"  </indexList>\n")
        writer.write(b"  <indexListOffset>")
        writer.write("{:d}</indexListOffset>\n".format(offset).encode("utf-8"))

    def add(self, indexer):
        self.indexers.append(indexer)


class HashingFileBuffer(object):
    def __init__(self):
        self.buffer = BytesIO()
        self.checksum = sha1()
        self.accumulator = 0

    def write(self, data):
        self.buffer.write(data)
        self.accumulator += len(data)
        self.checksum.update(data)
        return self.accumulator


class MzMLIndexer(HashingFileBuffer):
    def __init__(self, source, pretty=True):
        self.source = source
        super(MzMLIndexer, self).__init__()
        self.indices = IndexList()
        self.indices.add(SpectrumIndexer())
        self.indices.add(ChromatogramIndexer())

    def write(self, data):
        self.indices.test(data, self.accumulator)
        return super(MzMLIndexer, self).write(data)

    def write_opening(self):
        header = (b'<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                  b'<indexedmzML xmlns="http://psi.hupo.org/ms/mzml" '
                  b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                  b' xsi:schemaLocation="http://psi.hupo.org/ms/mzml '
                  b'http://psidev.info/files/ms/mzML/xsd/mzML1.1.2_idx.xsd">\n')
        self.write(header)

    def embed_source(self):
        try:
            self.source.seek(0)
        except AttributeError:
            pass
        tree = etree.parse(self.source)
        content = etree.tostring(tree, pretty_print=True).splitlines()
        for line in content:
            indented = b''.join((b'  ', line, b'\n'))
            self.write(indented)

    def write_index(self, index, name):
        self.write("    <index name=\"{}\">\n".format(name).encode('utf-8'))
        for ref_id, index_data in index.items():
            self.write_offset(ref_id, index_data)
        self.write(b"    </index>\n")

    def write_index_list(self):
        offset = self.accumulator
        self.indices.write_index_list(self, offset)

    def write_checksum(self):
        self.write(b"  <fileChecksum>")
        self.write(self.checksum.hexdigest().encode('utf-8'))
        self.write(b"</fileChecksum>\n")

    def write_closing(self):
        self.write(b"</indexedmzML>")

    def write_offset(self, ref_id, index_data):
        self.write('      <offset idRef="{}">{:d}</offset>\n'.format(
            ref_id, index_data).encode('utf-8'))

    def build(self):
        self.write_opening()
        self.embed_source()
        self.write_index_list()
        self.write_checksum()
        self.write_closing()

    def overwrite(self, opener=None):
        if opener is None:
            opener = compression.get(self.source)
        try:
            self.source.seek(0)
            fh = self.source
        except AttributeError:
            fh = opener(self.source, 'wb')
        fh.write(self.buffer.getvalue())
