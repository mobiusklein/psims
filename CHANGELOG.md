# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][Keep a Changelog] and this project adheres to [Semantic Versioning][Semantic Versioning].

## [v0.1.45]

### CV Versions
| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 6e4b70ba06653e2944a7f4e73e30a42b |
| gno.obo.gz | 2021-08-13 | a0365da4060e84703aaec8baeae753d0 |
| go.obo.gz | releases/2021-11-16 | 1cc9921ed933b2de6231cdfa4a0acdf6 |
| pato.obo.gz | releases/2019-09-05 | 443de10a418cba2b0a6f4a9c3b73c60c |
| psi-mod.obo.gz | - | 0f6779b432281c47de1f6879262e394d |
| psi-ms.obo.gz | 4.1.64 | 162f1ab5e81bacd9bfce95088d1f4967 |
| unimod_tables.xml.gz | - | 61ac665064dd806b536c609fcb775920 |
| unit.obo.gz | releases/2020-03-10 | 4e45267605698d1fcda533c27853a8fc |


## [v0.1.44] - 2021-12-04

### CV Versions
| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 6e4b70ba06653e2944a7f4e73e30a42b |
| gno.obo.gz | 2021-08-13 | a0365da4060e84703aaec8baeae753d0 |
| go.obo.gz | releases/2021-11-16 | 1cc9921ed933b2de6231cdfa4a0acdf6 |
| pato.obo.gz | releases/2019-09-05 | 443de10a418cba2b0a6f4a9c3b73c60c |
| psi-mod.obo.gz | - | 0f6779b432281c47de1f6879262e394d |
| psi-ms.obo.gz | 4.1.64 | 162f1ab5e81bacd9bfce95088d1f4967 |
| unimod_tables.xml.gz | - | 61ac665064dd806b536c609fcb775920 |
| unit.obo.gz | releases/2020-03-10 | 4e45267605698d1fcda533c27853a8fc |

### Added
- Improved documentation of HDF5 compressors


## [v0.1.43] - 2021-08-06

### Added
1. Properly coerce negative numbers

### Fixed
1. Restored support for Py3.5

## [v0.1.42] - 2021-08-05

### Fixed
1. Made CV-param binding safe to use for Py2 again.

## [v0.1.41] - 2021-08-05

### Added
1. Re-wrote the `Entity.value_type` machinery to better take into account
   compound or vocabulary-defined types.
2. Modified the `Relationship` type to be able to dispatch to sub-classes for named
   relationship types.

### Changed
1. Updated vendor controlled vocabularies.

## [v0.1.39] - 2021-06-27

### Added
1. The data model for representing entities in OBO was revised to cover a wider range of cases.
2. `Entity` attributes are automatically type-coerced if their primitive types are recognizable. This
   does not apply to formula-like attributes as these are formatted in a controlled vocabulary-specific
   manner.

### Changed
1. Updated vendor controlled vocabularies.

### Deprecated

### Removed

### Fixed

### Security


## [v0.1.38] - 2021-05-24

### Changed
1. Updated vendor controlled vocabularies
2. Extended mzML writer's list of known arrays to match `psi-ms.obo` v4.1.53's new list
3. Added additional warnings for when users have `h5py` but not `hdf5plugin`


## [v0.1.37]

### Added
1. Added additional in-memory buffering of data arrays to reduce round-trips to HDF5 file when writing mzMLb.

### Changed
1. The `MzIdentMLTranslater` class was renamed `MzIdentMLTranslator` for the sake of the English language.
2. Overhauled large parts of the documentation.
3. Added clearer error message when attempting to use the mzMLb components without `h5py`.

### Deprecated

### Removed

### Fixed
1. Made the README mzML example actually work.
2. Allowed `Mapping` types to be used for `other_arrays` array names so that units may be specified. Previously, only
   hashable types were supported, though this was not the intent. Also corrected the documentation to indicate this
   expects a `list` of (name, array) pairs, not a `Mapping` of them.

### Security

## [v0.1.35]

### Added
1. Added a change log.
2. Added a `mzMLb` writer implementation.

### Changed
1. Improved write performance when writing `indexedMzML` by supporting `io.BufferedWriter`
   wrapping the whole write stack.
2. Vendored controlled vocabularies are now gzip-compressed so they use much less space on disk.

### Deprecated

### Removed

### Fixed

### Security

---

## [Released]

---

<!-- Links -->
[Keep a Changelog]: https://keepachangelog.com/
[Semantic Versioning]: https://semver.org/

<!-- Versions -->
[Unreleased]: https://github.com/mobiusklein/psims/compare/v0.1.44...HEAD
[Released]: https://github.com/mobiusklein/psims/releases
[v0.1.44]: https://github.com/mobiusklein/psims/releases/v0.1.44
[v0.1.43]: https://github.com/mobiusklein/psims/releases/v0.1.43
[v0.1.42]: https://github.com/mobiusklein/psims/releases/v0.1.42
[v0.1.41]: https://github.com/mobiusklein/psims/releases/v0.1.41
[v0.1.40]: https://github.com/mobiusklein/psims/releases/v0.1.40
[v0.1.39]: https://github.com/mobiusklein/psims/releases/v0.1.39
[v0.1.38]: https://github.com/mobiusklein/psims/releases/v0.1.38
[v0.1.37]: https://github.com/mobiusklein/psims/releases/v0.1.37
[v0.1.35]: https://github.com/mobiusklein/psims/releases/v0.1.35
[v0.1.34]: https://github.com/mobiusklein/psims/releases/v0.1.34