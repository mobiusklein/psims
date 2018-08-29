from __future__ import print_function

import sys

import numpy as np
from pyteomics.xml import cvstr


def _log(message):
    print(message, file=sys.stderr)


class LoggingProxy(object):
    def __init__(self, logger=None):
        self.logger = logger

    def enable(self, logger=None):
        if logger is None:
            logger = _log
        self.logger = logger

    def log(self, message):
        if self.logger is not None:
            self.logger(message)

    def __call__(self, message):
        self.log(message)

    def disable(self):
        self.logger = None


log = LoggingProxy()
log.enable()


def differ(a, b):
    if not issubclass(type(a), type(b)):
        return False
    if isinstance(a, dict):
        return dict_diff(a, b)
    elif isinstance(a, (list, tuple)):
        return all(differ(ai, bi) for ai, bi in zip(sorted(a), sorted(b)))
    elif isinstance(a, float):
        return abs(a - b) < 1e-3
    elif isinstance(a, cvstr):
        return a.accession.lower() == b.accession.lower()
    elif isinstance(a, np.ndarray):
        return np.allclose(a, b)
    else:
        return a == b


def dict_diff(a, b):
    a = dict(a)
    b = dict(b)
    aparams = []
    for key, value in list(a.items()):
        if hasattr(key, 'accession'):
            a.pop(key)
            aparams.append((key, value))
    bparams = []
    for key, value in list(b.items()):
        if hasattr(key, 'accession'):
            b.pop(key)
            bparams.append((key, value))
    aparams.sort()
    bparams.sort()
    if sorted(a.keys(), key=str) != sorted(b.keys(), key=str):
        return False
    for akey, avalue in a.items():
        for bkey, bvalue in b.items():
            if akey == bkey:
                if differ(avalue, bvalue):
                    pass
                else:
                    print(type(avalue))
                    print(akey, avalue, '!=', bvalue)
                    return False
                break
    return differ(aparams, bparams)
