"""Read the RESID Database of Protein Modifications.

RESID describes each modification twice. ``FormulaBlock`` gives the *whole
modified residue* -- for O-phospho-L-threonine, C4H8NO5P at 181.014009 -- while
``CorrectionBlock`` gives the *change* relative to an unmodified parent residue,
+HO3P at 79.966331, naming that parent in its ``uids`` attribute.

Almost every consumer wants the correction. A ProForma tag such as
``[RESID:AA0038]`` denotes the delta, and so do the equivalent ``[UNIMOD:21]``
and ``[MOD:00047]``; a resolver that returned the whole-residue mass would be
wrong by the mass of a threonine and wrong silently.

Note that RESID's weight types are named the opposite way round from the usual
convention: ``physical`` is the monoisotopic weight and ``chemical`` is the
average. For AA0038 those read 79.966331 and 79.98 respectively, matching
PSI-MOD's ``DiffMono`` and ``DiffAvg`` for MOD:00047.

Not every entry yields a single delta, and the exceptions are chemical rather
than clerical. Of RESID 76.00's 621 entries:

- 564 carry exactly one correction.
- 7 are unmodified residues, marked by a correction that names the entry itself
  as its own parent; their delta is zero.
- 30 have several corrections with different masses, because the delta depends
  on which residue was modified. 2-pyrrolidone-5-carboxylic acid (AA0031) is
  -17.026549 when formed from glutamine but -18.010565 from glutamate.
- 20 have no correction at all.

For the 30, :attr:`RESIDModification.monoisotopic_mass` is ``None`` rather than
an arbitrary pick; :attr:`RESIDModification.corrections` carries the
alternatives along with the parent each applies to, so a caller that knows the
parent residue can choose correctly.
"""

import re
import warnings

from collections import Counter
from urllib.request import urlopen

from lxml import etree

try:
    has_pyteomics = True
    from pyteomics.mass.mass import Composition
    CompositionType = Composition
except ImportError:
    has_pyteomics = False
    CompositionType = Counter

from psims.utils import KeyToAttrProxy
from .entity import Entity


#: RESID is served over HTTPS by PIR. The database was last released in 2018
#: (release 76.00) and is no longer updated.
RESID_SOURCE_URL = "https://ftp.proteininformationresource.org/pir_databases/other_databases/resid/RESIDUES.XML"


def fetch(source_url=None):
    """Download and parse the RESID XML document.

    Parameters
    ----------
    source_url : str, optional
        Where to read RESID from. Defaults to :data:`RESID_SOURCE_URL`.

    Returns
    -------
    :class:`lxml.etree._Element`
    """
    if source_url is None:
        source_url = RESID_SOURCE_URL
    uri = urlopen(source_url)
    return etree.fromstring(uri.read())


def parse(tree=None):
    """Convert a RESID XML document into modification objects.

    Entries whose mass cannot be interpreted unambiguously are skipped, which
    is how the two placeholder entries covering "L-aspartic acid or
    L-asparagine" and its glutamic counterpart are excluded -- they carry two
    formulae apiece and could not be a single modification under any scheme.

    Returns
    -------
    mods : list of :class:`RESIDModification`
    attribs : dict
    """
    if tree is None:
        tree = fetch()
    elif hasattr(tree, 'read'):
        # A file-like object, as the cache hands back.
        tree = etree.parse(tree).getroot()
    entries = tree.findall("./Entry")
    mods = []
    for entry in entries:
        try:
            mods.append(RESIDModification.from_xml(entry))
        except RESIDAmbiguousModificationError:
            continue
    attribs = {}
    attribs['version'] = tree.attrib['release']
    attribs['name'] = tree.attrib['id']
    return mods, attribs


class RESIDAmbiguousModificationError(ValueError):
    """Raised when an entry does not describe one interpretable mass."""


class RESIDCorrection(object):
    """One mass change RESID lists for an entry, and the parent it applies to.

    Attributes
    ----------
    parents : list of str
        RESID identifiers of the unmodified residues this correction converts
        from. Empty when the entry does not say.
    monoisotopic_mass : float or None
        The delta, from ``Weight[@type='physical']``.
    average_mass : float or None
        The delta, from ``Weight[@type='chemical']``.
    composition : :class:`~pyteomics.mass.Composition` or :class:`~collections.Counter`
        Elemental change, which may contain negative counts.
    """

    def __init__(self, parents, monoisotopic_mass, average_mass, composition):
        self.parents = parents
        self.monoisotopic_mass = monoisotopic_mass
        self.average_mass = average_mass
        self.composition = composition

    def __repr__(self):
        return "{self.__class__.__name__}({self.parents}, {self.monoisotopic_mass})".format(self=self)


class RESIDModification(object):
    """A single RESID entry.

    The mass-bearing attributes describe the *modification*, so that they mean
    the same thing as their counterparts in UNIMOD and PSI-MOD. The whole
    modified residue remains available as :attr:`residue_monoisotopic_mass` and
    :attr:`residue_composition`.
    """

    def __init__(self, id, name, alternative_names, residue_monoisotopic_mass,
                 residue_composition, corrections=None, is_unmodified_residue=False):
        self.id = id
        self.name = name
        self.alternative_names = alternative_names
        self.residue_monoisotopic_mass = residue_monoisotopic_mass
        self.residue_composition = residue_composition
        self.corrections = corrections or []
        self.is_unmodified_residue = is_unmodified_residue

    def __repr__(self):
        template = ("{self.__class__.__name__}({self.id!r}, {self.name!r}, "
                    "{self.alternative_names}, {self.monoisotopic_mass}, "
                    "{self.composition})")
        return template.format(self=self)

    @property
    def _unique_correction(self):
        """The one correction that applies, or ``None`` if that is not defined.

        ``None`` covers two cases a caller must not conflate with zero: an entry
        with no correction at all, and an entry whose delta depends on which
        residue was modified.
        """
        distinct = {c.monoisotopic_mass for c in self.corrections}
        if len(distinct) == 1:
            return self.corrections[0]
        return None

    @property
    def monoisotopic_mass(self):
        """Monoisotopic mass change, or ``None`` when RESID does not fix one."""
        correction = self._unique_correction
        return correction.monoisotopic_mass if correction is not None else None

    @property
    def average_mass(self):
        """Average mass change, or ``None`` when RESID does not fix one."""
        correction = self._unique_correction
        return correction.average_mass if correction is not None else None

    @property
    def composition(self):
        """Elemental change, or ``None`` when RESID does not fix one."""
        correction = self._unique_correction
        return correction.composition if correction is not None else None

    @property
    def mass(self):
        """Alias of :attr:`monoisotopic_mass`."""
        return self.monoisotopic_mass

    @classmethod
    def _parse_mass(cls, text):
        if "," in text:
            raise RESIDAmbiguousModificationError(
                "Multiple masses found %r" % text)
        tokens = text.split(" ")
        masses = []
        for tok in tokens:
            try:
                masses.append(float(tok))
            except ValueError:
                if tok == "+":
                    continue
                else:
                    raise
        if len(masses) > 1:
            raise RESIDAmbiguousModificationError(
                "Multiple masses found %r" % text)
        return masses

    @classmethod
    def _parse_formula(self, formula):
        composition = CompositionType()
        # Counts may be negative: a correction that removes water reads
        # "C 0 H -2 N 0 O -1".
        for key, val in re.findall(r"([A-Za-z]\S*)\s(-?\d+)", formula):
            composition[key] += int(val)
        return composition

    @classmethod
    def _parse_weight(cls, block, type):
        node = block.find("Weight[@type='%s']" % type)
        if node is None or not node.text:
            return None
        values = cls._parse_mass(node.text)
        return values[0] if values else None

    @classmethod
    def _parse_corrections(cls, tag, id):
        """Read every ``CorrectionBlock``, and note self-referential ones.

        A block whose ``uids`` names the entry itself marks an unmodified
        residue: RESID records L-alanine as convertible from alanine with a
        zero correction. It is kept as an ordinary correction, since an entry
        may list conversions from other residues too -- L-alanine is also
        reachable from L-aspartate at -43.989829 -- in which case there is no
        single delta to report.
        """
        corrections = []
        is_unmodified_residue = False
        for block in tag.findall("CorrectionBlock"):
            parents = (block.attrib.get("uids") or "").split()
            if id in parents:
                # RESID records an unmodified residue as convertible from
                # itself with a zero correction. That is a real correction and
                # is kept, but it is flagged, because an entry that also lists
                # conversions from *other* residues then has no single delta.
                is_unmodified_residue = True
            formula = block.find("Formula")
            try:
                correction = RESIDCorrection(
                    parents,
                    cls._parse_weight(block, "physical"),
                    cls._parse_weight(block, "chemical"),
                    cls._parse_formula(formula.text) if formula is not None and formula.text else None)
            except RESIDAmbiguousModificationError:
                # An unreadable correction should not discard the entry; the
                # remaining corrections and the whole-residue mass are intact.
                warnings.warn("Skipping an uninterpretable correction for %s" % id)
                continue
            corrections.append(correction)
        return corrections, is_unmodified_residue

    @classmethod
    def from_xml(cls, tag):
        """Build a modification from a RESID ``Entry`` element."""
        id = tag.attrib['id']
        name = tag.find(".//Name").text
        alternative_names = [t.text for t in tag.findall(".//AlternateName")]
        formula = tag.find(".//FormulaBlock/Formula").text.replace("+", "")
        mass = cls._parse_mass(tag.find(".//FormulaBlock/Weight[@type='physical']").text)[0]
        composition = cls._parse_formula(formula)
        corrections, is_unmodified_residue = cls._parse_corrections(tag, id)
        return cls(id, name, alternative_names, mass, composition, corrections,
                   is_unmodified_residue)


class RESIDEntity(Entity):
    """A RESID modification wrapped for use as a controlled vocabulary term."""

    def is_of_type(self, tp):
        try:
            if tp.startswith('RESID'):
                return True
            return False
        except AttributeError:
            if isinstance(tp, RESIDEntity):
                return True

    @classmethod
    def converter(cls, modification, vocabulary):
        """Flatten a :class:`RESIDModification` into an :class:`~.Entity`."""
        data = dict(KeyToAttrProxy(modification))
        data['id'] = 'RESID:%s' % modification.id
        data['name'] = modification.name
        data['monoisotopic_mass'] = modification.monoisotopic_mass
        data['average_mass'] = modification.average_mass
        data['composition'] = modification.composition
        data['_object'] = modification
        return cls(vocabulary, **data)


class RESID(object):
    """The RESID database, indexed by identifier and by name."""

    name = "RESID"
    default_version = '1.0'

    def __init__(self, xml_document=None):
        self._entries, self.metadata = parse(xml_document)
        self.version = self.metadata.get('version')
        self.terms = {}
        for entry in self._entries:
            self.terms[entry.id] = entry
            self.terms['RESID:%s' % entry.id] = entry
            self.terms[entry.name] = entry
            for name in entry.alternative_names:
                self.terms[name] = entry

    def __getitem__(self, key):
        return self.terms[key]

    def __contains__(self, key):
        return key in self.terms

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)
