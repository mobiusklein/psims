mzML Transformation Stream
--------------------------

Given a file stream from an mzML file, :class:`psims.transform.mzml.MzMLTransformer`
will copy it to a new stream, applying a user provided transformation function to modify
each spectrum en-route. It can also optionally sort the spectra by "scan start time".


.. automodule:: psims.transform.mzml

    .. autoclass:: MzMLTransformer
        :members:
        :inherited-members:

MzMLb Translation
=================
:mod:`psims` can also translate mzML into mzMLb automatically using a variant of :class:`MzMLtransformer` called
:class:`MzMLToMzMLb`. It works identically to :class:`MzMLTransformer`, though it can accept additional arguments
to control the HDF5 block size and compression.

.. autoclass:: MzMLToMzMLb

.. code-block:: python
    :linenos:

    #!/usr/bin/env python
    import sys
    from psims.transform.mzml import MzMLToMzMLb

    inpath = sys.argv[1]
    outpath = sys.argv[2]
    try:
        compression = sys.argv[3]
    except IndexError:
        compression = "blosc"

    with open(inpath, 'rb') as instream:
        MzMLToMzMLb(instream, outpath, h5_compression=compression).write()