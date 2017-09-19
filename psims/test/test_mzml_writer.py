from psims.mzml import MzMLWriter
from pyteomics import mzml
import numpy as np
from lxml import etree
import tempfile
import os

import pytest

from .utils import output_path


mz_array = [
    255.22935009, 283.26141863, 284.26105318, 301.23572871,
    304.908247, 329.26327093, 755.25267878, 910.6317435,
    960.96747136, 971.31396162, 972.649568, 991.66036894,
    1017.87649113, 1060.29899182, 1112.67519902, 1113.11545762,
    1113.86200673, 1114.42377982, 1152.34596544, 1177.73119994,
    1188.36935517, 1214.70161813, 1265.9795606, 1266.16111855,
    1293.14606767, 1294.68263447, 1367.01605133, 1565.95282753,
    1700.23290184, 969.65408783, 1110.37794027, 1170.89893785,
    1175.34669421, 1183.40737076, 861.61958381, 1292.94207114,
    1295.4429046, 876.96085225, 1335.39755355, 1357.92354342,
    1365.96972386, 925.64504217, 958.65480011, 1438.49014079,
    1452.48402739, 967.98859816, 986.63557879, 1480.46326372,
    1001.97032019, 1007.67089513, 1525.51932956, 1016.67747057,
    1080.3583722, 1090.03199733, 1133.01762219, 1186.72735997,
    960.79647487, 1274.44354121, 1918.2693496, 961.85503396
]

intensity_array = [
    1.90348869e+03, 1.92160377e+03, 3.26032338e+02,
    1.05527732e+03, 9.50991606e+02, 1.52403574e+03,
    8.63154395e+02, 4.11169655e+02, 2.33462730e+03,
    2.62603673e+02, 2.73669694e+02, 8.62436899e+02,
    4.22323174e+02, 2.54371429e+02, 1.02364420e+03,
    5.44244205e+02, 4.93101348e+02, 2.64984906e+02,
    9.36500725e+02, 4.79373626e+02, 9.26742857e+02,
    4.52209221e+02, 3.02178809e+03, 4.94385979e+02,
    1.67240655e+03, 9.41320838e+02, 7.25744090e+02,
    1.27260012e+03, 8.24236545e+02, 4.93518583e+02,
    7.33281806e+04, 9.60817582e+02, 2.64893187e+03,
    7.95614286e+03, 4.94586514e+03, 2.35346153e+04,
    1.50301526e+03, 5.36435167e+03, 3.78042332e+02,
    1.09926345e+03, 3.10133857e+03, 7.41566590e+02,
    2.77340229e+05, 1.00796887e+05, 4.69519356e+03,
    1.55343822e+04, 5.45621612e+03, 5.53939031e+03,
    9.49732490e+03, 8.05000735e+03, 2.65457068e+03,
    1.36766228e+04, 2.69348480e+03, 6.71802368e+03,
    4.46828571e+02, 1.39065143e+04, 4.29267365e+03,
    2.73782365e+03, 1.35373492e+03, 1.17601397e+03
]

charge_array = [
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -2, -2, -2, -2, -2,
    -3, -2, -2, -3, -2, -2, -2, -3, -3, -2, -2, -3, -3, -2, -3, -3, -2,
    -3, -3, -3, -3, -3, -5, -4, -3, -6
]


sample = {
    "name": "shotgun explodeomics precipitate #123",
    "params": [
        "certified organic",
        {"acquired in": "1812"}
    ]
}


def test_write(output_path):
    f = MzMLWriter(open(output_path, 'wb'))

    with f:
        f.controlled_vocabularies()
        f.file_description(["spam"], [
            dict(id="SPAM1", name="Spam.raw", location="file:///", params=[dict(name="Thermo RAW format")])])
        f.sample_list([sample])
        with f.element('run'):
            with f.spectrum_list(count=1):
                f.write_spectrum(mz_array, intensity_array, charge_array, id='scanId=1', params=[
                    {"name": "ms level", "value": 1}], polarity='negative scan')
                f.write_spectrum(mz_array, intensity_array, charge_array, id='scanId=2', params=[
                    {"name": "ms level", "value": 2}], polarity='negative scan', precursor_information={
                        "mz": 1230, "intensity": None, "charge": None, "params": [
                            "No Ion Found"
                        ],
                        "scan_id": "scanId=1"
                })
    try:
        f.format()
    except OSError:
        pass

    reader = mzml.read(output_path)
    sample_data = next(reader.iterfind("sample"))
    assert sample_data['name'] == "shotgun explodeomics precipitate #123"
    reader.reset()
    spec = next(reader)
    assert (all(np.abs(spec['m/z array'] - mz_array) < 1e-4))
    assert "negative scan" in spec
    assert spec['ms level'] == 1
    spec = next(reader)
    assert "negative scan" in spec
    assert spec['ms level'] == 2
