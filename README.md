# psims
Prototype work for a unified API for writing PSIMS standardized XML documents, currently just mzML and MzIdentML


## mzML Minimal Example

```python
from psims.mzml.writer import MzMLWriter

# Load the data to write
scans = get_scan_data()

with MzMLWriter(open("out.mzML", 'wb')) as out:
    # Add default controlled vocabularies
    out.controlled_vocabularies()
    # Open the run and spectrum list sections
    with out.run(id="my_analysis"):
        with out.spectrum_list(count=len(scans)):
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
                            {"total ion current": sum(scan.intensity_array)}   
                         ], 
                         # Include precursor information
                         precursor_information={
                            "mz": prod.precursor_mz,
                            "intensity": prod.precursor_intensity,
                            "charge": prod.precursor_charge,
                            "scan_id": prod.precursor_scan_id
                         })
```
