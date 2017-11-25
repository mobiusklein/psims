import os

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen


registry = {
    "psi-ms.obo": "https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo",
    "unit.obo": "http://ontologies.berkeleybop.org/uo.obo",
    "unimod_tables.xml": "http://www.unimod.org/xml/unimod_tables.xml"
}


storage_dir = os.path.dirname(__file__)

for cv, url in registry.items():
    print("Updating %s from %s" % (cv, url))
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
    with open(os.path.join(storage_dir, cv), 'wb') as fh:
        content = f.read(2**16)
        while content:
            fh.write(content)
            content = f.read(2**16)
