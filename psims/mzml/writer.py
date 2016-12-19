from contextlib import contextmanager
import numbers

from lxml import etree
import numpy as np

from psims.xml import XMLWriterMixin

from .components import (
    ComponentDispatcher, common_units, element, _element,
    default_cv_list, MzML)

from .binary_encoding import (
    encode_array, COMPRESSION_NONE, COMPRESSION_ZLIB,
    encoding_map)

from utils import ensure_iterable, basestring

_t = tuple()


MZ_ARRAY = 'm/z array'
INTENSITY_ARRAY = 'intensity array'
CHARGE_ARRAY = 'charge array'

ARRAY_TYPES = (MZ_ARRAY, INTENSITY_ARRAY, CHARGE_ARRAY)

compression_map = {
    'zlib': "zlib compression",
    'none': 'no compression',
    None: 'no compression'
}


class DocumentSection(ComponentDispatcher, XMLWriterMixin):

    def __init__(self, section, writer, parent_context):
        super(DocumentSection, self).__init__(parent_context)
        self.section = section
        self.writer = writer

    def __enter__(self):
        self.toplevel = element(self.writer, self.section)
        self.toplevel.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.toplevel.__exit__(exc_type, exc_value, traceback)
        self.writer.flush()


# ----------------------
# Order of Instantiation
# todo


class MzMLWriter(ComponentDispatcher, XMLWriterMixin):
    """
    A high level API for generating mzML XML files from simple Python objects.

    This class depends heavily on lxml's incremental file writing API which in turn
    depends heavily on context managers. Almost all logic is handled inside a context
    manager and in the context of a particular document. Since all operations assume
    that they have access to a universal identity map for each element in the document,
    that map is centralized in this instance.

    MzMLWriter inherits from :class:`.ComponentDispatcher`, giving it a :attr:`context`
    attribute and access to all `Component` objects pre-bound to that context with attribute-access
    notation.

    Attributes
    ----------
    outfile : file
        The open, writable file descriptor which XML will be written to.
    xmlfile : lxml.etree.xmlfile
        The incremental XML file wrapper which organizes file writes onto :attr:`outfile`.
        Kept to control context.
    writer : lxml.etree._IncrementalFileWriter
        The incremental XML writer produced by :attr:`xmlfile`. Kept to control context.
    toplevel : lxml.etree._FileWriterElement
        The top level incremental xml writer element which will be closed at the end
        of file generation. Kept to control context
    context : :class:`.DocumentContext`
    """

    toplevel_tag = MzML

    def __init__(self, outfile, vocabularies=None, **kwargs):
        if vocabularies is None:
            vocabularies = []
        vocabularies = default_cv_list + list(vocabularies)
        super(MzMLWriter, self).__init__(vocabularies=vocabularies)
        self.outfile = outfile
        self.xmlfile = etree.xmlfile(outfile, **kwargs)
        self.writer = None
        self.toplevel = None
        self.spectrum_count = 0

    def _begin(self):
        self.outfile.write('<?xml version="1.0" encoding="utf-8"?>\n')
        self.writer = self.xmlfile.__enter__()

    def __enter__(self):
        self._begin()
        self.toplevel = element(self.writer, self.toplevel_tag())
        self.toplevel.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.toplevel.__exit__(exc_type, exc_value, traceback)
        self.writer.flush()
        self.xmlfile.__exit__(exc_type, exc_value, traceback)
        self.outfile.close()

    def close(self):
        self.outfile.close()

    def controlled_vocabularies(self, vocabularies=None):
        if vocabularies is None:
            vocabularies = []
        self.vocabularies.extend(vocabularies)
        cvlist = self.CVList(self.vocabularies)
        cvlist.write(self.writer)

    def software_list(self, software_list):
        n = len(software_list)
        if n:
            software_list = [self.Software(**sw) for sw in software_list]
        self.SoftwareList(software_list).write(self)

    def write_spectrum(self, mz_array, intensity_array, charge_array=None, id=None,
                       polarity='positive scan', centroided=True, precursor_information=None,
                       scan_start_time=None,
                       params=None, compression=COMPRESSION_ZLIB, encoding=32):
        if params is None:
            params = []
        else:
            params = list(params)

        if isinstance(polarity, int):
            if polarity > 0:
                polarity = 'positive scan'
            else:
                polarity = 'negative scan'
        elif 'positive' in polarity:
            polarity = 'positive scan'
        else:
            polarity = 'negative scan'

        if centroided:
            peak_mode = "centroid spectrum"
        else:
            peak_mode = 'profile spectrum'
        params.append(peak_mode)

        array_list = []

        mz_array_tag = self._prepare_array(
            mz_array, encoding=encoding, compression=compression, array_type=MZ_ARRAY)
        array_list.append(mz_array_tag)

        intensity_array_tag = self._prepare_array(
            intensity_array, encoding=encoding, compression=compression, array_type=INTENSITY_ARRAY)
        array_list.append(intensity_array_tag)

        if charge_array is not None:
            charge_array_tag = self._prepare_array(
                charge_array, encoding=encoding, compression=compression, array_type=CHARGE_ARRAY)
            array_list.append(charge_array_tag)
        array_list_tag = self.BinaryDataArrayList(array_list)

        if polarity not in params:
            params.append(polarity)

        if precursor_information is not None:
            precursor_list = self._prepare_precursor_information(**precursor_information)
        else:
            precursor_list = None

        scan_params = []
        if scan_start_time is not None:
            if isinstance(scan_start_time, numbers.Number):
                scan_params.append({"name": "scan start time",
                                    "value": scan_start_time,
                                    "unitName": 'minute'})
            else:
                scan_params.append(scan_start_time)

        scan = self.Scan(params=scan_params)
        scan_list = self.ScanList([scan])

        index = self.spectrum_count
        self.spectrum_count += 1
        spectrum = self.Spectrum(
            index, array_list_tag, scan_list=scan_list, params=params, id=id,
            default_array_length=len(mz_array),
            precursor_list=precursor_list)
        spectrum.write(self.writer)

    def _prepare_array(self, numeric, encoding=32, compression=COMPRESSION_ZLIB, array_type=None):
        _encoding = int(encoding)
        array = np.array(numeric)
        encoding = encoding_map[_encoding]
        encoded_binary = encode_array(
            array, compression=compression, dtype=encoding)
        binary = self.Binary(encoded_binary)
        params = []
        if array_type is not None:
            params.append(array_type)
        params.append(compression_map[compression])
        params.append("%d-bit float" % _encoding)
        encoded_length = len(encoded_binary)
        return self.BinaryDataArray(binary, encoded_length, params=params)

    def _prepare_precursor_information(self, mz, intensity, charge, scan_id):
        ion = self.SelectedIon(mz, intensity, charge)
        ion_list = self.SelectedIonList([ion])
        precursor = self.Precursor(
            ion_list, activation=None, isolation_window=None, spectrum_reference=scan_id)
        precursor_list = self.PrecursorList([precursor])
        return precursor_list
