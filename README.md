# psims
Prototype work for a unified API for writing Proteomics Standards Initiative standardized formats
for mass spectrometry:
    1. mzML
    2. mzIdentML
    3. mzMLb

See the [Documenation](https://mobiusklein.github.io/psims) for more information

## mzML Minimal Example

```python
from psims.mzml.writer import MzMLWriter

# Load the data to write
scans = get_scan_data()

with MzMLWriter(open("out.mzML", 'wb'), close=True) as out:
    # Add default controlled vocabularies
    out.controlled_vocabularies()
    # Open the run and spectrum list sections
    with out.run(id="my_analysis"):
        spectrum_count = len(scans) + sum([len(products) for _, products in scans])
        with out.spectrum_list(count=spectrum_count):
            for scan, products in scans:
                # Write Precursor scan
                out.write_spectrum(
                    scan.mz_array, scan.intensity_array,
                    id=scan.id, params=[
                        "MS1 Spectrum",
                        {"ms level": 1},
                        {"total ion current": sum(scan.intensity_array)}
                     ])
                # Write MSn scans
                for prod in products:
                    out.write_spectrum(
                        prod.mz_array, prod.intensity_array,
                        id=prod.id, params=[
                            "MSn Spectrum",
                            {"ms level": 2},
                            {"total ion current": sum(prod.intensity_array)}
                         ],
                         # Include precursor information
                         precursor_information={
                            "mz": prod.precursor_mz,
                            "intensity": prod.precursor_intensity,
                            "charge": prod.precursor_charge,
                            "scan_id": prod.precursor_scan_id,
                            "activation": ["beam-type collisional dissociation", {"collision energy": 25}],
                            "isolation_window": [prod.precursor_mz - 1, prod.precursor_mz, prod.precursor_mz + 1]
                         })
```

## Citing

If you use `psims` in an academic project, please cite:

    Klein, J. A., & Zaia, J. (2018). psims - A declarative writer for mzML and mzIdentML for Python. Molecular & Cellular Proteomics, mcp.RP118.001070. https://doi.org/10.1074/mcp.RP118.001070
