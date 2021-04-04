mzML Transformation Stream
--------------------------

Given a file stream from an mzML file, :class:`psims.transform.mzml.MzMLTransformer`
will copy it to a new stream, applying a user provided transformation function to modify
each spectrum en-route. It can also optionally sort the spectra by "scan start time".


.. automodule:: psims.transform.mzml

    .. autoclass:: MzMLTransformer
        :members:
        :inherited-members:

    .. autoclass:: MzMLToMzMLb