import itertools

from collections import Counter

import numpy as np

from lxml import etree

from pyteomics import mzml

from psims.mzml import MzMLWriter, binary_encoding, components
from psims import compression as compression_registry
from psims.test.utils import output_path, compressor, identity


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
    "name": "shotgun_explodeomics_precipitate_123",
    "params": [
        "certified organic",
        {"acquired in": "1812"}
    ]
}

encodings = {
    "m/z array": np.float64,
    "intensity array": np.float64,
    "charge array": np.float64
}


def test_array_codec():
    encode = binary_encoding.encode_array
    decode = binary_encoding.decode_array

    compression_types = [binary_encoding.COMPRESSION_ZLIB, binary_encoding.COMPRESSION_NONE]

    dtypes = [np.float64, np.float32]

    for dtype, compression in itertools.product(dtypes, compression_types):
        original = np.array(intensity_array, dtype=dtype)
        encoded = encode(original, compression, dtype)
        decoded = decode(encoded, compression, dtype)
        np.allclose(original, decoded)


def test_param_unit_resolution():
    param = components.NullMap.param({"base peak intensity": 1, 'unit_accession': 'MS:1000131'})
    assert param.unit_accession == "MS:1000131"
    assert param.value == 1
    assert param.name == 'base peak intensity'


def test_write(output_path, compressor):
    handle = compressor(output_path, 'wb')
    with MzMLWriter(handle, close=True) as f:
        f.register("Software", 'psims')
        f.controlled_vocabularies()
        f.native_id_format = "Agilent MassHunter nativeID format"
        f.file_description(["spam", "MS1 spectrum", "MSn spectrum"], [
            dict(id="SPAM1", name="Spam.raw", location="file:///", params=[
                dict(name="Thermo RAW format"), dict(name="Agilent MassHunter nativeID format")])
                ])
        f.reference_param_group_list([
            {'id': 'common_params', 'params': [{"proven": "inductively"}]}
        ])
        f.sample_list([sample])
        f.software_list([
            f.Software(version="0.0.0", id='psims', params=['custom unreleased software tool', 'python-psims'])
        ])
        f.instrument_configuration_list([
            f.InstrumentConfiguration(id=1, component_list=f.ComponentList([
                f.Source(params=['electrospray ionization'], order=1),
                f.Analyzer(params=['quadrupole'], order=2),
                f.Detector(params=['inductive detector'], order=3)
            ])),
            f.InstrumentConfiguration(id=2, component_list=f.ComponentList([
                f.Source(params=['electrospray ionization'], order=1),
                f.Analyzer(params=['radial ejection linear ion trap'], order=2),
                f.Detector(params=['inductive detector'], order=3)
            ]))
        ])
        f.data_processing_list([
            f.DataProcessing(processing_methods=[
                dict(order=0, software_reference='psims', params=['Conversion to mzML']),
            ], id=1)
        ])
        with f.run(id='test'):
            with f.spectrum_list(count=2):
                f.write_spectrum(mz_array, intensity_array, charge_array, id=1, params=[
                    {"name": "ms level", "value": 1}, {"ref": 'common_params'}],
                    polarity='negative scan', encoding=encodings,
                    compression='zlib')
                f.write_spectrum(mz_array, intensity_array, charge_array, id='scanId=2', params=[
                    {"name": "ms level", "value": 2}, {"ref": 'common_params'}],
                    polarity='negative scan', precursor_information={
                        "mz": 1230, "intensity": None, "charge": None, "params": [
                            "no peak detected"
                        ],
                        "scan_id": 1, "activation": ["collision-induced dissociation",
                                                              {"collision energy": 56.}]
                }, instrument_configuration_id=2, encoding=encodings, compression='zlib')
                pb = f.precursor_builder(mz=12030, scan_id='scanId=2')
                pb.selected_ion_list[0].set(charge=-2)
                pb.activation({"collision-induced dissociation": None})

                f.write_spectrum(mz_array, intensity_array, charge_array, id='scanId=3', params=[
                    {"name": "ms level", "value": 2}, {"ref": 'common_params'}],
                    polarity='negative scan', precursor_information=pb)

                spectrum = f.spectrum(mz_array, intensity_array, charge_array, id='scanId=4', params=[
                    {"name": "ms level", "value": 2}, {"ref": 'common_params'}],
                    polarity='negative scan', precursor_information=pb)
                spectrum.write()
    output_path = f.outfile.name
    opener = compression_registry.get(output_path)
    if compressor != identity:
        assert opener == compressor
    reader = mzml.read(opener(output_path, 'rb'))

    def reset():
        reader.reset()
        reader.seek(0)

    reset()
    sample_data = next(reader.iterfind("sample"))
    assert sample_data['name'] == "shotgun_explodeomics_precipitate_123"
    reset()
    spec = next(reader)
    assert (all(np.abs(spec['m/z array'] - mz_array) < 1e-4))
    assert "negative scan" in spec
    # appears to be broken in reader
    # assert "referenceableParamGroupRef" in spec and spec['referenceableParamGroupRef'][0]['ref'] == 'common_params'
    assert spec['ms level'] == 1
    spec = next(reader)
    assert "negative scan" in spec
    assert spec['ms level'] == 2
    assert "sourceFileRef" not in spec
    scan_list_struct = spec['scanList']
    reference = None
    for scan in scan_list_struct.get("scan", []):
        reference = scan.get("instrumentConfigurationRef")
        if reference is None:
            continue
    assert reference == "INSTRUMENTCONFIGURATION_2"

    reset()
    spectra = list(reader.iterfind("spectrum"))
    assert len(spectra) == 4
    ms_levels = Counter([s['ms level'] for s in spectra])
    assert ms_levels[1] == 1
    assert ms_levels[2] == 3

    reset()
    inst_config = next(reader.iterfind("instrumentConfiguration"))
    assert inst_config['id'] == 'INSTRUMENTCONFIGURATION_1'
    assert ("quadrupole") in inst_config['componentList']['analyzer'][0]

    reset()
    file_description = next(reader.iterfind("fileDescription"))
    content = file_description['fileContent']
    assert "MS1 spectrum" in content
    assert "spam" in content

    reset()
    run = next(reader.iterfind("run"))
    assert run.get("defaultInstrumentConfigurationRef") == "INSTRUMENTCONFIGURATION_1"

    reset()
    index_list = list(reader.iterfind("index"))
    assert len(index_list) == 1
    assert index_list[0]['name'] == 'spectrum'
    reset()
    spectrum_offsets = list(reader.iterfind("offset"))
    for i, off in enumerate(spectrum_offsets):
        assert "scanId=%d" % (i + 1) == off['idRef']
    offset = int(spectrum_offsets[0]['offset'])
    reader.seek(offset)
    bytestring = reader.read(100)
    try:
        content = bytestring.decode("utf8")
    except AttributeError:
        content = bytestring
    assert 'index="0"' in content
    is_valid, schema = f.validate()
    assert is_valid, schema.error_log
    reset()
    line = reader.readline()
    assert line.startswith(b"""<?xml version='1.0' encoding='utf-8'?>""")
    reader.close()
