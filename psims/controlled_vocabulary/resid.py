import ftplib
import warnings
import re
import io

from collections import Counter
try:
    from urllib2 import urlopen, URLError, Request
except ImportError:
    from urllib.request import urlopen, URLError, Request

from lxml import etree

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

from psims.utils import KeyToAttrProxy
from .entity import Entity


def fetch():
    # buffer = io.BytesIO()
    # server = ftplib.FTP("ftp.proteininformationresource.org")
    # server.login()
    # server.cwd("pir_databases/other_databases/resid/")
    # server.retrbinary("RETR RESIDUES.XML", buffer.write)
    # return etree.fromstring(buffer.getvalue())
    uri = urlopen(
        "ftp://ftp.proteininformationresource.org/pir_databases/other_databases/resid/RESIDUES.XML")
    return etree.fromstring(uri.read())


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
    attribs = {}
    attribs['version'] = tree.attrib['release']
    attribs['name'] = tree.attrib['id']
    return mods, attribs


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
    def _parse_formula(self, formula):
        composition = CompositionType()
        for key, val in re.findall(r"(\S+)\s(\d+)", formula):
            composition[key] += int(val)
        return composition

    @classmethod
    def from_xml(cls, tag):
        id = tag.attrib['id']
        name = tag.find(".//Name").text
        alternative_names = [t.text for t in tag.findall(".//AlternateName")]
        formula = tag.find(".//FormulaBlock/Formula").text.replace("+", "")
        mass = cls._parse_mass(tag.find(".//FormulaBlock/Weight[@type='physical']").text)[0]
        composition = cls._parse_formula(formula)
        return cls(id, name, alternative_names, mass, composition)


class RESIDEntity(Entity):
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
        data = dict(KeyToAttrProxy(modification))
        data['id'] = 'RESID:%s' % modification.id
        data['name'] = modification.name
        data['_object'] = modification
        return cls(vocabulary, **data)


class RESID(object):
    name = "RESID"
    default_version = '1.0'

    def __init__(self, xml_document=None):
        self._entries, self.metadata = parse(xml_document)
        self.terms = {}
        for entry in self._entries:
            self.terms[entry.id] = entry
            self.terms[entry.name] = entry
            for name in entry.alternative_names:
                self.terms[name] = entry

    def __getitem__(self, key):
        return self.terms[key]


