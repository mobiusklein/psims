import logging
import io
import numbers
import warnings

from typing import Dict
from collections import Counter

import numpy as np

logging.getLogger('hdf5plugin').addHandler(logging.NullHandler())

import h5py
try:
    import hdf5plugin
except ImportError:
    warnings.warn(
        "hdf5plugin is missing! Only the slower GZIP compression scheme will be available! "
        "Please install hdf5plugin to be able to use Blosc.")
    hdf5plugin = None

from ..mzml.binary_encoding import encode_array_direct, encoding_map, compression_map, dtype_to_encoding, COMPRESSION_NONE
from ..mzml.writer import PlainMzMLWriter as _MzMLWriter, NON_STANDARD_ARRAY, ARRAY_TYPES, Mapping
from ..mzml.index import IndexingStream

from . import components


HDF5_COMPRESSORS = {}

DEFAULT_COMPRESSOR = 'gzip'

if hdf5plugin is not None:
    HDF5_COMPRESSORS = {
        "blosc": hdf5plugin.Blosc(),
        "blosc:lz4": hdf5plugin.Blosc('lz4'),
        "blosc:lz4hc": hdf5plugin.Blosc('lz4hc'),
        "blosc:zlib": hdf5plugin.Blosc('zlib'),
        "blosc:zstd": hdf5plugin.Blosc('zstd'),
    }
    HDF5_COMPRESSORS = {k: dict(v) for k, v in HDF5_COMPRESSORS.items()}
    DEFAULT_COMPRESSOR = 'blosc'

HDF5_COMPRESSORS['zlib'] = HDF5_COMPRESSORS['gzip'] = {'compression': 'gzip', 'compression_opts': 4}


HDF5_COMPRESSOR_MAGIC_NUMBERS_TO_NAME = {
    v['compression']: k for k, v in HDF5_COMPRESSORS.items()
}


class ArrayBuffer(object):
    def __init__(self, dataset, dtype, size=1024 ** 2):
        self.dataset = dataset
        self.dtype = dtype
        self.size = size
        self.buffer = io.BytesIO()
        self.offset = 0

    def add(self, array):
        self.buffer.write(array.tobytes())
        self.check()

    def check(self):
        v = self.buffer.tell()
        if v >= self.size:
            self.flush()

    def flush(self):
        array = np.frombuffer(self.buffer.getvalue(), dtype=self.dtype)
        n = len(array)
        total_size = self.offset + n
        if self.dataset.size < total_size:
            self.dataset.resize((total_size, ))
        self.dataset[self.offset:total_size] = array
        self.offset += n
        self.buffer.seek(0)
        self.buffer.truncate(0)


class MzMLbWriter(_MzMLWriter):
    '''A high level API for generating mzMLb HDF5 files from simple Python objects.

    This class's public interface is identical to :class:`~.IndexedMzMLWriter`, with the exception of those
    related to HDF5 compression described below.

    .. note::
        Although :mod:`h5py` can read and write through Python file-like objects, if they are used they
        must be opened in read+write mode to allow the file to be partially re-read during an update to
        an existing block.

    Attributes
    ----------
    h5_compression : str
        A valid HDF5 compressor ID or compression scheme name or :const:`None`. Available compression schemes
        are "gzip"/"zlib", and if :mod:`hdf5plugin` is installed, "blosc", "blosc:lz4", "blosc:zlib", and
        "blosc:zstd". All Blosc-based compressors enable byte shuffling.
    h5_compressor_options : int or tuple
        The options to provide to the compressor designated by :attr:`h5_compressor`. For "gzip", this a single
        integer setting the compression level, while Blosc takes a tuple of integers.
    h5_blocksize : int
        The number of bytes to include in a single HDF5 data block. Smaller blocks improve random access speed
        at the expense of compression efficiency and space. Defaults to 2 ** 20, 1MB.
    buffer_blocks: int
        The number of array blocks to buffer in memory before syncing to disk to reduce the number of
        resize operations. This applies to each array independently. Defaults to 10.
    '''

    buffer_blocks: int
    h5_blocksize: int

    h5_compression: str
    h5_compression_options: Dict

    array_name_cache: Dict
    array_buffers: Dict[str, ArrayBuffer]

    offset_tracker: Counter

    def __init__(self, h5_file, close=False, vocabularies=None, missing_reference_is_error=False,
                 vocabulary_resolver=None, id=None, accession=None, h5_compression=DEFAULT_COMPRESSOR,
                 h5_compression_options=None, h5_blocksize: int=2**20, buffer_blocks: int=10, **kwargs):
        if h5_compression in HDF5_COMPRESSORS:
            key = h5_compression
            h5_compression = HDF5_COMPRESSORS[key]['compression']
            if h5_compression_options is None:
                h5_compression_options = HDF5_COMPRESSORS[key]['compression_opts']
        if h5_compression_options is None:
            h5_compression_options = 4
        self.compressor_name = HDF5_COMPRESSOR_MAGIC_NUMBERS_TO_NAME[h5_compression]
        if not isinstance(h5_file, h5py.File):
            h5_file = h5py.File(h5_file, 'w')
        self.xml_buffer = io.BytesIO()
        outfile = IndexingStream(self.xml_buffer)
        super(MzMLbWriter, self).__init__(
            outfile, close, vocabularies, missing_reference_is_error, vocabulary_resolver,
            id, accession, **kwargs)
        self.index_builder = outfile

        self.h5_file = h5_file
        self.h5_blocksize = h5_blocksize
        self.h5_compression = h5_compression
        self.h5_compression_options = h5_compression_options
        self.buffer_blocks = buffer_blocks

        self.array_name_cache = {}
        self.array_buffers = {}
        self.offset_tracker = Counter()

    def begin(self):
        self.h5_file.attrs['compression'] = self.compressor_name
        return super(MzMLbWriter, self).begin()

    def end(self, type=None, value=None, traceback=None):
        close_ = self._close
        self._close = False
        super(MzMLbWriter, self).end(type, value, traceback)
        xml_bytes = self.xml_buffer.getvalue()
        n = self.create_buffer("mzML", xml_bytes)
        self.h5_file['mzML'].attrs['version'] = "mzMLb 1.0"
        for array, z in self.offset_tracker.items():
            buff = self.array_buffers[array]
            buff.flush()
            if buff.dataset.size != z:
                self.h5_file[array].resize((z, ))

        for index in self.index_builder.indices:
            self._prepare_offset_index(index, index.name, n)

        self._close = close_
        self.h5_file.flush()
        if self._should_close():
            self.close()

    def _generate_array_name(self, array_type, is_non_standard=False, scope='spectrum', dtype=None):
        if not is_non_standard:
            cv_ref, name, accession, term = self.context._resolve_cv_ref(array_type, None, None)
            key = accession.replace(":", "_")
        else:
            key = array_type.replace(" ", "_")
        tag_name = "{scope}_{key}".format(scope=scope, key=key)
        if dtype is not None:
            tag_name += '_' + dtype.__name__
        dset = self.h5_file.create_dataset(
            tag_name, chunks=(self.h5_blocksize, ),
            shape=(self.h5_blocksize, ), dtype=dtype, compression=self.h5_compression,
            compression_opts=self.h5_compression_options, maxshape=(None, ))
        self.array_buffers[tag_name] = ArrayBuffer(dset, dtype, self.h5_blocksize * self.buffer_blocks)
        return tag_name

    def _prepare_array(self, array, encoding=32, compression=COMPRESSION_NONE, array_type=None,
                       default_array_length=None, scope='spectrum'):
        if isinstance(encoding, numbers.Number):
            _encoding = int(encoding)
        else:
            _encoding = encoding
        dtype = encoding_map[_encoding]
        array = np.array(array, dtype=dtype)
        encoded_array = encode_array_direct(
            array, compression=compression, dtype=dtype)

        if default_array_length is not None and len(array) != default_array_length:
            override_length = True
        else:
            override_length = False
        is_non_standard = False
        params = []
        if array_type is not None:
            params.append(array_type)
            if isinstance(array_type, Mapping):
                array_type_ = array_type['name']
            else:
                array_type_ = array_type
            if array_type_ not in ARRAY_TYPES:
                is_non_standard = True
                params.append(NON_STANDARD_ARRAY)
        params.append(compression_map[compression])
        params.append(dtype_to_encoding[dtype])

        if isinstance(array_type, dict):
            if len(array_type) == 1:
                array_name = next(iter(array_type.keys()))
            else:
                array_name = array_type['name']
        else:
            array_name = array_type
        try:
            storage_name = self.array_name_cache[array_name, is_non_standard, scope, dtype]
        except KeyError:
            storage_name = self._generate_array_name(array_name, is_non_standard, scope, dtype)
            self.array_name_cache[array_name, is_non_standard, scope, dtype] = storage_name

        length = len(encoded_array)
        offset = self.offset_tracker[storage_name]

        buff = self.array_buffers[storage_name]
        buff.add(encoded_array)
        self.offset_tracker[storage_name] += length
        return self.ExternalBinaryDataArray(
            external_dataset_name=storage_name,
            offset=offset, array_length=length,
            params=params)

    def _prepare_offset_index(self, index, name, last):
        '''Prepare an offset index.

        Parameters
        ----------
        index : :class:`Iterable` of :class:`~.Offset`
            The offset index records to store
        name : str
            The name of the indexed entity, e.g. "spectrum" or "chromatogram"
        last : int
            The final offset value at the end of the file or list
        '''
        offset_index_key = "mzML_{name}Index".format(name=name)
        offset_index_id_ref = "mzML_{name}Index_idRef".format(name=name)

        id_ref_array = []
        offset_array = []
        for i, o in index:
            id_ref_array.append(i)
            offset_array.append(o.offset)
        id_ref_array.append(b'')
        offset_array.append(last)

        id_ref_array_enc = bytearray(b'\x00'.join(id_ref_array))
        self.h5_file.create_dataset(
            offset_index_key, data=np.array(offset_array), compression=self.h5_compression,
            compression_opts=self.h5_compression_options)
        self.h5_file.create_dataset(
            offset_index_id_ref, data=id_ref_array_enc, compression=self.h5_compression,
            compression_opts=self.h5_compression_options)

    def create_array(self, data, name, last=None, dtype=np.float32, chunks=True):
        '''Store a typed data array as a named dataset in the HDF5 file.

        .. note::
            The array should not be textual unless they've already been translated
            into a byte array with terminal null bytes.

        Parameters
        ----------
        data : :class:`Iterable`
            The data to be stored.
        name : str
            The name to store the dataset by.
        last : object, optional
            A value to associate with the final entry of the array.
        dtype : type
            The type of the entries in the array.
        chunks : bool
            Whether or not to store the dataset in chunks.
        '''
        n = len(data)
        value = np.empty(n + 1, dtype=dtype)
        value[:n] = data
        value[n] = dtype(last) if last is not None else dtype()
        self.h5_file.create_dataset(
            name, data=value, compression=self.h5_compression,
            compression_opts=self.h5_compression_options,
            chunks=min(self.h5_blocksize, n) if chunks else None)

    def create_buffer(self, name, content):
        '''Create a compressed binary buffer with a name and fixed length in the HDF5 file.

        Parameters
        ----------
        name : str
            The name of the HDF5 dataset
        content : bytes-like object
            The data to store. Must be convertable into a :class:`bytearray`, e.g. through the
            buffer interface.

        Returns
        -------
        n : int
            The size of the buffer written
        '''
        n = len(content)
        self.h5_file.create_dataset(
            name, shape=(n, ), chunks=(min(self.h5_blocksize, n), ),
            dtype=np.int8, data=bytearray(content), compression=self.h5_compression,
            compression_opts=self.h5_compression_options)
        return n
