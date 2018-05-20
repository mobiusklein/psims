from lxml import etree

from psims.controlled_vocabulary import load_psims
from psims.utils import simple_repr


MUST = "MUST"
MAY = "MAY"
AND = "AND"
OR = "OR"


static_vocabularies = {
    "MS": load_psims(),
}


class RuleParser(object):
    def __init__(self, rules, vocabularies=None):
        if not vocabularies:
            vocabularies = static_vocabularies.copy()
        self.nsmap = {'ms': 'http://psi.hupo.org/ms/mzml'}
        self.vocabularies = vocabularies
        self.rules = list(rules) or []

    @classmethod
    def from_file(cls, path):
        tree = etree.parse(path)
        rules = map(CVRule.from_element, tree.findall(".//CvMappingRule"))
        return cls(rules)

    def get_rule_targets(self, rule, document):
        return document.xpath(rule.cv_element_path, namespaces=self.nsmap)

    def test_rule(self, rule, document):
        targets = self.get_rule_targets(rule, document)
        term_satisfied = []
        for term in rule.terms:
            cv = self.vocabularies[term.cv_identifier]
            satisfied = []
            for match in targets:
                if self._is_instance_of(match, cv[term.term_accession], cv.allow_children):
                    satisfied.append(match)


    def _is_instance_of(self, term, accession, allow_children=True):
        if not allow_children:
            return term.id == accession
        while term is not None:
            if term.id == accession:
                return True
            term = term.parent()
        return False


def _fix_element_path(elpath, nsprefix):
    steps = elpath.split("/")
    acc = ['/']
    for step in steps:
        if not step:
            continue
        if not step.startswith("@"):
            acc.append("%s:%s" % (nsprefix, step))
        else:
            acc.append(step)
    return '/'.join(acc)


class CVRule(object):
    def __init__(self, id, scope_path, cv_element_path, requirement_level, combinator, terms):
        self.id = id
        self.scope_path = scope_path
        self.cv_element_path = cv_element_path
        self.requirement_level = requirement_level
        self.combinator = combinator
        self.terms = terms

    __repr__ = simple_repr

    @classmethod
    def from_element(cls, element):
        terms = []
        for term in element.getchildren():
            if isinstance(term, etree._Comment):
                continue
            terms.append(CVTerm.from_element(term))
        attrs = element.attrib
        inst = cls(
            attrs.get('id'),
            _fix_element_path(attrs.get('scopePath'), 'ms'),
            _fix_element_path(attrs.get('cvElementPath'), 'ms'),
            attrs.get('requirementLevel'),
            attrs.get('cvTermsCombinatorLogic'),
            terms)
        return inst


def parsebool(text):
    return {
        "true": True,
        "false": False,
        None: None
    }[text]


class CVTerm(object):
    def __init__(self, term_accession, use_term_name, use_term, term_name, is_repeatable, allow_children,
                 cv_identifier):
        self.term_accession = term_accession
        self.use_term_name = use_term_name
        self.use_term = use_term
        self.term_name = term_name
        self.is_repeatable = is_repeatable
        self.allow_children = allow_children
        self.cv_identifier = cv_identifier

    __repr__ = simple_repr

    @classmethod
    def from_element(cls, element):
        attrs = element.attrib
        inst = cls(
            attrs.get("termAccession"),
            parsebool(attrs.get('useTermName')),
            parsebool(attrs.get('useTerm')),
            attrs.get("termName"),
            parsebool(attrs.get("isRepeatable")),
            parsebool(attrs.get("allowChildren")),
            attrs.get("cvIdentifierRef"))
        return inst
