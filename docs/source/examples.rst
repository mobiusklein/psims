Usage Examples
--------------

Writing mzML
============

    In this example, we'll walk through the steps involved in writing an mzML file containing simulated data.

    Writing an mzML file with :mod:`psims` is done using the :class:`~.MzMLWriter` class.

    .. code:: python

        from psims.mzml import MzMLWriter

    To begin, you create the writer with a file path, or a previously created file-like object:

    .. code:: python

        writer = MzMLWriter("path/to/write.mzML")

    Before any content can be written out, the writer must start the document, which can be done by either
    using it as a context manager, or by calling it's :meth:`~.MzMLWriter.begin` method.

    .. code:: python

        with writer:
            writer.controlled_vocabularies()
            ...

    The above example uses the context manager syntax, and immediately writes the controlled vocabulary
    list to the document. This starts the standard-compliance state-machine, which checks to make sure that
    a document proceeds through each section in the expected order, without skipping required sections. The
    remainder of these code samples will take place within this context manager.

    The next step is to describe the contents of the file to be written. This includes both provenance
    information (where the data came from) and classification of the types of spectra contained (MS1 and/or
    MSn spectra, centroid vs. profile spectra). In this example, we'll generate some data *de novo*, and
    so won't have any ``<sourceFile>`` elements.

    .. code:: python

        writer.file_description([ # the list of file contents terms
            "MS1 spectrum",
            "MSn spectrum",
            "centroid spectrum"
        ])


    If a ``<sourceFile>`` is needed, it can be built using

    .. code:: python

        sf = writer.SourceFile("file://path/to/the", "file_name.ext", id="RAW1", params=params)
        # If you need to checksum a local file
        sf.params.append(sf.checksum('sha-1'))

    The next required list is ``<softwareList>``. Replace the names here with your own tools if needed:

    .. code:: python

        writer.software_list([
            {"id": "psims-writer",
             "version": "0.1.2",
             "params": [
                "python-psims",
            ]}
        ])


    The instrument configuration list is a bit more involved to specify. For example, an ESI FT-ICR
    system would be described by:

    .. code:: python

        source = writer.Source(1, ["electrospray ionization", "electrospray inlet"])
        analyzer = writer.Analyzer(2, [
                ""fourier transform ion cyclotron resonance mass spectrometer"
            ])
        detector = writer.Detector(3, ["inductive detector"])
        config = writer.InstrumentConfiguration(id="IC1", component_list=[source, analyzer, detector],
                                                params=["LTQ-FT"])
        writer.instrument_configuration_list([config])

    Multiple configurations may be specified.

    The ``<dataProcessing>`` instructions can be as intricate as needed, as in this case:

    .. code:: python

        methods = []

        methods.append(
            writer.ProcessingMethod(
                order=1, sofware_reference="psims-writer", params=[
                    "Gaussian smoothing",
                    "median baseline reduction",
                    "MS:1000035", # peak picking
                    "Conversion to mzML"
                ]))
        processing = writer.DataProcessing(methods, id='DP1')
        writer.data_processing_list([processing])


    Now, we're nearly ready to start writing spectra. To start, we open the run and spectrum list:

    .. code:: python

        import numpy as np

        with writer.run(id=1, instrument_configuration='IC1'):
            # we will write 3,000 spectra
            with writer.spectrum_list(count=1e3):
                ...

    We write all spectra within the inner context manager of the spectrum list, or instead of
    using the context manager notation, call the :meth:`~.XMLDocumentWriter.begin` and
    :meth:`~.XMLDocumentWriter.end` methods.

    A spectrum is a collection of many complex details. We'll use :title-reference:`NumPy` arrays
    to represent the data arrays. This file contains centroided spectra as previously specified in
    the file description.

    We'll assume there's a function that generates a centroided spectrum, called ``get_next_arrays``
    to produce those arrays.

    .. code:: python
        
        i = 0
        while i < 1e3:
            i += 1
            ms1_mzs, ms1_intensities = get_next_arrays()
            ms1_spectrum_id = "index=%d" % i
            scan_time = 0.23 * i

            writer.write_spectrum(
                ms1_mzs, ms1_intensities, id=ms1_spectrum_id, centroided=True,
                scan_start_time=scan_time, scan_window_list=[(0, 2000.0)],
                params=[{"ms level": 1}, {"total ion current": ms1_intensities.sum()}])

            for j in range(3):
                i += 1
                msn_mzs, msn_intensities = get_next_arrays()
                msn_spectrum_id = "index=%d" % i
                scan_time = 0.23 * i

                k = np.random.randint(len(ms1_mzs))
                precursor_info = {
                    "mz": ms1_mzs[k], 'intensity': ms1_intensities[k],
                    "spectrum_reference": ms1_spectrum_id,
                    "activation": ["HCD", {"collision energy": 25.0}],
                    "isolation_window": (1.0, ms1_mzs[k], 1.0)
                }


                writer.write_spectrum(
                    msn_mzs, msn_intensities, id=msn_spectrum_id, centroided=True,
                    scan_start_time=scan_time, scan_window_list=[(0, 2000.0)],
                    precursor_information=precursor_info,
                    params=[{"ms level": 2}, {"total ion current": msn_intensities.sum()}])

    Similar code can be used for writing chromatograms, see :meth:`~.MzMLWriter.write_chromatogram`.

    Once the document is finished, we leave the top-level context manager, and we can index the file
    using :meth:`~.MzMLWriter.format` method.
