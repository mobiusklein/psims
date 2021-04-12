Writing mzML Documents
----------------------


.. automodule:: psims.mzml.writer

.. autoclass:: IndexedMzMLWriter
    :members:
    :inherited-members:
    :exclude-members: toplevel_tag
    :special-members: __enter__, __exit__, __getattr__

.. data:: compression_map
    The compression methods available:

    .. exec::

        from psims.mzml.binary_encoding import compression_map
        from rst_table import as_rest_table

        rows = [("Name", "Compression Scheme")]
        for key, value in sorted(compression_map.items()):
            rows.append((repr(key), value))

        print(as_rest_table(rows))
