import io
from typing import DefaultDict, Dict, List, Optional, Any
import warnings

from collections import defaultdict

from six import string_types as basestring

from psims.utils import ensure_iterable

from .entity import Entity
from .relationship import Relationship, Reference, HasValueTypeRelationship
from .type_definition import parse_xsdtype, type_inference_guess


synonym_scopes = {
    "EXACT",
    "BROAD",
    "NARROW",
    "RELATED"
}


def _synonym_parser(text):
    state = None
    quoted_chars = []
    scopes = []
    scope_chars = []
    references = []
    for c in text:
        if c == "\"":
            if state is None:
                state = "quote_open"
            elif state == 'quote_open':
                state = "quote_close"
            elif state == 'trailing':
                pass
            else:
                raise ValueError("Quote after quoted text!")
        else:
            if state == "quote_open":
                quoted_chars.append(c)
            elif state == "quote_close":
                if c == " ":
                    state = 'scope'
                else:
                    raise ValueError("Expected space before scope")
            elif state == 'scope':
                if c == ' ':
                    scopes.append(''.join(scope_chars))
                    scope_chars = []
                elif c == '[':
                    state = 'references'
                else:
                    scope_chars.append(c)
            elif state == 'references':
                if c != ']':
                    references.append(c)
                else:
                    state = 'trailing'
            elif state == 'trailing':
                pass
    return ''.join(quoted_chars), scopes, ''.join(references)


def synonym_parser(text):
    synonym, scopes, references = _synonym_parser(text)
    return synonym


class OBOParser(object):
    """Parser for an :title-reference:`OBO` [OBO]_ file that constructs a semantic graph.

    Attributes
    ----------
    current_term : dict
        The current term being parsed
    handle : file
        The file stream to read from
    header : defaultdict(list)
        Store the header information from the OBO file
    terms : dict
        Maps term id to :class:`~.Entity` objects

    References
    ----------
    OBO
        http://owlcollab.github.io/oboformat/doc/GO.format.obo-1_2.html
    """

    handle: io.IOBase
    terms: Dict[str, Entity]
    current_term: Optional[Dict[str, Any]]
    header: DefaultDict[str, List[str]]

    def __init__(self, handle, type_inference_rules=None):
        if type_inference_rules is None:
            type_inference_rules = {}
        self.handle = handle
        self.terms = {}
        self.current_term = None
        self.header = defaultdict(list)
        self.type_inference_rules = type_inference_rules
        self.parse()

    @property
    def version(self):
        try:
            return self.header['data-version']
        except KeyError:
            return None

    @property
    def name(self):
        try:
            names = self.header['ontology']
            if isinstance(names, str):
                return names.upper()
            return names[0].upper()
        except KeyError:
            return None

    def _get_value_type(self, xref_string):
        # Plug into the HasValueTypeRelationship mechanism to push this off onto
        # later type conversion determination logic
        name = xref_string.replace("value-type:", '').strip().split(" ")[0]
        return HasValueTypeRelationship(HasValueTypeRelationship.name, name, name)

    def pack(self):
        """Pack the currently collected OBO entry into an :class:`~.Entity`.

        Returns
        -------
        :class:`~.Entity`
        """
        if self.current_term is None:
            return
        self.current_term['_class'] = self.term_type
        entity = Entity(self, **{k: v[0] if len(v) == 1 else v for k, v in self.current_term.items()})
        self._expand_is_a(entity)
        self._expand_synonym(entity)
        self._expand_xref(entity)
        self._expand_property_value(entity)
        self._expand_relationship(entity)
        self.terms[entity['id']] = entity
        self.current_term = None

    def _expand_is_a(self, entity):
        if "is_a" in entity.data:
            is_as = entity['is_a']
            if isinstance(is_as, basestring):
                is_as = Reference.fromstring(is_as)
            else:
                is_as = list(map(Reference.fromstring, is_as))
            entity['is_a'] = is_as

    def _expand_relationship(self, entity):
        if 'relationship' in entity.data:
            relationships = entity['relationship']
            if not isinstance(relationships, list):
                relationships = [relationships]
            relationships = [Relationship.fromstring(r) for r in relationships]
            entity.data['relationship'] = relationships
            for rel in relationships:
                entity.setdefault(rel.predicate, [])
                entity[rel.predicate].append(rel)
        else:
            entity.data['relationship'] = []

    def _expand_synonym(self, entity):
        if 'synonym' in entity.data:
            synonyms = entity['synonym']
            if not isinstance(synonyms, list):
                synonyms = [synonyms]
            synonyms = list(map(synonym_parser, synonyms))
            entity['synonym'] = synonyms

    def _infer_type(self, key, value):
        rule = self.type_inference_rules.get(key)
        if rule is not None:
            value = rule(value)
        else:
            value = type_inference_guess(value)
        return value

    def _expand_xref(self, entity):
        entity.value_type = None
        if 'xref' in entity.data:
            xref = entity['xref']
            if isinstance(xref, basestring):
                xref = [xref]
            for x in xref:
                try:
                    key, value = x.split(":", 1)
                except ValueError:
                    key, value = x.split(' \"', 1)
                    value = '\"' + value
                if key == 'value-type':
                    rel = self._get_value_type(x)
                    entity.setdefault(rel.predicate, [])
                    entity[rel.predicate].append(rel)
                else:
                    if value.startswith("\""):
                        try:
                            value, dtype = value.rsplit('\" ', 1)
                            value += '\"'
                        except ValueError:
                            dtype = None
                        value = value.strip()
                        if dtype is not None:
                            dtype, _ = parse_xsdtype(dtype)
                        if dtype is not None:
                            value = dtype(value[1:-1])
                        else:
                            value = self._infer_type(key, value)
                    else:
                        value = value.strip()
                        value = self._infer_type(key, value)
                    entity[key] = value

    def _expand_property_value(self, entity):
        if "property_value" in entity.data:
            for prop_val in ensure_iterable(entity.data['property_value']):
                prop, val = prop_val.split(" ", 1)
                prop = prop.strip(": ")
                val = val.strip()
                if val.startswith("\""):
                    val, dtype = val.rsplit(" ", 1)
                    dtype, _ = parse_xsdtype(dtype)
                    try:
                        val = dtype(val[1:-1])
                    except (ValueError, TypeError):
                        pass
                entity[prop] = val

    def _connect_parents(self):
        """Walk the semantic graph up the parent hierarchy, binding child
        to parent through ``is_a`` :class:`~.Reference` connections.
        """
        term: Entity
        rel: Relationship
        for term in self.terms.values():
            try:
                if isinstance(term.is_a, Reference):
                    self.terms[term.is_a].children.append(term)
                else:
                    for is_a in term.is_a:
                        self.terms[is_a].children.append(term)
            except KeyError:
                pass
            try:
                for rel in term.relationship:
                    if rel.predicate == 'part_of':
                        larger = self.terms[rel.accession]
                        larger.setdefault('parts', [])
                        larger.parts.append(term)
            except KeyError:
                pass

    def _pack_if_occupied(self):
        if self.current_term is not None:
            self.pack()

    def _simplify_header_information(self):
        self.header = {
            k: v if len(v) > 1 else v[0] for k, v in self.header.items()
        }

    def parse(self):
        """Iteratively parse a binary file stream for an OBO file into a
        semantic graph.
        """
        in_header = True
        for line in self.handle.readlines():
            line = line.decode('utf-8')
            line = line.strip()
            if not line:
                in_header = False
                continue
            elif in_header:
                key, val = line.split(":", 1)
                self.header[key].append(val.strip())
            elif line == "[Typedef]":
                self._pack_if_occupied()
                self.current_term = defaultdict(list)
                self.term_type = "typedef"
            elif line == "[Term]":
                self._pack_if_occupied()
                self.current_term = defaultdict(list)
                self.term_type = 'term'
            else:
                if self.current_term is None:
                    continue
                key, sep, val = line.partition(":")
                self.current_term[key].append(val.strip())
        self.pack()
        self._connect_parents()
        self._simplify_header_information()
        self.handle.close()

    def __getitem__(self, key):
        return self.terms[key]

    def __iter__(self):
        return iter(self.terms.items())


class OBOWriter(object):
    def __init__(self, stream):
        self.stream = stream

    def write_header(self, header):
        for key, value in header.items():
            if isinstance(value, (list, tuple)):
                for v in value:
                    self.stream.write("%s: %s\n" % (key, v))
            else:
                self.stream.write("%s: %s\n" % (key, value))
        self.stream.write("\n")

    def write_term(self, term):
        if term._class == 'term':
            self.stream.write("[Term]\nid: %s\nname: %s\n" %
                        (term.id, term.name, ))
            if term.definition:
                self.stream.write("def: %s\n" % (term.definition, ))
            seen = set()
            for syn in ensure_iterable(term.get('synonyms', [])):
                if syn in seen:
                    continue
                seen.add(syn)
                self.stream.write("synonym: \"%s\" EXACT\n" % str(syn).replace("\n", "\\n"))
            for xref in ensure_iterable(term.get('xref', [])):
                self.stream.write("xref: %s\n" % str(xref))
            for is_a in ensure_iterable(term.get("is_a", [])):
                self.stream.write("is_a: %s\n" % str(is_a))
            for rel in ensure_iterable(term.get("relationship", [])):
                self.stream.write("relationship: %s\n" % str(rel))
            for prop in ensure_iterable(term.get('property_value', [])):
                self.stream.write("property_value: %s\n" % prop)
            self.stream.write("\n")
        elif term._class == "typedef":
            self.stream.write("[Typedef]\nid: %s\nname: %s\n" %
                              (term.id, term.name, ))
            if term.definition:
                self.stream.write("def: %s\n" % term.definition)
            seen = set()
            for syn in ensure_iterable(term.get('synonyms', [])):
                if syn in seen:
                    continue
                seen.add(syn)
                self.stream.write("synonym: \"%s\" EXACT\n" %
                                  str(syn).replace("\n", "\\n"))
            for xref in ensure_iterable(term.get('xref', [])):
                self.stream.write("xref: %s\n" % str(xref))
            keys = ['domain', 'range', 'is_anti_symmetric', 'is_cyclic',
                    'is_reflexive', 'is_symmetric', 'is_transitive', 'is_a',
                    'transitive_over']
            for key in keys:
                is_boolean_predicate = key.startswith('is_')
                for d in ensure_iterable(term.get(key, [])):
                    if is_boolean_predicate:
                        if d is True:
                            d = 'true'
                        elif d is False:
                            d = 'false'
                    self.stream.write("%s: %s\n" % (key, d))
            for rel in ensure_iterable(term.get("relationship", [])):
                self.stream.write("relationship: %s\n" % str(rel))
            for prop in ensure_iterable(term.get('property_value', [])):
                self.stream.write("property_value: %s\n" % prop)
            self.stream.write("\n")

    def write_vocabulary(self, vocabulary):
        self.write_header(vocabulary.metadata)
        groups = defaultdict(list)
        for term in vocabulary.terms.values():
            groups[term._class].append(term)
        for tp in  ['typedef', 'term', 'instance']:
            for term in sorted(groups[tp], key=lambda x: x.id):
                self.write_term(term)
