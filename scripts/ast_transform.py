# A short script to rewrite class with common methods and attributes

import sys
import ast
import astunparse

path = sys.argv[1]

module = ast.parse(open(path).read())

# Collect all the classes which inherit from ComponentBase
clses = []
for block in module.body:
    if isinstance(block, ast.ClassDef):
        if "ComponentBase" in [b.id for b in block.bases]:
            clses.append(block)


# Inspect each class's __init__ method for an argument called "id" which we'll assume
# means that the class should map to an XML element that has an id attribute
for cls in clses:
    print(cls.name)
    for block in cls.body:
        if isinstance(block, ast.FunctionDef):
            if block.name == "__init__":
                args = block.args
                print '\t', len(args.args), "argument __init__"
                if "id" in [a.id for a in args.args]:
                    print("Has ID")
                    cls.body.insert(0, ast.Assign(targets=[ast.Name(id="requires_id")], value=ast.Name(id="True")))
                    break
    else:
        cls.body.insert(0, ast.Assign(targets=[ast.Name(id="requires_id")], value=ast.Name(id="False")))


# Rewrite the write method as "write_content", removing the top-most with expression
for cls in clses:
    print cls.name
    for block in cls.body:
        if isinstance(block, ast.FunctionDef):
            if block.name == "write":
                assert len(block.body) == 1
                block.name = "write_content"
                if isinstance(block.body[0], ast.With):
                    block.body = block.body[0].body

# Render the AST back into text
path = sys.argv[2]
with open(path, 'w') as fh:
    astunparse.Unparser(module, fh)
