import io
import numbers
from collections import Counter

import numpy as np

import h5py
import hdf5plugin

from ..mzml.binary_encoding import encode_array_direct, encoding_map, compression_map, dtype_to_encoding, COMPRESSION_NONE
from ..mzml.writer import PlainMzMLWriter as _MzMLWriter, NON_STANDARD_ARRAY, ARRAY_TYPES, Mapping
from ..mzml.index import IndexingStream


class MzMLbWriter(_MzMLWriter):
    def __init__(self, h5_file, close=False, vocabularies=None, missing_reference_is_error=False,
                 vocabulary_resolver=None, id=None, accession=None, h5_compression='gzip',
                 h5_compression_options=9, h5_blocksize=2**20, **kwargs):
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

        self.array_name_cache = {}
        self.offset_tracker = Counter()

    def begin(self):
        return super(MzMLbWriter, self).begin()

    def end(self, type, value, traceback):
        close_ = self._close
        self._close = False
        super(MzMLbWriter, self).end(type, value, traceback)
        xml_bytes = self.xml_buffer.getvalue()
        n = len(xml_bytes)
        self.h5_file.create_dataset(
            'mzML', shape=(n, ), chunks=True,
            dtype=np.int8, data=bytearray(xml_bytes), compression=self.h5_compression,
            compression_opts=self.h5_compression_options)

        for array, z in self.offset_tracker.items():
            self.h5_file[array].resize((z, ))

        for index in self.index_builder.indices:
            self._prepare_index(index, index.name, n)

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
        self.h5_file.create_dataset(
            tag_name, chunks=(self.h5_blocksize, ),
            shape=(self.h5_blocksize, ), dtype=dtype, compression=self.h5_compression,
            compression_opts=self.h5_compression_options, maxshape=(None, ))
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

        buff = self.h5_file[storage_name]
        buff[offset:offset + length] = encoded_array
        # z = buff.size
        # if offset + length > z:


        self.offset_tracker[storage_name] += length

        return self.ExternalBinaryDataArray(
            external_dataset_name=storage_name,
            offset=offset, array_length=length,
            params=params)

    def _prepare_index(self, index, name, last):
        offset_index_key = "mzML_{name}Index".format(name=name)
        offset_index_id_ref = "mzML_{name}Index_idRef".format(name=name)

        id_ref_array = []
        offset_array = []
        for i, o in index:
            id_ref_array.append(i.encode('utf8'))
            offset_array.append(o.offset)
        id_ref_array.append(b'')
        offset_array.append(last)

        id_ref_array_enc = bytearray(b'\x00'.join(id_ref_array))
        self.h5_file.create_dataset(
            offset_index_key, data=np.array(offset_array))
        self.h5_file.create_dataset(
            offset_index_id_ref, data=id_ref_array_enc)

