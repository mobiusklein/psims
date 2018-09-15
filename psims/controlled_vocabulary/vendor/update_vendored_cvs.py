import os
import re
import hashlib

try:
    from urllib2 import urlopen, Request
except ImportError:
    from urllib.request import urlopen, Request


registry = {
    "psi-ms.obo": "https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo",
    "unit.obo": "http://ontologies.berkeleybop.org/uo.obo",
    'pato.obo': "http://ontologies.berkeleybop.org/pato.obo",
    "unimod_tables.xml": "http://www.unimod.org/xml/unimod_tables.xml",
    "XLMOD.obo": "https://raw.githubusercontent.com/HUPO-PSI/mzIdentML/master/cv/XLMOD.obo",
    # appears to reject automated download unless User-Agent is said
    "bto.obo": "http://www.brenda-enzymes.info/ontology/tissue/tree/update/update_files/BrendaTissueOBO",
    "go.obo": "http://purl.obolibrary.org/obo/go.obo"
}


storage_dir = os.path.dirname(__file__)

for cv, url in registry.items():
    print("Updating %s from %s" % (cv, url))
    path = os.path.join(storage_dir, cv)
    old_hash = hashlib.new("md5")
    if not os.path.exists(path):
        print("No Previous Version")
    else:
        with open(path) as current:
            read = current.read(2000)
            version_search = re.search("data-version: ([^\n]+)\n", read)
            if version_search:
                print("Have Version %s" % (version_search.group(1),))
            while read:
                old_hash.update(read)
                read = current.read(2000)
            print("Checksum (MD5): %s" % old_hash.hexdigest())

    rq = Request(url, headers={
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like'
                       ' Gecko) Chrome/68.0.3440.106 Safari/537.36')
    })
    f = urlopen(rq)
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
    new_hash = hashlib.new("md5")
    with open(path) as current:
            read = current.read(2000)
            version_search = re.search("data-version: ([^\n]+)\n", read)
            if version_search:
                print("New Version %s" % (version_search.group(1),))
            while read:
                new_hash.update(read)
                read = current.read(2000)
            print("Checksum (MD5): %s" % new_hash.hexdigest())
