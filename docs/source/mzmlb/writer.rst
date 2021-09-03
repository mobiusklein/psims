Writing mzMLb Documents
-----------------------

.. automodule:: psims.mzmlb.writer

    .. autoclass:: MzMLbWriter
        :members:
        :exclude-members: toplevel_tag, begin, end

mzMLb Compression Methods
=========================
mzMLb can use any compression method that HDF5 can use. By default,
only the "zlib" (or "gzip") compressors are included in :mod:`h5py`,
which will be used by default. If :mod:`hdf5plugin` is installed,
several additional compression options are available as well.

.. note:: Default Compressor

    If :mod:`hdf5plugin` is installed, the default compressor will be :obj:`"blosc"`,
    otherwise, it will be :obj:`"gzip"`.

.. exec::

    from psims.mzmlb.writer import (HDF5_COMPRESSORS, HDF5_COMPRESSOR_MAGIC_NUMBERS_TO_NAME)
    from rst_table import as_rest_table

    rows = [("Compressor Name", "Defaults Options", "Available")]
    for key, value in sorted(HDF5_COMPRESSORS.items()):
        rows.append((
            "**%s**" % (key, ),
            repr(value["compression_opts"]),
            "Required :mod:`hdf5plugin`" if key not in ("gzip", "zlib") else "Built-In to :mod:`h5py`"
            ))

    print(as_rest_table(rows))