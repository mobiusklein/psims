import base64
import zlib

import numpy as np


COMPRESSION_NONE = 'none'
COMPRESSION_ZLIB = 'zlib'


encoding_map = {
    32: np.float32,
    64: np.float64,
    '64-bit integer': np.int64,
    'MS:1000522': np.int64,
    'MS:1000519': np.int32,
    '32-bit integer': np.int32,
    'MS:1000520': np.float16,
    '16-bit float': np.float16,
    'MS:1000521': np.float32,
    '32-bit float': np.float32,
    'MS:1000523': np.float64,
    '64-bit float': np.float64,
    'MS:1001479': np.bytes_,
    'null-terminated ASCII string': np.bytes_,
    float: np.float64,
    int: np.int32
}

for dtype in list(encoding_map.values()):
    encoding_map[dtype] = dtype


def encode_array(array, compression=COMPRESSION_NONE, dtype=np.float32):
    bytestring = np.asanyarray(array).astype(dtype).tobytes()
    if compression == COMPRESSION_NONE:
        bytestring = bytestring
    elif compression == COMPRESSION_ZLIB:
        bytestring = zlib.compress(bytestring)
    else:
        raise ValueError("Unknown compression: %s" % compression)
    encoded_string = base64.standard_b64encode(bytestring)
    return encoded_string


def decode_array(bytestring, compression=COMPRESSION_NONE, dtype=np.float32):
    try:
        decoded_string = bytestring.encode("ascii")
    except AttributeError:
        decoded_string = bytestring
    decoded_string = base64.decodestring(decoded_string)
    if compression == COMPRESSION_NONE:
        decoded_string = decoded_string
    elif compression == COMPRESSION_ZLIB:
        decoded_string = zlib.decompress(decoded_string)
    else:
        raise ValueError("Unknown compression: %s" % compression)
    array = np.fromstring(decoded_string, dtype=dtype)
    return array
