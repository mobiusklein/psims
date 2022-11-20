import io
import json
try:
    from importlib import resources
    _load = resources.open_binary
except ImportError:
    import pkg_resources
    _load = pkg_resources.resource_stream
from gzip import GzipFile


def _use_vendored_psims_obo():
    return GzipFile(fileobj=_load(__name__, "psi-ms.obo.gz"))


def _use_vendored_psimod_obo():
    return GzipFile(fileobj=_load(__name__, "psi-mod.obo.gz"))


def _use_vendored_unit_obo():
    return GzipFile(fileobj=_load(__name__, "unit.obo.gz"))


def _use_vendored_pato_obo():
    return GzipFile(fileobj=_load(__name__, "pato.obo.gz"))


def _use_vendored_unimod_xml():
    return GzipFile(fileobj=_load(__name__, "unimod_tables.xml.gz"))


def _use_vendored_xlmod_obo():
    return GzipFile(fileobj=_load(__name__, "XLMOD.obo.gz"))


def _use_vendored_bto_obo():
    return GzipFile(fileobj=_load(__name__, "bto.obo.gz"))


def _use_vendored_go_obo():
    return GzipFile(fileobj=_load(__name__, "go.obo.gz"))


def _use_vendored_gno_obo():
    return GzipFile(fileobj=_load(__name__, "gno.obo.gz"))


def version_table():
    fh = _load(__name__, "record.json")
    stream = io.TextIOWrapper(fh, 'utf8')
    return json.load(stream)