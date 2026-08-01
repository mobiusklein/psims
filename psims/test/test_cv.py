import os
from functools import lru_cache

from psims import load_psims
from psims.controlled_vocabulary import OBOCache, ControlledVocabulary
from psims.controlled_vocabulary.controlled_vocabulary import load_psimod, load_resid

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


@lru_cache(maxsize=1)
def _resid():
    # Loaded on demand rather than at import: RESID is not vendored, so this
    # reaches the network, and the rest of the suite should not pay for it.
    return load_resid()


def test_resid_reports_the_modification_mass_not_the_residue():
    # RESID describes both the whole modified residue and the change relative
    # to an unmodified parent. A ProForma tag means the change, so that is what
    # the mass attributes carry; reading FormulaBlock instead would return
    # 181.014009 here, wrong by the mass of a threonine.
    cv = _resid()
    phospho_threonine = cv['AA0038']
    assert abs(phospho_threonine.monoisotopic_mass - 79.966331) < 1e-6
    assert abs(phospho_threonine.average_mass - 79.98) < 1e-6
    assert abs(phospho_threonine.residue_monoisotopic_mass - 181.014009) < 1e-6
    assert dict(phospho_threonine.composition) == {'H': 1, 'O': 3, 'P': 1}


def test_resid_agrees_with_psi_mod():
    # PSI-MOD publishes DiffMono for the same chemistry, derived independently.
    cv = _resid()
    psimod = load_psimod()
    for resid_id, psimod_id in [('AA0038', 'MOD:00047'), ('AA0055', 'MOD:00064'),
                                ('AA0074', 'MOD:00083')]:
        assert abs(cv[resid_id].monoisotopic_mass - float(psimod[psimod_id].DiffMono)) < 1e-4


def test_resid_lookup_by_name_and_accession():
    cv = _resid()
    assert cv['O-phospho-L-threonine'].id == 'AA0038'
    assert cv['RESID:AA0038'].id == 'AA0038'


def test_resid_does_not_invent_a_mass_it_does_not_have():
    # 2-pyrrolidone-5-carboxylic acid loses ammonia when formed from glutamine
    # and water when formed from glutamate, so there is no single delta. Both
    # are offered, with the parent each applies to, rather than one being
    # picked arbitrarily.
    cv = _resid()
    pyroglutamate = cv['AA0031']
    assert pyroglutamate.monoisotopic_mass is None
    by_parent = {c.parents[0]: c.monoisotopic_mass for c in pyroglutamate.corrections}
    assert abs(by_parent['AA0006'] - -18.010565) < 1e-6
    assert abs(by_parent['AA0007'] - -17.026549) < 1e-6


def test_resid_keeps_the_self_referential_correction():
    # RESID records L-alanine as convertible from alanine with a zero
    # correction, and also from L-aspartate at -43.989829, which is what
    # PSI-MOD's MOD:00869 refers to. Reading the self-reference as "this entry
    # is unmodified, delta zero" would discard that second conversion, so it is
    # kept as an ordinary correction and the entry reports no single delta.
    cv = _resid()
    alanine = cv['AA0001']
    assert alanine.is_unmodified_residue
    assert alanine.monoisotopic_mass is None
    by_mass = sorted(c.monoisotopic_mass for c in alanine.corrections)
    assert abs(by_mass[0] - -43.989829) < 1e-6
    assert by_mass[1] == 0.0
