import os
import re
import json
import hashlib

registry = {
    "psi-ms.obo": r"data-version: ([^\n]+)\n",
    "unit.obo": r"data-version: ([^\n]+)\n",
    'pato.obo': r"data-version: ([^\n]+)\n",
    "unimod_tables.xml": None,
    "XLMOD.obo": r"data-version: ([^\n]+)\n",
    "bto.obo": r"date: ([^\n]+)\n",
    "go.obo": r"data-version: ([^\n]+)\n",
    'psi-mod.obo': r"remark: PSI-MOD version: \(([^)\n]+)\)\n",
}


storage_dir = os.path.dirname(__file__)

record = {}


for name, pattern in registry.items():
    print("CV: " + name)
    path = os.path.join(storage_dir, name)
    md5 = hashlib.new("md5")
    if not os.path.exists(path):
        print("%s is missing" % name)

    else:
        with open(path) as current:
            read = current.read(2000)
            if pattern is not None:
                version_search = re.search(pattern, read)
            else:
                version_search = None
            if version_search:
                print("Version %s" % (version_search.group(1),))
                version = version_search.group(1)
            else:
                version = None
            while read:
                md5.update(read)
                read = current.read(2000)
            print("Checksum (MD5): %s" % md5.hexdigest())
        record[name] = {
            "version": version,
            "checksum": md5.hexdigest()
        }

with open(os.path.join(storage_dir, "record.json"), 'wt') as fh:
    json.dump(record, fh, sort_keys=True, indent=2)
