import json
import itertools
import csv

from collections import defaultdict
from xsd_parser import dump_attributes


format_to_xsd = {
    "mzquant": "https://www.psidev.info/sites/default/files/mzQuantML_1_0_0.xsd",
    "traml": "http://www.peptideatlas.org/schemas/TraML/1.0.0/TraML1.0.0.xsd",
    "mzid": "https://raw.githubusercontent.com/HUPO-PSI/mzIdentML/master/schema/mzIdentML1.2.0.xsd",
    "mzml": "http://psidev.info/files/ms/mzML/xsd/mzML1.1.0.xsd"
}


merged = defaultdict(lambda: defaultdict(list))

for schema, uri in format_to_xsd.items():
    print(schema)
    attrs = dump_attributes(uri)
    with open(f"{schema}_attrs.json", 'wt') as fh:
        json.dump(attrs, fh, sort_keys=True, indent=2)

    for attr_name, attr_tp_to_tp_name in attrs.items():
        node = merged[attr_name]
        for attr_tp, tp_names in attr_tp_to_tp_name.items():
            node[attr_tp].extend(zip(tp_names, itertools.cycle([schema])))

with open(f"merged_attrs.json", 'wt') as fh:
    json.dump(merged, fh, sort_keys=True, indent=2)

with open("attributes.csv", 'wt', newline='') as fh:
    writer = csv.writer(fh)
    writer.writerow(["attribute_name", "attribute_type", "tag_type", "format"])
    for attr_name, attr_tp_to_tp_name in merged.items():
        for attr_tp, tp_names in attr_tp_to_tp_name.items():
            for tp_name, schema in tp_names:
                writer.writerow([
                    attr_name, attr_tp, tp_name, schema
                ])
