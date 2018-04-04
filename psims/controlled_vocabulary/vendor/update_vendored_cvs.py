import os
import re

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen


registry = {
    "psi-ms.obo": "https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo",
    "unit.obo": "http://ontologies.berkeleybop.org/uo.obo",
    'pato.obo': "http://ontologies.berkeleybop.org/pato.obo",
    "unimod_tables.xml": "http://www.unimod.org/xml/unimod_tables.xml"
}


storage_dir = os.path.dirname(__file__)

for cv, url in registry.items():
    print("Updating %s from %s" % (cv, url))
    path = os.path.join(storage_dir, cv)
    if not os.path.exists(path):
        print("No Previous Version")
    else:
        with open(path) as current:
            head = current.read(2000)
            version_search = re.search("data-version: ([^\n]+)\n", head)
            if version_search:
                print("Have Version %s" % (version_search.group(1),))
    f = urlopen(url)
    code = None
    # The keepalive library monkey patches urllib2's urlopen and returns
    # an object with a different API. First handle the normal case, then
    # the patched case.
    if hasattr(f, 'getcode'):
        code = f.getcode()
    elif hasattr(f, "code"):
        code = f.code
    else:
        raise ValueError("Can't understand how to get HTTP response code from %r" % f)
    if code != 200:
        raise ValueError("%s did not resolve" % url)
    with open(path, 'wb') as fh:
        content = f.read(2**16)
        while content:
            fh.write(content)
            content = f.read(2**16)
    with open(path) as current:
            head = current.read(2000)
            version_search = re.search("data-version: ([^\n]+)\n", head)
            if version_search:
                print("New Version %s" % (version_search.group(1),))
