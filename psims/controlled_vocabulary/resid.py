import ftplib
import warnings
import re
import io

from collections import Counter

from lxml import etree
from sqlalchemy.orm import composite

try:
    has_pyteomics = True
    from pyteomics.mass.mass import Composition, _make_isotope_string
    CompositionType = Composition
except ImportError:
    has_pyteomics = False
    CompositionType = Counter

    def _make_isotope_string(element, isotope):
        if isotope:
            return "%s[%d]" % (element, isotope)
        else:
            return str(element)


def fetch():
    buffer = io.BytesIO()
    server = ftplib.FTP("ftp.proteininformationresource.org")
    server.login()
    server.cwd("pir_databases/other_databases/resid/")
    server.retrbinary("RETR RESIDUES.XML", buffer.write)
    return etree.fromstring(buffer.getvalue())


def parse(tree=None):
    if tree is None:
        tree = fetch()
    entries = tree.findall("./Entry")
    mods = []
    for entry in entries:
        try:
            mods.append(RESIDModification.from_xml(entry))
        except RESIDAmbiguousModificationError:
            continue
    return mods


class RESIDAmbiguousModificationError(ValueError):
    pass


class RESIDModification(object):
    def __init__(self, id, name, alternative_names, mass, composition):
        self.id = id
        self.name = name
        self.alternative_names = alternative_names
        self.mass = mass
        self.composition = composition

    def __repr__(self):
        template = ("{self.__class__.__name__}({self.id!r}, {self.name!r}, "
                    "{self.alternative_names}, {self.mass}, {self.composition})")
        return template.format(self=self)

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
    def from_xml(cls, tag):
        id = tag.attrib['id']
        name = tag.find(".//Name").text
        alternative_names = [t.text for t in tag.findall(".//AlternateName")]
        formula = tag.find(".//FormulaBlock/Formula").text.replace(" ", '').replace("+", "")
        mass = cls._parse_mass(tag.find(".//FormulaBlock/Weight[@type='chemical']").text)
        composition = Composition(formula)
        return cls(id, name, alternative_names, mass, composition)
