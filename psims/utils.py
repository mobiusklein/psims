from lxml import etree
from six import add_metaclass


def pretty_xml(path, outpath=None):
    tree = etree.parse(path)
    if outpath is None:
        outpath = path
    with open(outpath, 'wb') as outstream:
        outstream.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        outstream.write(
            etree.tostring(tree, pretty_print=True))


# From six
# def add_metaclass(metaclass):
#     """Class decorator for creating a class with a metaclass."""
#     def wrapper(cls):
#         orig_vars = cls.__dict__.copy()
#         slots = orig_vars.get('__slots__')
#         if slots is not None:
#             if isinstance(slots, str):
#                 slots = [slots]
#             for slots_var in slots:
#                 orig_vars.pop(slots_var)
#         orig_vars.pop('__dict__', None)
#         orig_vars.pop('__weakref__', None)
#         return metaclass(cls.__name__, cls.__bases__, orig_vars)
#     return wrapper
