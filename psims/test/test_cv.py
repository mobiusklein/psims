import os
from psims import load_psims
from psims.controlled_vocabulary import OBOCache, ControlledVocabulary

import shutil
import tempfile

cv = load_psims()


tempdir = tempfile.gettempdir()

cache_path = os.path.join(tempdir, '.obo_cache')

try:
    shutil.rmtree(cache_path)
except OSError:
    pass
obo_cache = OBOCache(cache_path)


def test_version():
    assert cv.version is not None


def test_traversal():
    term = cv['m/z array']
    term2 = cv['MS:1000514']
    assert term == term2
    parent = term.parent()
    parent2 = cv['MS:1000513']
    assert parent == parent2
    assert parent.parent() is None


def test_multiple_parent_terms():
    term = cv['MS:1000528']
    assert len(term.parent()) > 1



def test_cache_resolve_path():
    path = obo_cache.path_for(
        "https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo")
    assert path.endswith("psi-ms.obo")


def test_cache_resolve():
    new_cv_file = obo_cache.resolve("https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo")
    new_cv = ControlledVocabulary.from_obo(new_cv_file)
    assert new_cv.version is not None
    assert new_cv['m/z array'] == cv['m/z array']
