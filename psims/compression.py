import gzip
import io
import os

from collections import namedtuple, deque

from six import string_types as basestring

OpenerRecord = namedtuple("OpenerRecord", ('opener', 'extension', 'magic_bytes'))

DEFAULT_OPENER = OpenerRecord(open, None, None)


class OpenerRegistry(object):
    def __init__(self, openers=None, default=DEFAULT_OPENER):
        if openers is None:
            openers = []
        self.openers = deque(openers)
        self.default = default

    def add(self, opener, extension=None, magic_bytes=None):
        record = OpenerRecord(opener, extension, magic_bytes)
        self.openers.appendleft(record)

    def __iter__(self):
        return iter(self.openers)

    def __len__(self):
        return len(self.openers)

    def __getitem__(self, i):
        return self.openers[i]

    def by_extension(self, extension):
        for rec in self:
            if rec.extension is None:
                continue
            if rec.extension == extension:
                return rec
        return None

    def by_magic_bytes(self, bytestring):
        for rec in self:
            if rec.magic_bytes is None:
                continue
            if bytestring.startswith(rec.magic_bytes):
                return rec
        return None

    def get(self, path):
        opener = None
        if isinstance(path, basestring):
            ext = os.path.splitext(path)[1]
            opener = self.by_extension(ext)
            if opener is None:
                with open(path, 'rb') as fh:
                    bytestring = fh.read(100)
                    opener = self.by_magic_bytes(bytestring)
        elif hasattr(path, 'read') and hasattr(path, 'tell'):
            current = path.tell()
            path.seek(0)
            bytestring = path.read(100)
            path.seek(current)
            opener = self.by_magic_bytes(bytestring)
        if opener is None:
            return self.default.opener
        else:
            return opener.opener


openers = OpenerRegistry([
    OpenerRecord(gzip.GzipFile, 'gz', b'\037\213'),
])


try:
    import bz2
    openers.add(bz2.BZ2File, 'bz2', None)
except ImportError:
    pass

register = openers.add
get = openers.get
