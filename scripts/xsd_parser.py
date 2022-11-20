import json

from urllib.request import urlopen
from collections import defaultdict, deque, namedtuple

from lxml import etree


ScopeMarker = namedtuple("ScopeMarker", ("tag", "name"))

def _local_name(element):
    """Strip namespace from the XML element's name"""
    tag = element.tag
    if tag and tag[0] == '{':
        return tag.rpartition('}')[2]
    return tag


def toposort(pairs):
    incoming = defaultdict(set)
    outgoing = defaultdict(set)
    nodes = set()
    for child, parent in pairs:
        nodes.add(child)
        nodes.add(parent)
        incoming[child].add(parent)
        outgoing[parent].add(child)
    has_no_parents = {k for k in nodes if not incoming[k]}

    result = []
    while has_no_parents:
        node = has_no_parents.pop()
        result.append(node)
        for edge in outgoing[node]:
            node_to_child = incoming[edge]
            node_to_child.remove(node)
            if not node_to_child:
                has_no_parents.add(edge)
    return result


def dequalify_name(type_name):
    if not type_name:
        return (None, type_name)
    if ":" in type_name:
        return type_name.split(":", 1)
    return None, type_name


class AliasableTypeDefinitionMapping(object):
    def __init__(self, mapping=None):
        self.mapping = defaultdict(dict, mapping or {})
        self.aliases = dict()

    def __getitem__(self, key):
        if key in self.aliases:
            key = self.aliases[key]
        return self.mapping[key]

    def __setitem__(self, key, value):
        self.mapping[key] = value

    def __delitem__(self, key):
        del self.mapping[key]

    def __len__(self):
        return len(self.mapping)

    def __iter__(self):
        return iter(self.mapping)

    def __contains__(self, key):
        if key in self.aliases:
            key = self.aliases[key]
        return key in self.mapping

    def keys(self):
        return self.mapping.keys()

    def values(self):
        return self.mapping.values()

    def items(self):
        return self.mapping.items()

    def get(self, key, default=None):
        if key in self.aliases:
            key = self.aliases[key]
        return self.mapping.get(key, default)

    def add_alias(self, name, alias):
        self.aliases[alias] = name

    def __repr__(self):
        return "{self.__class__.__name__}({self.mapping}, {self.aliases})".format(self=self)


def parse_schema(tree):
    data_types = AliasableTypeDefinitionMapping()
    type_stack = deque()

    has_ref = set()
    has_extension = set()
    inline_element = set()

    for event, element in etree.iterwalk(tree, events=("start", "end")):
        elt_name = _local_name(element)
        if event == "start":
            if (elt_name == "element") or (elt_name in ("complexType", "attributeGroup") and not type_stack):
                if "name" in element.attrib:
                    entity_name = element.attrib['name']
                if type_stack:
                    ns, tp_name = dequalify_name(element.attrib.get("type"))
                    if element.attrib.get("maxOccurs", '1') != '1' and type_stack:
                        data_types[type_stack[-1].name][entity_name] = ('list', tp_name)
                        inline_element.add((entity_name, tp_name))
                    elif tp_name:
                        data_types[type_stack[-1].name][entity_name] = tp_name
                        inline_element.add((entity_name, tp_name))
                type_stack.append(ScopeMarker(elt_name, entity_name))
            elif elt_name == "attribute":
                attr_name = element.attrib['name']
                value_type = element.attrib.get('type', 'xs:string')
                ns, value_type = dequalify_name(value_type)
                data_types[type_stack[-1].name][attr_name] = value_type
            elif elt_name == "attributeGroup":
                tp_name = element.attrib.get('name')
                ns, tp_name = dequalify_name(tp_name)
                data_types[type_stack[-1].name]['$REF'] = element.attrib.get("ref", tp_name)
                has_ref.add((type_stack[-1].name, element.attrib.get("ref", tp_name)))
            elif elt_name == "extension":
                tp_name = element.attrib['base']
                ns, tp_name = dequalify_name(tp_name)
                data_types[type_stack[-1].name]['$BASE'] = tp_name
                has_extension.add((type_stack[-1].name, tp_name))
        else:
            if elt_name == "element" or ((elt_name in ("complexType", "attributeGroup") and len(type_stack) == 1) and elt_name == type_stack[-1].tag):
                last_name = type_stack.pop()

    for node in toposort(has_extension):
        if "$BASE" in data_types[node]:
            dt = data_types[node]
            base_type = dt.pop("$BASE")
            dt.update(data_types[base_type])

    for node in toposort(has_ref):
        if "$REF" in data_types[node]:
            dt = data_types[node]
            base_type = dt.pop("$REF")
            dt.update(data_types[base_type])

    for elt, elt_type in inline_element:
        data_types.add_alias(elt_type, elt)
    return data_types


def transpose_build_type_map(data_types):
    types = {
        "ints": {
            "int",
            "long",
            "nonNegativeInteger",
            "positiveInt",
            "integer",
            "unsignedInt",
        },
        "floats": {"float", "double"},
        "bools": {"boolean"},
        "intlists": {"listOfIntegers"},
        "floatlists": {"listOfFloats"},
        "charlists": {"listOfChars", "listOfCharsOrAny"},
        "lists": {"list", }
    }
    ret = {}

    for k, val in types.items():
        pairs = set()
        for typename, attribs in data_types.items():
            for attr, val_type in attribs.items():
                if isinstance(val_type, tuple):
                    for vt in val_type:
                        if vt in val:
                            pairs.add((typename, attr))
                elif val_type in val:
                    pairs.add((typename, attr))
        ret[k] = pairs
    return  ret


def dump_attributes(schema_url):
    fh = urlopen(schema_url)
    tree = etree.parse(fh)
    schema = parse_schema(tree)
    groups = defaultdict(lambda: defaultdict(list))
    for tp_name, props in schema.items():
        for prop_name, prop_tp in props.items():
            if isinstance(prop_tp, tuple) or prop_tp in schema:
                continue
            groups[prop_name][prop_tp].append(tp_name)
    print(json.dumps(groups, sort_keys=True, indent=2))
    return groups


if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    dump_attributes(url)
