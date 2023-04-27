import warnings
import re

from collections import Counter

from lxml import etree


try:
    from sqlalchemy.orm import declarative_base, DeclarativeMeta
except ImportError: # sqlalchemy 1/2 compat
    from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

from sqlalchemy.orm import relationship, backref, object_session
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import (Numeric, Unicode,
                        Column, Integer, ForeignKey,
                        UnicodeText, Boolean, event)
from sqlalchemy import exc as sa_exc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from six import string_types as basestring

from psims.utils import KeyToAttrProxy
from .entity import Entity


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


model_registry = set()

class SubclassRegisteringDeclarativeMeta(DeclarativeMeta):
    def __new__(cls, name, parents, attrs):
        new_type = super(SubclassRegisteringDeclarativeMeta,
                         cls).__new__(cls, name, parents, attrs)
        model_registry.add(new_type)
        return new_type


Base = declarative_base(metaclass=SubclassRegisteringDeclarativeMeta)

_unimod_xml_download_url = "http://www.unimod.org/xml/unimod_tables.xml"


def simple_repr(self):  # pragma: no cover
    template = "{self.__class__.__name__}({d})"
    items = [(k, v) for k, v in self.__dict__.items() if not k.startswith("_")]
    parts = []
    for key, value in items:
        if key.endswith("_id"):
            try:
                value = getattr(self, key[:-3])
                key = key[:-3]
            except AttributeError:
                pass
        parts.append("%s=%r" % (key, value))

    return template.format(self=self, d=', '.join(parts))


Base.__repr__ = simple_repr


def attr_repr(attr_name):  # pragma: no cover
    def __repr__(self):
        return str(getattr(self, attr_name))

    def applier(cls):
        cls.__repr__ = __repr__
        return cls

    return applier


def remove_namespace(doc, namespace):
    """Remove namespace in the passed document in place."""
    ns = u'{%s}' % namespace
    nsl = len(ns)
    for elem in doc.getiterator():
        if elem.tag.startswith(ns):
            elem.tag = elem.tag[nsl:]


def preprocess_xml(doc_path):
    '''
    Parse and drop namespaces from an XML document.

    Parameters
    ----------
    doc_path: str

    Returns
    -------
    etree.ElementTree
    '''
    tree = etree.parse(doc_path)
    root = tree.getroot()
    for ns in root.nsmap.values():
        remove_namespace(tree, ns)
    return tree


def _formula_parser(formula, session):
    '''
    Parse a unimod formula composed of elements,
    isotopes, and other bricks.

    In order to look up a Brick's composition, this
    function must have access to a session.

    Parameters
    ----------
    formula: str
        A Unimod formula of the form `A(n) B(m)...`
        where A, B, ... are element names or bricks and
        (n), (m)... are parenthesized possibly signed integers or
        omitted in which case they are interpreted as 1
    session: Session
        An active SQLAlchemy session for looking up bricks in the database

    Returns
    -------
    CompositionType
    '''
    composition = CompositionType()
    for token in formula.split(" "):
        match = re.search(r"(?P<isotope>\d+)?(?P<elemet>[^\(]+)(?:\((?P<count>-?\d+)\))?", token)
        if match:
            isotope, element, count = match.groups()
            if count is not None:
                count = int(count)
            else:
                count = 1
            if isotope:
                name = _make_isotope_string(element, int(isotope))
            else:
                name = element
            is_brick = session.query(Brick).filter(Brick.brick == name).first()
            if is_brick is None:
                composition[str(name)] += count
            else:
                composition += is_brick.composition * count
    return composition


def _composition_listener(attr):
    '''
    Attach event listeners to an InstrumentedAttribute
    to trigger formula parsing on load and on change.
    '''
    @event.listens_for(attr, "set")
    def _update_composition_from_formula(target, value, oldvalue, initiator):
        session = object_session(target)
        if value == "" or value is None:
            return
        # If the object hasn't been associated with a session,
        # we can't look up bricks.
        if session is None:
            return
        target.composition = _formula_parser(value, session)

    @event.listens_for(attr.class_, "load")
    def _update_composition_on_load(target, context):
        value = getattr(target, attr.prop.key)
        if value == "" or value is None:
            return
        session = object_session(target)
        target.composition = _formula_parser(value, session)


def has_composition(attr_name):
    '''
    A decorator to simplify flagging a Model with a column
    to be treated as a formula for parsing. Calls :func:`_composition_listener`
    internally.
    '''
    def decorator(model):
        _composition_listener(getattr(model, attr_name))
        return model
    return decorator


class HasFullNameMixin(object):
    '''
    A simple mixin to standardize equality operators
    for models with a :attr:`full_name` attribute.
    '''
    def __eq__(self, other):
        try:
            return self.full_name == other.full_name
        except AttributeError:
            return self.full_name == other

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.full_name)


class AlternativeName(Base):
    __tablename__ = "AlternativeName"

    _tag_name = "alt_names_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib["record_id"]),
            alt_name=attrib['alt_name'],
            modification_id=int(attrib['mod_key'])
        )
        return inst

    id = Column(Integer, primary_key=True)
    alt_name = Column(Unicode(256), index=True)
    modification_id = Column(Integer, ForeignKey("Modification.id"), index=True)


class AminoAcid(Base, HasFullNameMixin):
    __tablename__ = "AminoAcid"

    _tag_name = "amino_acids_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            full_name=attrib['full_name'],
            one_letter=attrib['one_letter'],
            three_letter=attrib['three_letter'],
            num_H=int(attrib["num_H"]),
            num_O=int(attrib["num_O"]),
            num_C=int(attrib["num_C"]),
            num_N=int(attrib["num_N"]),
            num_S=int(attrib["num_S"]),
        )
        return inst

    id = Column(Integer, primary_key=True)
    num_H = Column(Integer)
    num_O = Column(Integer)
    num_C = Column(Integer)
    num_N = Column(Integer)
    num_S = Column(Integer)
    full_name = Column(Unicode(25), index=True)
    one_letter = Column(Unicode(10), index=True)
    three_letter = Column(Unicode(10), index=True)


@attr_repr("classification")
class Classification(Base):
    __tablename__ = "Classification"

    _tag_name = "classifications_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            classification=attrib["classification"]
        )
        return inst

    id = Column(Integer, primary_key=True)
    classification = Column(Unicode(30), index=True)


@attr_repr("position")
class Position(Base):
    __tablename__ = "Position"

    _tag_name = "positions_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            position=attrib['position']
        )
        return inst

    def __eq__(self, other):
        try:
            return self.position == other.position
        except AttributeError:
            return self.position == other

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.position)

    id = Column(Integer, primary_key=True)
    position = Column(Unicode(20), index=True)


class Brick(Base, HasFullNameMixin):
    __tablename__ = "Brick"

    _tag_name = "bricks_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            brick=attrib['brick'],
            full_name=attrib['full_name']
        )
        return inst

    id = Column(Integer, primary_key=True)
    brick = Column(Unicode(64), index=True)
    full_name = Column(Unicode(128), index=True)

    elements = relationship("BrickToElement")

    @property
    def composition(self):
        composition = CompositionType()
        for element_relation in self.elements:
            symbol = element_relation.element
            isotope, element = re.search(r"(?P<isotope>\d+)?(?P<element>\S+)", symbol).groups()
            if isotope:
                isotope = int(isotope)
                iso_str = _make_isotope_string(element, isotope)
            else:
                iso_str = element
            count = element_relation.count
            composition[str(iso_str)] = count
        return composition


class Fragment(Base):
    __tablename__ = "Fragment"

    _tag_name = "fragments_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            modification_id=int(attrib["mod_key"])
        )
        return inst

    id = Column(Integer, primary_key=True)
    modification_id = Column(Integer, ForeignKey("Modification.id"), index=True)

    _fragment_composition = relationship("FragmentComposition")

    @property
    def composition(self):
        composition = CompositionType()
        session = object_session(self)
        for fragment_composition_relation in self._fragment_composition:
            symbol = fragment_composition_relation.brick_string
            isotope, element = re.search(r"(?P<isotope>\d+)?(?P<element>\S+)", symbol).groups()
            count = fragment_composition_relation.count
            if count is not None:
                count = int(count)
            else:
                count = 1
            if isotope:
                name = _make_isotope_string(element, isotope)
            else:
                name = element
            is_brick = session.query(Brick).filter(Brick.brick == name).first()
            if is_brick is None:
                composition[str(name)] += count
            else:
                composition += is_brick.composition * count
        return composition


class FragmentComposition(Base):
    __tablename__ = "FragmentComposition"

    _tag_name = "fragment_comp_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            brick_string=attrib["brick"],
            fragment_id=int(attrib["fragments_key"]),
            count=int(attrib["num_brick"])
        )
        return inst

    id = Column(Integer, primary_key=True)
    brick_string = Column(Unicode(64), ForeignKey(Brick.brick), index=True)
    fragment_id = Column(Integer, ForeignKey("Fragment.id"), index=True)
    count = Column(Integer)


class ModificationToBrick(Base):
    __tablename__ = "ModificationToBrick"

    _tag_name = "mod2brick_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            brick_string=(attrib['brick']),
            modification_id=int(attrib["mod_key"]),
            count=int(attrib["num_brick"])
        )
        return inst

    id = Column(Integer, primary_key=True)
    brick_string = Column(Unicode(64), ForeignKey(Brick.brick), index=True)
    modification_id = Column(Integer, ForeignKey("Modification.id"), index=True)
    count = Column(Integer)


class BrickToElement(Base):
    __tablename__ = "BrickToElement"

    _tag_name = "brick2element_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            brick_id=int(attrib['brick_key']),
            count=int(attrib["num_element"]),
            element=attrib['element']
        )
        return inst

    id = Column(Integer, primary_key=True)
    brick_id = Column(Integer, ForeignKey(Brick.id), index=True)
    element = Column(Unicode(16), ForeignKey("Element.element"), index=True)
    element_obj = relationship("Element", uselist=False)
    count = Column(Integer)


class Element(Base, HasFullNameMixin):
    __tablename__ = "Element"

    _tag_name = "elements_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            average_mass=float(attrib["avge_mass"]),
            monoisotopic_mass=float(attrib["mono_mass"]),
            full_name=attrib["full_name"],
            element=attrib["element"]
        )
        return inst

    id = Column(Integer, primary_key=True)
    average_mass = Column(Numeric(12, 6, asdecimal=False))
    monoisotopic_mass = Column(Numeric(12, 6, asdecimal=False))
    full_name = Column(Unicode(64), index=True)
    element = Column(Unicode(16), index=True)


@has_composition("_composition")
class Modification(Base, HasFullNameMixin):
    __tablename__ = "Modification"

    _tag_name = "modifications_row"

    id = Column(Integer, primary_key=True)
    username_of_poster = Column(Unicode(128))
    average_mass = Column(Numeric(12, 6, asdecimal=False), index=True)
    ex_code_name = Column(Unicode(64), index=True)
    monoisotopic_mass = Column(Numeric(12, 6, asdecimal=False), index=True)
    full_name = Column(Unicode(128), index=True)
    code_name = Column(Unicode(128), index=True)
    _composition = Column(Unicode(128), index=True)
    approved = Column(Boolean, index=True)

    notes = relationship("MiscNotesModifications")
    specificities = relationship("Specificity")
    bricks = relationship(ModificationToBrick)
    crossreferences = relationship("Crossreference")
    _fragments = relationship(Fragment)

    _alt_names = relationship(AlternativeName, backref=backref("modification"))
    # Maps the list of AlternativeName instances loaded dynamically from _alt_names
    # into a list of plain strings, since the AlternativeName type contains no
    # additional information.
    alternative_names = association_proxy("_alt_names", "alt_name")
    fragments = association_proxy("_fragments", "composition")

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib["record_id"]),
            username_of_poster=attrib["username_of_poster"],
            average_mass=float(attrib["avge_mass"]),
            monoisotopic_mass=float(attrib["mono_mass"]),
            ex_code_name=attrib["ex_code_name"],
            code_name=attrib["code_name"],
            full_name=attrib["full_name"],
            approved=bool(int(attrib['approved'])),
            _composition=attrib["composition"]
        )
        for note in tag:
            if note.tag == MiscNotesModifications._tag_name:
                model_note = MiscNotesModifications._from_tag(note, inst.id)
                if model_note is not None:
                    inst.notes.append(model_note)
        return inst

    @property
    def name(self):
        return self.ex_code_name


class MiscNotesModifications(Base):
    __tablename__ = "MiscNotesModifications"
    _tag_name = "misc_notes"

    id = Column(Integer, primary_key=True)
    modification_id = Column(Integer, ForeignKey(Modification.id), index=True)
    text = Column(UnicodeText)

    @classmethod
    def _from_tag(cls, tag, modification_id):
        if tag.text is None:
            return
        return cls(text=tag.text, modification_id=modification_id)


class Specificity(Base):
    __tablename__ = "Specificity"

    _tag_name = "specificity_row"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey(Position.id), index=True)
    classification_id = Column(Integer, ForeignKey(Classification.id), index=True)
    classification = relationship("Classification", uselist=False)
    # Map through one_letter
    amino_acid = Column(Unicode(10), ForeignKey(AminoAcid.one_letter), index=True)
    modification_id = Column(Integer, ForeignKey(Modification.id), index=True)
    hidden = Column(Boolean, index=True)
    group = Column(Integer, index=True)
    neutral_losses = relationship("SpecificityToNeutralLoss")

    position = relationship(Position)

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            position_id=int(attrib['position_key']),
            classification_id=int(attrib["classifications_key"]),
            hidden=bool(int(attrib["hidden"])),
            amino_acid=attrib["one_letter"],
            modification_id=int(attrib["mod_key"]),
        )
        return inst


class NeutralLoss(Base):
    __tablename__ = "NeutralLoss"

    _tag_name = "neutral_losses_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            brick_string=(attrib['brick']),
            count=int(attrib["num_brick"]),
            specificity_id=int(attrib["spec_key"])
        )
        return inst

    id = Column(Integer, primary_key=True)
    brick_string = Column(Unicode(64), index=True)
    specificity_id = Column(Integer, ForeignKey(Specificity.id), index=True)
    count = Column(Integer)


@has_composition("_composition")
class SpecificityToNeutralLoss(Base):
    __tablename__ = "SpecificityToNeutralLoss"

    _tag_name = "spec2nl_row"

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls(
            id=int(attrib['record_id']),
            specificity_id=int(attrib["spec_key"]),
            monoisotopic_mass=float(attrib["nl_mono_mass"]),
            average_mass=float(attrib["nl_avge_mass"]),
            is_required_peptide_neutral_loss=bool(int(attrib["is_req_pep_nl"])),
            is_peptide_neutral_loss=bool(int(attrib["is_pep_nl"])),
            is_slave=bool(int(attrib["is_slave_nl"])),
            _composition=attrib['nl_composition']
        )
        return inst

    id = Column(Integer, primary_key=True)
    specificity_id = Column(Integer, ForeignKey(Specificity.id), index=True)
    specificity = relationship(Specificity, uselist=False)
    monoisotopic_mass = Column(Numeric(12, 6, asdecimal=False), index=True)
    average_mass = Column(Numeric(12, 6, asdecimal=False), index=True)
    _composition = Column(Unicode(128))
    is_slave = Column(Boolean, index=True)
    is_peptide_neutral_loss = Column(Boolean, index=True)
    is_required_peptide_neutral_loss = Column(Boolean, index=True)


class CrossreferenceSource(Base):
    __tablename__ = "CrossreferenceSource"
    _tag_name = "xref_sources_row"

    id = Column(Integer, primary_key=True)
    source = Column(Unicode(64), index=True)

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls()
        inst.id = int(attrib['record_id'])
        inst.source = attrib['xref_source']
        return inst


class Crossreference(Base):
    __tablename__ = "Crossreference"

    _tag_name = "xrefs_row"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey(CrossreferenceSource.id), index=True)
    source = relationship(CrossreferenceSource, uselist=False)
    url = Column(Unicode(128))
    modification_id = Column(Integer, ForeignKey(Modification.id), index=True)
    text = Column(UnicodeText)

    @classmethod
    def from_tag(cls, tag):
        attrib = tag.attrib
        inst = cls()
        inst.id = int(attrib['record_id'])
        inst.url = attrib['xref_url']
        inst.source_id = int(attrib['xref_source_key'])
        inst.modification_id = int(attrib["mod_key"])
        text = []
        for node in tag.getchildren():
            if node.tag == "xref_text":
                if node.text is not None:
                    text.append(node.text)
        inst.text = "\n".join(text)
        return inst


class History(Base):
    __tablename__ = "History"

    id = Column(Integer, primary_key=True)
    url = Column(Unicode(128))
    version = Column(Unicode(128))


def create(doc_path, output_path="sqlite://"):
    '''
    Parse the relational table-like XML file provided by http://www.unimod.org/downloads.html
    and convert each <tag>_row into an equivalent database entry.

    By default the table will be held in memory.
    '''
    tree = preprocess_xml(doc_path)
    engine = create_engine(output_path)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=sa_exc.SAWarning)
        for model in model_registry:
            if hasattr(model, "_tag_name") and hasattr(model, "from_tag"):
                for tag in tree.iterfind(".//" + model._tag_name):
                    session.add(model.from_tag(tag))
            session.commit()
        root = tree.getroot()
        version = "%s.%s" % (root.attrib['majorVersion'], root.attrib['minorVersion'])
        if not isinstance(doc_path, basestring):
            try:
                doc_path = doc_path.name
            except AttributeError:
                doc_path = str(doc_path)
        session.add(History(url=doc_path, version=version))
        session.commit()
    return session


def session(path="sqlite:///unimod.db"):
    engine = create_engine(path)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    return session


class Unimod(object):
    name = "UNIMOD"
    default_version = '1.0'

    def __init__(self, path=None, unimod_xml_uri=_unimod_xml_download_url):
        if path is None:
            self.path = None
            self.session = create(unimod_xml_uri)
        else:
            self.path = path
            try:
                self.session = session(path)
                if self.session.query(Modification).first() is None:
                    raise Exception()
            except Exception:
                # Database may not yet exist at that location
                self.session = create(unimod_xml_uri, path)
                self.session.query(Modification).first()

    @property
    def version(self):
        try:
            version = self.session.query(History.version).all()
            if len(version) > 0:
                version = max(version)
            return version[0]
        except Exception:
            return self.default_version

    def get(self, identifier, strict=True):
        is_explicit_accession = isinstance(identifier, basestring) and identifier.startswith("UNIMOD")
        try:
            # At least one Modification has an empty string code_name or ex_code_name, causing
            # this fuzzy finder function to happily respond to that record
            if identifier == "":
                raise KeyError(identifier)
        except (TypeError, ValueError):
            pass
        if isinstance(identifier, int) or is_explicit_accession:
            if is_explicit_accession:
                identifier = int(identifier.replace("UNIMOD:", ''))
            mod = self.session.query(Modification).get(identifier)
            if mod is None:
                raise KeyError(identifier)
            return mod
        elif isinstance(identifier, basestring):
            if strict:
                mod = self.session.query(Modification).filter(
                    (Modification.full_name == identifier) |
                    (Modification.code_name == identifier) |
                    (Modification.ex_code_name == identifier)).first()
                if mod is None:
                    alt_name = self.session.query(AlternativeName).filter(
                        AlternativeName.alt_name == identifier).first()
                    if alt_name is None:
                        raise KeyError(identifier)
                    mod = alt_name.modification
                return mod
            else:
                qname = "%%%s%%" % identifier
                mod = self.session.query(Modification).filter(
                    (Modification.full_name.like(qname)) |
                    (Modification.code_name.like(qname)) |
                    (Modification.ex_code_name.like(qname))).first()
                if mod is None:
                    alt_name = self.session.query(AlternativeName).filter(
                        AlternativeName.alt_name.like(qname)).first()
                    if alt_name is None:
                        raise KeyError(identifier)
                    mod = alt_name.modification
                return mod
        else:
            raise KeyError(identifier)

    by_title = by_name = get

    __getitem__ = get

    def infer(self, mass, amino_acid, mass_error=1e-6):
        candidates = self.session.query(Modification).filter(
            Modification.monoisotopic_mass.between(mass - mass_error, mass + mass_error)
        ).join(Modification.specificities).filter(Specificity.amino_acid == amino_acid).all()
        return candidates

    @property
    def mods(self):
        return self.session.query(Modification).all()

    def __iter__(self):
        return iter(self.session.query(Modification).yield_per(1000))


def load(path=None):
    return Unimod(path)


class UNIMODEntity(Entity):

    def is_of_type(self, tp):
        try:
            if tp.startswith('UNIMOD'):
                return True
            return False
        except AttributeError:
            if isinstance(tp, UNIMODEntity):
                return True

    @classmethod
    def converter(cls, modification, vocabulary):
        data = dict(KeyToAttrProxy(modification))
        data['id'] = 'UNIMOD:%s' % modification.id
        data['name'] = modification.ex_code_name or modification.code_name or modification.full_name
        data['_object'] = modification
        return cls(vocabulary, **data)
