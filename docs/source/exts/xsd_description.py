from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.locale import _
from sphinx.addnodes import desc

from lxml import etree


class xsd_description(nodes.Admonition, nodes.Element):
    pass


def visit_xsd_description_node(self, node):
    self.visit_admonition(node)


def depart_xsd_description_node(self, node):
    self.depart_admonition(node)


def setup(app):
    app.add_config_value("xsd_description_include_xsd_descriptions", False, 'html')
    app.add_config_value("xsd_description_xsd_paths", [], 'html')

    app.add_node(xsd_description,
                 html=(visit_xsd_description_node, depart_xsd_description_node),
                 latex=(visit_xsd_description_node, depart_xsd_description_node),
                 text=(visit_xsd_description_node, depart_xsd_description_node))
    app.add_directive('xsd_description', XSDDescriptionDirective)

    app.connect("doctree-resolved", process_xsd_description_nodes)
    app.connect("env-purge-doc", purge_xsd_descriptions)
    print(xsd_description, app)
    return {'version': '0.1'}


class XSDDescriptionDirective(Directive):
    has_content = True

    def run(self):
        env = self.state.document.settings.env
        target_id = "xsd_description-%d" % env.new_serialno('xsd_description')
        target_node = nodes.target('', '', ids=[target_id])

        xsd_description_node = xsd_description('\n'.join(self.content))
        xsd_description_node += nodes.title(_("XSD Description"), _("XSD Description"))
        self.state.nested_parse(self.content, self.content_offset, xsd_description_node)

        if not hasattr(env, 'xsd_description_all_xsd_descriptions'):
            env.xsd_description_all_xsd_descriptions = []

        env.xsd_description_all_xsd_descriptions.append({
            'docname': env.docname,
            'lineno': self.lineno,
            'xsd_description': xsd_description_node.deepcopy(),
            'target': target_node,
        })

        return [target_node, xsd_description_node]


def purge_xsd_descriptions(app, env, docname):
    if not hasattr(env, 'xsd_description_all_xsd_descriptions'):
        return
    env.todo_all_todos = [xsd_description for xsd_description in env.xsd_description_all_xsd_descriptions
                          if xsd_description['docname'] != docname]


def process_xsd_description_nodes(app, doctree, fromdocname):
    if not app.config.xsd_description_include_xsd_descriptions:
        for node in doctree.traverse(xsd_description):
            node.parent.remove(node)

    env = app.builder.env

    schemata = []
    for xsd in env.config.xsd_description_xsd_paths:
        tree = etree.parse(xsd)
        nsmap = {'xs': 'http://www.w3.org/2001/XMLSchema'}
        component_map = {}
        for tp in tree.findall("/xs:complexType", nsmap):
            doc = tp.find(".//xs:annotation/xs:documentation", nsmap)
            if doc is not None:
                doc = doc.text
            tp_name = tp.attrib.get('name')
            tp_name = tp_name.replace("Type", '', 1).lower()
            component_map[tp_name] = doc
        schemata.append(component_map)

    def find_description(name):
        name = name.lower()
        for schema in schemata:
            try:
                return schema[name]
            except KeyError:
                continue
        return ''

    for xsd_description_node in doctree.traverse(xsd_description):
        cls_name_node = xsd_description_node.parent.parent[0]
        cls_name = cls_name_node.attributes['fullname']
        desc_text = _(find_description(cls_name))
        if desc_text:
            para = nodes.paragraph()
            para += nodes.Text(desc_text, desc_text)
            xsd_description_node.append(para)
        else:
            xsd_description_node.parent.remove(xsd_description_node)

    # inject an XSD description into every class
    for desc_node in doctree.traverse(desc):
        cls_name_node = desc_node[0]
        cls_name = cls_name_node.attributes['fullname']
        desc_text = _(find_description(cls_name))
        if desc_text:
            para = nodes.paragraph()
            para += nodes.Text(desc_text, desc_text)
            xsd_description_node = xsd_description()
            xsd_description_node += nodes.title(_("XSD Description"), _("XSD Description"))
            xsd_description_node.append(para)
            desc_node.append(xsd_description_node)
